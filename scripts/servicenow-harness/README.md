# ServiceNow kit harness

Executes the repo's ServiceNow Script Includes **outside a ServiceNow instance**,
so their refusal logic is observed rather than asserted.

## Why this exists

The three ServiceNow kits in this repo are ~3,700 lines of security-critical
Script Include JavaScript:

| Kit | Path |
|---|---|
| Day-2 automation | `docs/customer-documents/orgcomp-series/servicenow-day2/` |
| Federal compliance | `docs/customer-documents/orgcomp-series/x_fed_compliance/` |
| Infoblox DDI | `infoblox-ddi-book/servicenow-app/` |

Their only tests are ATF specs, which run nowhere except inside a ServiceNow
instance. Before this harness, **no gate in this repo executed any of that
JavaScript** — the Python gates in each kit read it as text, and the ATF suite's
passing status was a claim, not an observation.

That is exactly the failure mode the external adversarial security review found
on 2026-07-29: `test_mode` short-circuited before the vulnerable code path, so
all twelve ATF specs passed while the injection path had never once executed.

**On its first run this harness found a live defect.** `AdHybridClient._isAllowedOu`
split the managed-OU allowlist on `,` — which is also the DN component separator
— so `OU=Users,DC=corp,DC=gov` was shredded into three fragments and no
well-formed DN could ever match. The allowlist was inert and both `createUserAd`
and `moveUserOuAd` refused every OU. Fail-closed, so not a vulnerability, but the
control did not work and nothing was checking.

## Running it

```bash
node scripts/servicenow-harness/run.js              # all specs
node scripts/servicenow-harness/run.js AdHybrid     # specs matching a substring

cd scripts/servicenow-harness && npm install        # once, for the linter
npm run lint                                        # ESLint, ES5 + Glide globals
npm test                                            # same as run.js
```

`HARNESS_JSON=results.json node scripts/servicenow-harness/run.js` writes a
machine-readable result file — that is the artifact to hand a ServiceNow
developer who wants to see named assertions with outcomes.

## What it is, and what it is not

**It is** a minimal implementation of the platform surface the kits' *refusal*
paths touch: `gs`, `GlideRecord`, `GlideDateTime`, `Class.create`. Every side
effect is captured rather than performed, so a spec can assert what a Script
Include *would have* sent to the platform.

**It is not** a ServiceNow emulator. It does not model ACLs, business rules, data
policies, Flow Designer, the ECC round trip, or update-set import. A test that
needs any of those belongs in ATF, on a real instance.

The division of labour:

| Question | Answered by |
|---|---|
| Does the refusal logic hold? | this harness, on every commit |
| Is the syntax valid, is the ES5 target respected? | `node --check` + ESLint |
| Do the two AD allowlists still agree? | `check_allowlist_parity.py` |
| Does the update set import, do the ACLs bind, does MID dispatch round-trip? | **ATF on a real instance — still required** |

## Files

| File | Role |
|---|---|
| `glide-shim.js` | The platform globals, in-process. Records side effects. |
| `load.js` | Evaluates a Script Include in a `node:vm` context and returns the class. |
| `run.js` | Discovers and runs `specs/*.spec.js`; no test-framework dependency. |
| `specs/*.spec.js` | One spec file per Script Include under test. |

Kit sources load **unmodified**. If a kit needs editing to become testable, the
harness is wrong, not the kit.

## Writing a spec

```js
const { loadScriptInclude, construct, silentLog } = require('../load.js');

module.exports = function (t, assert) {
    t('refuses an unknown parameter', () => {
        const { klass } = loadScriptInclude('day2', 'AdHybridClient', {
            properties: { 'x_fed_day2_ops.ad_mid_server': 'mid01' },
        });
        const c = construct(klass, { midServer: 'mid01', log: silentLog() });
        assert.refused(c.setUserAttributesAd('jdoe', { bogus: 'x' }), /not permitted/);
    });
};
```

`construct()` builds an instance **without** running `initialize()`. Most kit
`initialize()` bodies read a dozen system properties and construct sibling Script
Includes that are not under test; setting the handful of fields the method under
test actually reads keeps the seams visible in the spec instead of buried in shim
configuration.

Assertions available: `ok`, `notOk`, `equal`, `match`, `includes`, `throws`, plus
two shaped for this codebase — `refused(result, /pattern/)` for the
`{ ok: false, error }` convention, and `lacksKeys(result, [...])` for asserting a
write never claims post-state.

`loadScriptInclude(kit, name, options)` options: `properties` (system
properties), `records` (`table -> [rows]`, queried by `addQuery` equality),
`validTables` (drives the missing-table refusal path), and `globals` (inject
collaborators such as `Day2Env` or a scoped-app namespace).

## CI

`.github/workflows/servicenow-kit-checks.yml` runs all four gates on any change
to a kit. The same four are pre-commit hooks: `servicenow-kit-syntax`,
`servicenow-kit-eslint`, `servicenow-kit-harness`,
`servicenow-ad-allowlist-parity`.
