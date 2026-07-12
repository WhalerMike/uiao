// Script Include: InfobloxDDIClient  (application scope: x_infoblox_ddi)
// -----------------------------------------------------------------------------
// Server-side Infoblox client for the ServiceNow DDI orchestration app. Wraps the
// two control planes described in Chapter 7:
//   * NIOS WAPI  (self-managed Grid — in ATO boundary, deployment_model = grid)
//   * Universal DDI / Portal API (SaaS — out of boundary, acknowledge_saas_boundary)
//
// Credentials/endpoint come from a Connection & Credential alias
// (x_infoblox_ddi.infoblox) so no secrets live in code. Pick the flavor with the
// system property x_infoblox_ddi.api_flavor = "nios" | "universal_ddi".
//
// STARTER SKELETON — validate WAPI object/field versions against your Grid
// (<grid-master>/wapidoc) and the Universal DDI API reference before production use.
// -----------------------------------------------------------------------------
var InfobloxDDIClient = Class.create();
InfobloxDDIClient.prototype = {

    initialize: function () {
        this.flavor = gs.getProperty('x_infoblox_ddi.api_flavor', 'nios');
        this.wapiVersion = gs.getProperty('x_infoblox_ddi.wapi_version', 'v2.12');
        // Connection alias supplies base URL + basic/oauth credentials.
        this.midServer = gs.getProperty('x_infoblox_ddi.mid_server', '');
        this.log = new GSLog('x_infoblox_ddi.log', 'InfobloxDDIClient');
        // TEST MODE — when x_infoblox_ddi.test_mode = 'true', the allocate/register/
        // delete calls return deterministic canned values instead of hitting Infoblox,
        // so the ATF happy-path test (atf/) can drive the whole Flow in a sub-prod
        // instance with NO live Grid/Portal connectivity. Never enable in production.
        this.testMode = gs.getProperty('x_infoblox_ddi.test_mode', 'false') === 'true';
    },

    // Allocate the next free IP from a network and return it, or '' on failure.
    // networkCidr e.g. "10.16.4.0/24"; networkView optional.
    nextAvailableIp: function (networkCidr, networkView) {
        if (this.testMode) return gs.getProperty('x_infoblox_ddi.test_ip', '10.10.8.12');
        try {
            if (this.flavor === 'universal_ddi')
                return this._uddiNextAvailableIp(networkCidr, networkView);
            return this._niosNextAvailableIp(networkCidr, networkView);
        } catch (e) {
            this.log.logErr('nextAvailableIp failed: ' + e);
            return '';
        }
    },

    // Create an authoritative host (A+PTR) record. Returns the object ref/id or ''.
    createHostRecord: function (fqdn, ip, dnsView) {
        if (this.testMode) return 'record:host/TEST:' + fqdn;
        try {
            if (this.flavor === 'universal_ddi')
                return this._uddiCreateHost(fqdn, ip, dnsView);
            return this._niosCreateHost(fqdn, ip, dnsView);
        } catch (e) {
            this.log.logErr('createHostRecord failed: ' + e);
            return '';
        }
    },

    // Reclaim on decommission: delete an object by its ref/id. Returns boolean.
    deleteObject: function (ref) {
        if (this.testMode) return true;
        try {
            var r = this._rest('DELETE', this._path(ref), null);
            return r.getStatusCode() < 300;
        } catch (e) {
            this.log.logErr('deleteObject failed: ' + e);
            return false;
        }
    },

    // ---- NIOS WAPI branch ---------------------------------------------------
    _niosNextAvailableIp: function (cidr, view) {
        // 1) resolve the network _ref, 2) call its next_available_ip function.
        var q = '/network?network=' + encodeURIComponent(cidr) +
                (view ? '&network_view=' + encodeURIComponent(view) : '');
        var netResp = this._rest('GET', q, null);
        var nets = JSON.parse(netResp.getBody() || '[]');
        if (!nets.length) { this.log.logWarning('network not found: ' + cidr); return ''; }
        var ref = nets[0]._ref;
        var fnResp = this._rest('POST', '/' + ref + '?_function=next_available_ip&num=1', {});
        var out = JSON.parse(fnResp.getBody() || '{}');
        return (out.ips && out.ips.length) ? out.ips[0] : '';
    },

    _niosCreateHost: function (fqdn, ip, view) {
        var body = {
            name: fqdn,
            ipv4addrs: [{ ipv4addr: ip }],
            configure_for_dns: true,
            view: view || 'default'
        };
        var resp = this._rest('POST', '/record:host?_return_fields=name', body);
        // WAPI returns the object _ref as a quoted string on create.
        return (resp.getBody() || '').replace(/"/g, '');
    },

    // ---- Universal DDI (Portal) branch -------------------------------------
    _uddiNextAvailableIp: function (cidr, space) {
        // SKELETON — the CIDR is NOT the resource id. Universal DDI addresses objects
        // by an opaque id (e.g. "ipam/subnet/<uuid>"), so resolve the subnet id first
        // — GET /api/ddi/v1/ipam/subnet?_filter=address=='<cidr>' — then call
        // nextavailableip against that id, mirroring the NIOS branch's _ref lookup.
        // (Pin the exact endpoint/shape to your Universal DDI API version before use.)
        var subnetId = this._uddiResolveSubnetId(cidr, space); // resolve id from CIDR
        var body = { count: 1 };
        var resp = this._rest('POST',
            '/api/ddi/v1/' + subnetId + '/nextavailableip', body);
        var out = JSON.parse(resp.getBody() || '{}');
        return (out.results && out.results.length) ? out.results[0].address : '';
    },

    // Resolve a Universal DDI subnet's opaque object id from its CIDR (skeleton;
    // confirm the filter syntax/field against your Universal DDI API version).
    _uddiResolveSubnetId: function (cidr, space) {
        var q = '/api/ddi/v1/ipam/subnet?_filter=' +
            encodeURIComponent("address=='" + cidr + "'") +
            (space ? '&_filter=' + encodeURIComponent("space=='" + space + "'") : '');
        var resp = this._rest('GET', q, null);
        var out = JSON.parse(resp.getBody() || '{}');
        return (out.results && out.results.length) ? out.results[0].id : '';
    },

    _uddiCreateHost: function (fqdn, ip, zone) {
        var body = {
            name_in_zone: fqdn.split('.')[0],
            zone: zone,
            rdata: { address: ip },
            type: 'A'
        };
        var resp = this._rest('POST', '/api/ddi/v1/dns/record', body);
        var out = JSON.parse(resp.getBody() || '{}');
        return (out.result && out.result.id) ? out.result.id : '';
    },

    // ---- transport ----------------------------------------------------------
    _path: function (ref) {
        return this.flavor === 'universal_ddi' ? '/' + ref : '/' + ref;
    },

    _rest: function (method, path, body) {
        var base = (this.flavor === 'universal_ddi')
            ? ''                                   // UDDI paths already absolute under the alias base
            : '/wapi/' + this.wapiVersion;
        var m = new sn_ws.RESTMessageV2('x_infoblox_ddi.infoblox', 'default');
        m.setHttpMethod(method);
        m.setEndpoint(m.getEndpoint() + base + path);
        if (this.midServer) m.setMIDServer(this.midServer);  // keep the call in-boundary
        m.setRequestHeader('Content-Type', 'application/json');
        if (body !== null && body !== undefined)
            m.setRequestBody(JSON.stringify(body));
        var resp = m.execute();
        if (resp.getStatusCode() >= 300)
            this.log.logWarning(method + ' ' + path + ' -> ' + resp.getStatusCode() + ': ' + resp.getBody());
        return resp;
    },

    type: 'InfobloxDDIClient'
};
