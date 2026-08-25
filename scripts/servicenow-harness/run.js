#!/usr/bin/env node
'use strict';
// =============================================================================
// run.js — the harness runner.
//
// Discovers specs/*.spec.js, runs them, prints a report, exits non-zero on any
// failure. No test framework dependency: this must run on a bare Node in CI
// with nothing installed, because the value of the gate is that it is always
// available, not that it is featureful.
//
//   node scripts/servicenow-harness/run.js            # all specs
//   node scripts/servicenow-harness/run.js AdHybrid   # specs matching a substring
// =============================================================================

const fs = require('fs');
const path = require('path');

const SPEC_DIR = path.join(__dirname, 'specs');
const filter = process.argv[2] || '';

const results = [];
let passed = 0;
let failed = 0;

/** Assertion surface handed to each spec. */
function makeSuite(specName) {
    const cases = [];
    const t = (name, fn) => cases.push({ name, fn });
    return { specName, cases, t };
}

function deepIncludes(haystack, needle) {
    if (haystack === needle) return true;
    if (typeof haystack === 'string' && typeof needle === 'string') return haystack.includes(needle);
    return false;
}

const assert = {
    ok(value, message) {
        if (!value) throw new Error(message || `expected truthy, got ${JSON.stringify(value)}`);
    },
    notOk(value, message) {
        if (value) throw new Error(message || `expected falsy, got ${JSON.stringify(value)}`);
    },
    equal(actual, expected, message) {
        if (actual !== expected) {
            throw new Error(message || `expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
        }
    },
    match(actual, regex, message) {
        if (!regex.test(String(actual))) {
            throw new Error(message || `expected ${JSON.stringify(String(actual))} to match ${regex}`);
        }
    },
    includes(haystack, needle, message) {
        if (!deepIncludes(haystack, needle)) {
            throw new Error(message || `expected ${JSON.stringify(haystack)} to include ${JSON.stringify(needle)}`);
        }
    },
    /** The refusal shape the kits use: { ok:false, error:'...' } */
    refused(result, pattern, message) {
        if (!result || result.ok !== false) {
            throw new Error(message || `expected a refusal, got ${JSON.stringify(result)}`);
        }
        if (pattern) {
            const text = String(result.error || result.reason || '');
            if (!pattern.test(text)) {
                throw new Error(message || `refusal reason ${JSON.stringify(text)} did not match ${pattern}`);
            }
        }
    },
    /** No key in `forbidden` may appear on the result. */
    lacksKeys(result, forbidden, message) {
        const present = forbidden.filter((k) => result && Object.prototype.hasOwnProperty.call(result, k));
        if (present.length) {
            throw new Error(message || `result must not carry ${present.join(', ')}: ${JSON.stringify(result)}`);
        }
    },
    throws(fn, message) {
        let threw = false;
        try { fn(); } catch { threw = true; }
        if (!threw) throw new Error(message || 'expected the call to throw');
    },
};

function main() {
    if (!fs.existsSync(SPEC_DIR)) {
        console.error(`no spec directory at ${SPEC_DIR}`);
        process.exit(1);
    }

    const specFiles = fs.readdirSync(SPEC_DIR)
        .filter((f) => f.endsWith('.spec.js'))
        .filter((f) => !filter || f.toLowerCase().includes(filter.toLowerCase()))
        .sort();

    if (!specFiles.length) {
        console.error(filter ? `no specs matched ${JSON.stringify(filter)}` : 'no specs found');
        process.exit(1);
    }

    console.log('ServiceNow kit harness — executing Script Include sources outside an instance');
    console.log('='.repeat(78));

    for (const file of specFiles) {
        const specName = file.replace(/\.spec\.js$/, '');
        const suite = makeSuite(specName);
        let loadError = null;

        try {
            require(path.join(SPEC_DIR, file))(suite.t, assert);
        } catch (e) {
            loadError = e;
        }

        console.log(`\n${specName}`);

        if (loadError) {
            failed++;
            console.log(`  FAIL  <spec failed to load>`);
            console.log(`        ${loadError.message}`);
            results.push({ spec: specName, name: '<load>', ok: false, error: loadError.message });
            continue;
        }

        for (const c of suite.cases) {
            try {
                c.fn();
                passed++;
                console.log(`  PASS  ${c.name}`);
                results.push({ spec: specName, name: c.name, ok: true });
            } catch (e) {
                failed++;
                console.log(`  FAIL  ${c.name}`);
                console.log(`        ${e.message}`);
                results.push({ spec: specName, name: c.name, ok: false, error: e.message });
            }
        }
    }

    console.log('\n' + '='.repeat(78));
    console.log(`${passed} passed, ${failed} failed, ${specFiles.length} spec file(s)`);

    if (process.env.HARNESS_JSON) {
        fs.writeFileSync(process.env.HARNESS_JSON, JSON.stringify({ passed, failed, results }, null, 2));
        console.log(`results written to ${process.env.HARNESS_JSON}`);
    }

    process.exit(failed ? 1 : 0);
}

main();
