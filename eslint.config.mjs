// =============================================================================
// ESLint — ServiceNow kit profile.
//
// Server-side ServiceNow runs Script Includes on Rhino (or the ES2021 engine
// only when a scoped app opts in). The kits target the conservative baseline,
// so this config pins ES5 syntax and declares the platform globals. The point
// is not style: it is that an undeclared global or a stray `const` is a runtime
// failure on the instance that no reviewer reliably catches by eye, and that
// nothing in this repo was checking for before.
//
// Lives at the repo root because ESLint 9's flat config ignores any file
// outside its own base path, and the kits sit under docs/ and
// infoblox-ddi-book/. The toolchain itself stays scoped to
// scripts/servicenow-harness/ so this does not turn the repo into a Node
// project: there is no root package.json and no root node_modules.
//
//   cd scripts/servicenow-harness && npm run lint
// =============================================================================

const GLIDE_GLOBALS = {
    // Core server-side API
    gs: 'readonly',
    GlideRecord: 'readonly',
    GlideAggregate: 'readonly',
    GlideDateTime: 'readonly',
    GlideDate: 'readonly',
    GlideDuration: 'readonly',
    GlideTime: 'readonly',
    GlideSession: 'readonly',
    GlideSysAttachment: 'readonly',
    GlideStringUtil: 'readonly',
    GlideSecureRandomUtil: 'readonly',
    GlideDigest: 'readonly',
    GlideEncrypter: 'readonly',
    GlideFilter: 'readonly',
    GlideScriptedExtensionPoint: 'readonly',
    GlideTableHierarchy: 'readonly',
    GlideProperties: 'readonly',
    // Object model
    Class: 'readonly',
    JSUtil: 'readonly',
    // Integration
    RESTMessageV2: 'readonly',
    SOAPMessageV2: 'readonly',
    sn_ws: 'readonly',
    sn_fd: 'readonly',
    sn_auth: 'readonly',
    // Scoped application namespaces used by the kits
    x_fed_day2_ops: 'readonly',
    x_fed_compliance: 'readonly',
    x_infoblox_ddi: 'readonly',
    // The global application scope. A scoped app reaches cross-scope classes
    // through it (`new global.JavascriptProbe(...)`).
    global: 'readonly',
    GSLog: 'readonly',
    // Cross-Script-Include statics the kits reference by name. Classes
    // DECLARED by a kit file are deliberately absent: listing them here makes
    // their own `var Foo = Class.create()` a no-redeclare error.
    Day2Env: 'readonly',
    // Scripted REST. The platform injects `request` and `response` into a
    // resource script's scope; a resource that declared them would shadow the
    // real ones.
    RESTAPIRequest: 'readonly',
    RESTAPIResponse: 'readonly',
    request: 'readonly',
    response: 'readonly',
    // Common globals available on the platform
    JSON: 'readonly',
    Packages: 'readonly',
    action: 'readonly',
    current: 'readonly',
    previous: 'readonly',
};

export default [
    {
        // Everything else in the repo is out of scope: this config exists for
        // the ServiceNow kits and their harness, not for site assets or the
        // docs tooling, which have no ServiceNow runtime constraints.
        ignores: [
            '**/node_modules/**',
            'src/uiao/api/web/static/**',
            'docs/scripts/**',
            'docs/tools/**',
            'docs/docs/javascripts/**',
            'docs/_site/**',
            '.venv/**',
        ],
    },
    {
        name: 'servicenow-kits',
        files: [
            'docs/customer-documents/orgcomp-series/*/script-includes/**/*.js',
            'docs/customer-documents/orgcomp-series/*/scripted-rest/**/*.js',
            'docs/customer-documents/orgcomp-series/*/business-rules/**/*.js',
            'docs/customer-documents/orgcomp-series/*/fix-scripts/**/*.js',
            'infoblox-ddi-book/servicenow-app/script-includes/**/*.js',
            'infoblox-ddi-book/servicenow-app/scripted-rest/**/*.js',
        ],
        languageOptions: {
            // ES5: matches the Rhino baseline the kits target. A `let`, an arrow
            // function or a template literal is a parse error here, which is
            // exactly the feedback a kit author needs before an import.
            ecmaVersion: 5,
            sourceType: 'script',
            globals: GLIDE_GLOBALS,
        },
        linterOptions: {
            reportUnusedDisableDirectives: true,
        },
        rules: {
            // --- correctness: these are the ones that bite on an instance ---
            'no-undef': 'error',              // an undeclared global is a runtime crash
            'no-eval': 'error',               // the kits' own doctrine: never
            'no-implied-eval': 'error',
            'no-new-func': 'error',
            // OFF, deliberately. A Script Include is REQUIRED to declare its
            // class as a global `var` -- that is how the platform resolves the
            // name. Enabling this rule flags the one construct every Script
            // Include must contain, which would train reviewers to ignore the
            // linter. Genuine leaks are caught by no-undef instead.
            'no-implicit-globals': 'off',
            // caughtErrors: 'none' because ES5 has no optional catch binding
            // (that is ES2019). `catch (e) {}` with an unused `e` is not a
            // defect here -- it is the only syntax the target engine accepts.
            'no-unused-vars': ['error', { args: 'none', caughtErrors: 'none', varsIgnorePattern: '^_' }],
            'no-redeclare': 'error',
            'no-dupe-keys': 'error',          // a duplicated allowlist key silently wins
            'no-dupe-args': 'error',
            'no-duplicate-case': 'error',
            'no-unreachable': 'error',
            'no-fallthrough': 'error',
            'no-cond-assign': ['error', 'always'],
            'no-constant-condition': 'error',
            'no-sparse-arrays': 'error',
            'no-prototype-builtins': 'off',   // the kits call hasOwnProperty directly, by design
            'valid-typeof': 'error',
            'use-isnan': 'error',

            // --- security-shaped ---
            'no-script-url': 'error',
            'no-proto': 'error',
            'no-extend-native': 'error',
            'no-global-assign': 'error',

            // --- consistency that prevents real bugs ---
            eqeqeq: ['error', 'smart'],
            'no-caller': 'error',
            'no-with': 'error',
            'no-throw-literal': 'error',
            curly: 'off',                     // the kits use single-line guards throughout
        },
    },
    {
        // Day2Env.js DECLARES Day2Env; every other kit file merely references
        // it. Declaring it globally is right for the consumers and wrong for
        // the declarer, so the declaring file drops it from its own globals.
        name: 'servicenow-kits/declaring-files',
        files: ['docs/customer-documents/orgcomp-series/servicenow-day2/script-includes/Day2Env.js'],
        languageOptions: {
            globals: { Day2Env: 'off' },
        },
    },
    {
        // The harness itself is modern Node, not Rhino.
        name: 'harness',
        files: ['scripts/servicenow-harness/*.js', 'scripts/servicenow-harness/specs/**/*.js'],
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: 'commonjs',
            globals: { require: 'readonly', module: 'writable', process: 'readonly',
                       console: 'readonly', __dirname: 'readonly', Buffer: 'readonly' },
        },
        rules: {
            'no-unused-vars': ['error', { args: 'none' }],
            'no-undef': 'error',
        },
    },
];
