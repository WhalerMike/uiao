"""Parser helpers for the MS SQL Estate Inventory Adapter.

Two normalization entry points:

* :func:`normalize_spn_record` — parses an ``MSSQLSvc/*`` SPN record from
  the AD survey output into a :class:`MSSQLInstanceClaim`.
* :func:`normalize_arg_resource` — parses an Azure Resource Graph row
  for an MS-SQL-family resource type into a :class:`MSSQLInstanceClaim`.

Both return ``None`` for records the parser cannot recognize, signalling
the adapter to skip them silently. Failure here is not an exception path —
unrecognized records are common in heterogeneous federal estates (third-
party SPNs, exotic resource types, malformed ARM tags) and the right
behavior is to skip with a log line, not to abort the run.

OrgPath attribution cascade (per UIAO_153 / ADR-063):

1. Owning principal's ``extensionAttribute1`` (SPN path).
2. Hosting computer's ``extensionAttribute1`` (SPN fallback).
3. ARM tag ``OrgPath`` on the resource (ARG path).
4. ``ORG-BRANCH-UNPOSITIONED`` (signals ``DRIFT-IDENTITY``).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ``MSSQLSvc/host.fqdn:1433`` or ``MSSQLSvc/host.fqdn:INSTANCE_NAME``
_SPN_MSSQL_PATTERN = re.compile(
    r"^MSSQLSvc/(?P<host>[A-Za-z0-9_.-]+?)(?::(?P<port_or_instance>[A-Za-z0-9_-]+))?$"
)

# ARM resource-type → MSSQLInstanceClaim source enum mapping.
_ARG_TYPE_TO_SOURCE = {
    "microsoft.sql/servers": "arg-azure-sql",
    "microsoft.sql/servers/databases": "arg-azure-sql",
    "microsoft.sql/managedinstances": "arg-managed-instance",
    "microsoft.sql/managedinstances/databases": "arg-managed-instance",
    "microsoft.azurearcdata/sqlserverinstances": "arg-arc-sql",
    "microsoft.sqlvirtualmachine/sqlvirtualmachines": "arg-sql-on-vm",
}

ORGPATH_UNPOSITIONED = "ORG-BRANCH-UNPOSITIONED"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_spn_record(record: Dict[str, Any]) -> Optional[Any]:
    """Normalize a single AD-survey SPN record into an MSSQLInstanceClaim.

    Expected input shape (per ``survey.extract_spn_inventory``):

    .. code-block:: python

        {
          "servicePrincipalName": "MSSQLSvc/sqlsvr01.corp.example:1433",
          "principal_name": "CORP\\svc-sqlsvr01",
          "principal_extension_attribute_1": "ORG-CORP-US-EAST-FIN",
          "host_dn": "CN=SQLSVR01,OU=Servers,DC=corp,DC=example",
          "host_extension_attribute_1": "ORG-CORP-US-EAST",
          ...
        }

    Returns ``None`` if the SPN does not match ``MSSQLSvc/*``.
    """
    # Import here to avoid a circular import between adapter and parser.
    from .mssql_inventory_adapter import MSSQLInstanceClaim

    spn = record.get("servicePrincipalName") or record.get("spn")
    if not spn or not isinstance(spn, str):
        return None
    match = _SPN_MSSQL_PATTERN.match(spn)
    if not match:
        return None

    host = match.group("host")
    port_or_instance = match.group("port_or_instance")
    port: Optional[int] = None
    instance_name: Optional[str] = None
    if port_or_instance is not None:
        if port_or_instance.isdigit():
            port = int(port_or_instance)
        else:
            instance_name = port_or_instance

    owning_principal = record.get("principal_name") or record.get("owning_principal")

    # OrgPath attribution cascade.
    orgpath = record.get("principal_extension_attribute_1")
    attribution_source = "principal-extension"
    if not orgpath:
        orgpath = record.get("host_extension_attribute_1")
        attribution_source = "host-extension"
    if not orgpath:
        orgpath = ORGPATH_UNPOSITIONED
        attribution_source = "unpositioned"

    identifier = (
        f"{host}\\{instance_name}" if instance_name else f"{host}:{port or 1433}"
    )

    return MSSQLInstanceClaim(
        identifier=identifier,
        source="ad-spn",
        host=host,
        port=port,
        instance_name=instance_name,
        owning_principal=owning_principal,
        orgpath=orgpath,
        orgpath_attribution_source=attribution_source,
        azure_resource_id=None,
        azure_resource_type=None,
        azure_subscription_id=None,
        azure_location=None,
        discovered_at=_now_iso(),
    )


def normalize_arg_resource(record: Dict[str, Any]) -> Optional[Any]:
    """Normalize an Azure Resource Graph row into an MSSQLInstanceClaim.

    Expected input shape (the ARG query output projected by
    :data:`uiao.adapters.mssql_inventory_adapter.ARG_QUERY_MSSQL_RESOURCES`):

    .. code-block:: python

        {
          "id": "/subscriptions/.../providers/Microsoft.Sql/servers/foo",
          "name": "foo",
          "type": "microsoft.sql/servers",
          "location": "eastus2",
          "resourceGroup": "rg-fin",
          "subscriptionId": "12345...",
          "properties": {...},
          "tags": {"OrgPath": "ORG-CORP-US-EAST-FIN", ...},
          "orgpath": "ORG-CORP-US-EAST-FIN"   # projected from tags['OrgPath']
        }

    Returns ``None`` if the ARM type is not a recognized MS SQL family.
    """
    from .mssql_inventory_adapter import MSSQLInstanceClaim

    rtype_raw = record.get("type")
    if not rtype_raw or not isinstance(rtype_raw, str):
        return None
    rtype = rtype_raw.lower()
    source = _ARG_TYPE_TO_SOURCE.get(rtype)
    if source is None:
        return None

    arm_id = record.get("id")
    name = record.get("name")
    if not arm_id or not name:
        return None

    # OrgPath from ARM tag projection.
    orgpath_raw = record.get("orgpath")
    if not orgpath_raw:
        tags = record.get("tags") or {}
        orgpath_raw = tags.get("OrgPath") or tags.get("orgpath")
    if orgpath_raw:
        orgpath = str(orgpath_raw)
        attribution_source = "arm-tag"
    else:
        orgpath = ORGPATH_UNPOSITIONED
        attribution_source = "unpositioned"

    return MSSQLInstanceClaim(
        identifier=str(arm_id),
        source=source,
        host=None,  # ARM resources don't expose host in this query shape
        port=None,
        instance_name=str(name),
        owning_principal=None,  # cloud resources resolve identity via managed identity, not principal_name
        orgpath=orgpath,
        orgpath_attribution_source=attribution_source,
        azure_resource_id=str(arm_id),
        azure_resource_type=rtype,
        azure_subscription_id=record.get("subscriptionId"),
        azure_location=record.get("location"),
        discovered_at=_now_iso(),
    )
