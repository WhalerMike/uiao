#!/usr/bin/env python3
"""Assemble the x_infoblox_ddi scoped-app records into ONE importable update set.

Bundles the app's source records — the two Script Includes, the outbound REST
Message, the five catalog variable sets, the four ATF tests, the MID validation
script, and the app's default system properties — into a single ServiceNow
`<unload>` update-set XML with one `<sys_update_xml>` payload per record. The
result (x_infoblox_ddi-update-set.xml) can be pulled in via
"Retrieved Update Sets → Import Update Set from XML" instead of hand-adding each
record.

STARTER SKELETON, and honest about it: this produces an *unsigned* update set.
A cryptographically **signed scoped app** is a ServiceNow Store publishing step,
not something a repo can emit. The payload encoding here (escaped record XML) is
the standard update-set shape, but validate/adjust against your instance version
before relying on a one-click import. Output is deterministic (fixed timestamp)
so re-running does not churn the committed artifact.

Run: python3 servicenow-app/update-set/build-update-set.py
"""

import os
import sys
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))  # .../servicenow-app/update-set
APP = os.path.normpath(os.path.join(HERE, ".."))  # .../servicenow-app
SCOPE = "x_infoblox_ddi"
STAMP = "2026-01-01 00:00:00"  # fixed for deterministic output
OUT = os.path.join(HERE, "x_infoblox_ddi-update-set.xml")

# App default properties shipped with the set (name -> (value, description)).
PROPERTIES = [
    ("x_infoblox_ddi.api_flavor", "nios", "nios | universal_ddi"),
    ("x_infoblox_ddi.wapi_version", "v2.12", "NIOS WAPI version"),
    ("x_infoblox_ddi.mid_server", "", "In-boundary MID Server name"),
    ("x_infoblox_ddi.mid_scripts_dir", "/opt/servicenow/mid/agent/scripts/ddi", "MID scripts dir"),
    ("x_infoblox_ddi.test_mode", "false", "TEST ONLY — canned Infoblox responses for ATF"),
    ("x_infoblox_ddi.test_force_gate_fail", "false", "TEST ONLY — force a gate FAIL verdict"),
    ("x_infoblox_ddi.test_ip", "10.10.8.12", "TEST ONLY — canned next-available IP"),
]


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def sys_update_xml(type_label, target_name, inner_xml):
    """Wrap one record's XML as a <sys_update_xml> payload (escaped, per update-set format)."""
    return (
        '  <sys_update_xml action="INSERT_OR_UPDATE">\n'
        f"    <name>{escape(type_label)}_{escape(target_name)}</name>\n"
        f"    <type>{escape(type_label)}</type>\n"
        f"    <target_name>{escape(target_name)}</target_name>\n"
        f"    <application>{SCOPE}</application>\n"
        "    <update_set/>\n"
        f"    <payload>{escape(inner_xml)}</payload>\n"
        "  </sys_update_xml>\n"
    )


def script_include_record(name, js):
    """A sys_script_include record_update payload carrying the JS in <script>."""
    return (
        '<record_update table="sys_script_include">\n'
        '  <sys_script_include action="INSERT_OR_UPDATE">\n'
        f"    <name>{name}</name>\n"
        f"    <api_name>{SCOPE}.{name}</api_name>\n"
        "    <active>true</active>\n"
        "    <access>package_private</access>\n"
        f"    <sys_scope>{SCOPE}</sys_scope>\n"
        f"    <script>{escape(js)}</script>\n"
        "  </sys_script_include>\n"
        "</record_update>"
    )


def property_record(name, value, desc):
    return (
        '<record_update table="sys_properties">\n'
        '  <sys_properties action="INSERT_OR_UPDATE">\n'
        f"    <name>{escape(name)}</name>\n"
        f"    <value>{escape(value)}</value>\n"
        f"    <description>{escape(desc)}</description>\n"
        "    <type>string</type>\n"
        f"    <sys_scope>{SCOPE}</sys_scope>\n"
        "  </sys_properties>\n"
        "</record_update>"
    )


def main():
    parts = []

    # 1) Script Includes
    for fname, cls in [
        ("script-includes/InfobloxDDIClient.js", "InfobloxDDIClient"),
        ("script-includes/InfobloxDDIGate.js", "InfobloxDDIGate"),
    ]:
        parts.append(sys_update_xml("Script Include", cls, script_include_record(cls, read(os.path.join(APP, fname)))))

    # 2) Record-XML files bundled verbatim as payloads
    xml_records = [
        ("REST Message", "Infoblox DDI", "update-set/sys_rest_message_infoblox.xml"),
        ("Variable Set", "DDI-backed subnet (azure)", "catalog/variable-set-azure-ddi-subnet.xml"),
        ("Variable Set", "DDI-backed subnet (aws)", "catalog/variable-set-aws-ddi-subnet.xml"),
        ("Variable Set", "DDI-backed subnet (gcp)", "catalog/variable-set-gcp-ddi-subnet.xml"),
        ("Variable Set", "DDI-backed subnet (oci)", "catalog/variable-set-oci-ddi-subnet.xml"),
        ("Variable Set", "DDI-backed subnet (vmware)", "catalog/variable-set-vmware-ddi-subnet.xml"),
        ("ATF Test", "provision happy path", "atf/atf-provision-happy-path.xml"),
        ("ATF Test", "negative gate fail", "atf/atf-negative-gate-fail.xml"),
        ("ATF Test", "negative saas boundary", "atf/atf-negative-saas-boundary.xml"),
        ("ATF Test", "negative self approve", "atf/atf-negative-self-approve.xml"),
    ]
    for label, target, rel in xml_records:
        parts.append(sys_update_xml(label, target, read(os.path.join(APP, rel))))

    # 3) App properties
    for name, value, desc in PROPERTIES:
        parts.append(sys_update_xml("System Property", name, property_record(name, value, desc)))

    header = (
        '  <sys_remote_update_set action="INSERT_OR_UPDATE">\n'
        f"    <name>Infoblox DDI ({SCOPE}) — assembled starter</name>\n"
        f"    <application>{SCOPE}</application>\n"
        "    <description>Assembled by build-update-set.py — Script Includes, REST Message, "
        "5 catalog variable sets, 4 ATF tests, and default app properties. UNSIGNED starter; "
        "verify payload encoding against your instance.</description>\n"
        "    <state>loaded</state>\n"
        f"    <sys_created_on>{STAMP}</sys_created_on>\n"
        "  </sys_remote_update_set>\n"
    )

    doc = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<unload unload_date="{STAMP}">\n' + header + "".join(parts) + "</unload>\n"
    )

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(doc)
    print(f"wrote {OUT} ({len(parts)} records bundled)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
