'use strict';
// =============================================================================
// load.js — evaluate a Script Include in a sandboxed context and hand back the
// constructed class, plus the captured side effects.
//
// Uses node:vm rather than eval() so kit code cannot reach this process's
// globals: a Script Include that referenced `process` or `require` would fail
// here exactly as it fails on a ServiceNow instance, instead of silently
// working in the harness and breaking in production.
// =============================================================================

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { createSandbox } = require('./glide-shim.js');

const REPO_ROOT = path.resolve(__dirname, '..', '..');

// The three kits whose Script Includes this harness covers.
const KITS = {
    day2: 'docs/customer-documents/orgcomp-series/servicenow-day2',
    fedcompliance: 'docs/customer-documents/orgcomp-series/x_fed_compliance',
    infoblox: 'infoblox-ddi-book/servicenow-app',
};

function kitPath(kit, relative) {
    if (!KITS[kit]) throw new Error(`unknown kit: ${kit} (known: ${Object.keys(KITS).join(', ')})`);
    return path.join(REPO_ROOT, KITS[kit], relative);
}

/**
 * Load one Script Include.
 *
 * @param {string} kit       key of KITS
 * @param {string} name      Script Include name, e.g. 'AdHybridClient'
 * @param {object} options   passed to createSandbox (properties, records, ...)
 * @returns {{ klass, sandbox, captured, context }}
 */
function loadScriptInclude(kit, name, options) {
    const file = kitPath(kit, path.join('script-includes', `${name}.js`));
    return loadFile(file, name, options);
}

/**
 * Load an arbitrary kit JS file (Scripted REST resources live outside
 * script-includes/, so they need this rather than loadScriptInclude).
 */
function loadFile(file, exportName, options) {
    if (!fs.existsSync(file)) throw new Error(`source not found: ${file}`);
    const source = fs.readFileSync(file, 'utf8');

    const opts = options || {};
    const sandbox = createSandbox(opts);

    // opts.globals lets a spec inject collaborators a Script Include reaches
    // for by name -- the scoped-application namespace (`x_fed_day2_ops.Foo`)
    // and cross-Script-Include statics such as `Day2Env.scrub`. Injecting a
    // stub keeps a unit spec about the file under test instead of pulling the
    // whole kit into every load.
    const context = vm.createContext(Object.assign({}, sandbox.globals, opts.globals || {}));

    // ServiceNow exposes extendsObject as a method on the global Object. Doing
    // this inside the context keeps the kit's own `Object.extendsObject(...)`
    // call site working without the kit knowing it is under test.
    vm.runInContext(
        'Object.extendsObject = Object_extendsObject;',
        context,
        { filename: 'harness:bootstrap' }
    );

    // filename is the real path so a stack trace points at the kit file, not
    // at the harness.
    vm.runInContext(source, context, { filename: file });

    const klass = exportName ? vm.runInContext(exportName, context) : undefined;
    if (exportName && typeof klass !== 'function') {
        throw new Error(`${exportName} did not evaluate to a constructor in ${file}`);
    }

    return { klass, sandbox, captured: sandbox.captured, context, source, file };
}

/**
 * Build an instance WITHOUT running initialize().
 *
 * Most kit initialize() bodies read a dozen system properties and construct
 * sibling Script Includes that are not under test. A refusal-path spec wants
 * the method under test and the fields it reads, nothing else -- so specs set
 * those fields explicitly and the seams stay visible in the spec rather than
 * hidden in shim configuration.
 */
function construct(klass, fields) {
    const instance = Object.create(klass.prototype);
    Object.assign(instance, fields || {});
    return instance;
}

/** A no-op logger matching the { info, warn, err } shape the kits use. */
function silentLog() {
    const calls = { info: [], warn: [], err: [] };
    return {
        calls,
        info: (m) => calls.info.push(String(m)),
        warn: (m) => calls.warn.push(String(m)),
        err: (m) => calls.err.push(String(m)),
        error: (m) => calls.err.push(String(m)),
    };
}

module.exports = { loadScriptInclude, loadFile, construct, silentLog, kitPath, KITS, REPO_ROOT };
