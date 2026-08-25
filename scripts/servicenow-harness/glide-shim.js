'use strict';
// =============================================================================
// glide-shim.js — the ServiceNow platform globals, in-process.
//
// Why this exists: the kits under docs/customer-documents/orgcomp-series/ are
// ~3,700 lines of security-critical Script Include JavaScript whose only tests
// (ATF specs) can run nowhere except inside a ServiceNow instance. That made
// every refusal claim in those files an assertion rather than an observation --
// which is precisely the failure mode the external review found in July 2026,
// where `test_mode` short-circuited before the vulnerable path and all 12 specs
// passed while the injection path had never executed.
//
// This shim is deliberately NOT a ServiceNow emulator. It implements only the
// surface the kits' *refusal* paths touch, and it records side effects so a
// spec can assert what a Script Include would have sent to the platform. A test
// that needs more platform than this belongs in ATF, on a real instance.
//
// Design rules:
//   * Kit sources load UNMODIFIED. If a kit needs editing to be testable, the
//     harness is wrong, not the kit.
//   * Every side effect is captured, never performed.
//   * Unknown property reads return '' (GlideRecord/gs semantics), not
//     undefined, so a missing shim surfaces as a kit-visible value rather than
//     a TypeError that looks like a kit bug.
// =============================================================================

function createSandbox(options) {
    options = options || {};

    // Captured side effects. Specs assert against these.
    var captured = {
        inserts: [],      // { table, values }
        updates: [],      // { table, sys_id, values }
        logs: { info: [], warn: [], error: [] },
        events: [],       // { name, args } from gs.eventQueue
    };

    var properties = Object.assign({}, options.properties || {});
    var records = options.records || {};   // table -> array of plain objects

    // --- Class.create / extendsObject -------------------------------------
    // ServiceNow's Prototype-derived object model. Script Includes call
    // Class.create() then assign a prototype literal; some extend a base.
    var Class = {
        create: function () {
            return function () {
                if (this.initialize) this.initialize.apply(this, arguments);
            };
        }
    };

    var Object_extendsObject = function (parent, child) {
        var merged = Object.create(parent && parent.prototype ? parent.prototype : Object.prototype);
        for (var k in child) {
            if (Object.prototype.hasOwnProperty.call(child, k)) merged[k] = child[k];
        }
        return merged;
    };

    // --- gs ----------------------------------------------------------------
    var gs = {
        getProperty: function (key, fallback) {
            if (Object.prototype.hasOwnProperty.call(properties, key)) return properties[key];
            return fallback === undefined ? '' : fallback;
        },
        setProperty: function (key, value) { properties[key] = value; },
        info: function (m) { captured.logs.info.push(String(m)); },
        warn: function (m) { captured.logs.warn.push(String(m)); },
        error: function (m) { captured.logs.error.push(String(m)); },
        log: function (m) { captured.logs.info.push(String(m)); },
        debug: function () {},
        nil: function (v) { return v === null || v === undefined || v === ''; },
        getUserID: function () { return options.userID || 'test.user'; },
        getUserName: function () { return options.userName || 'test.user'; },
        hasRole: function (r) { return (options.roles || []).indexOf(r) !== -1; },
        eventQueue: function (name) {
            captured.events.push({ name: name, args: Array.prototype.slice.call(arguments, 1) });
        },
        now: function () { return '2026-01-01'; },
        nowDateTime: function () { return '2026-01-01 00:00:00'; },
        generateGUID: function () { return 'guid-' + (captured.inserts.length + 1); },
    };

    // --- GlideDateTime -----------------------------------------------------
    // Fixed clock. A harness that returns a real timestamp makes any spec that
    // asserts on a payload non-deterministic.
    function GlideDateTime(value) {
        this._v = value || (options.now || '2026-01-01 00:00:00');
    }
    GlideDateTime.prototype.getValue = function () { return this._v; };
    GlideDateTime.prototype.getDisplayValue = function () { return this._v; };
    GlideDateTime.prototype.toString = function () { return this._v; };
    GlideDateTime.prototype.getNumericValue = function () { return 1767225600000; };
    GlideDateTime.prototype.addSeconds = function () {};

    // --- GlideRecord -------------------------------------------------------
    // Query support is intentionally minimal: addQuery(field, value) equality
    // against the seeded `records` table. That covers the reconciliation and
    // read-back lookups the refusal paths make; anything richer is ATF's job.
    function GlideRecord(table) {
        this._table = table;
        this._values = {};
        this._query = [];
        this._rows = [];
        this._i = -1;
        this._loaded = false;
        this.sys_id = '';
    }

    GlideRecord.prototype.initialize = function () { this._values = {}; };
    GlideRecord.prototype.newRecord = function () { this._values = {}; };

    GlideRecord.prototype.addQuery = function (field, a, b) {
        // addQuery(field, value) or addQuery(field, operator, value)
        var value = (b === undefined) ? a : b;
        var op = (b === undefined) ? '=' : a;
        this._query.push({ field: field, op: op, value: value });
        return { addOrCondition: function () {} };
    };
    GlideRecord.prototype.addEncodedQuery = function () {};
    GlideRecord.prototype.setLimit = function () {};
    GlideRecord.prototype.orderBy = function () {};
    GlideRecord.prototype.orderByDesc = function () {};

    GlideRecord.prototype.query = function () {
        var rows = (records[this._table] || []).slice();
        var q = this._query;
        this._rows = rows.filter(function (row) {
            return q.every(function (c) {
                var actual = row[c.field];
                if (c.op === '!=') return String(actual) !== String(c.value);
                return String(actual) === String(c.value);
            });
        });
        this._i = -1;
        this._loaded = true;
    };
    GlideRecord.prototype.get = function (field, value) {
        if (value === undefined) { this.addQuery('sys_id', field); }
        else { this.addQuery(field, value); }
        this.query();
        return this.next();
    };

    GlideRecord.prototype.next = function () {
        if (!this._loaded) this.query();
        this._i++;
        if (this._i < this._rows.length) {
            this._values = Object.assign({}, this._rows[this._i]);
            this.sys_id = this._values.sys_id || ('row-' + this._i);
            return true;
        }
        return false;
    };
    GlideRecord.prototype._next = GlideRecord.prototype.next;
    GlideRecord.prototype.hasNext = function () {
        if (!this._loaded) this.query();
        return (this._i + 1) < this._rows.length;
    };
    GlideRecord.prototype.getRowCount = function () {
        if (!this._loaded) this.query();
        return this._rows.length;
    };

    GlideRecord.prototype.getValue = function (field) {
        var v = this._values[field];
        return (v === undefined || v === null) ? '' : String(v);
    };
    GlideRecord.prototype.setValue = function (field, value) { this._values[field] = value; };
    GlideRecord.prototype.getDisplayValue = function (field) { return this.getValue(field); };
    GlideRecord.prototype.getUniqueValue = function () { return this.sys_id || ''; };
    GlideRecord.prototype.getTableName = function () { return this._table; };
    GlideRecord.prototype.isValidRecord = function () { return this._i >= 0 && this._i < this._rows.length; };
    // isValid() answers "does this table exist on the instance". Seeding
    // options.validTables lets a spec drive the missing-table refusal path,
    // which is otherwise unreachable without an instance that lacks the table.
    GlideRecord.prototype.isValid = function () {
        if (!options.validTables) return true;
        return options.validTables.indexOf(this._table) !== -1;
    };
    GlideRecord.prototype.canWrite = function () { return options.canWrite !== false; };
    GlideRecord.prototype.canRead = function () { return true; };

    GlideRecord.prototype.insert = function () {
        var id = 'sys_id_' + (captured.inserts.length + 1);
        captured.inserts.push({ table: this._table, values: Object.assign({}, this._values) });
        this.sys_id = id;
        return id;
    };
    GlideRecord.prototype.update = function () {
        captured.updates.push({
            table: this._table,
            sys_id: this.sys_id,
            values: Object.assign({}, this._values),
        });
        return this.sys_id;
    };
    GlideRecord.prototype.deleteRecord = function () { return true; };

    return {
        captured: captured,
        properties: properties,
        globals: {
            Class: Class,
            gs: gs,
            GlideRecord: GlideRecord,
            GlideDateTime: GlideDateTime,
            GlideAggregate: GlideRecord,
            GlideDate: GlideDateTime,
            JSUtil: { nil: gs.nil },
            Object_extendsObject: Object_extendsObject,
        },
    };
}

module.exports = { createSandbox: createSandbox };
