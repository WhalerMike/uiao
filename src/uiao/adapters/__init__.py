"""
UIAO-Core Adapters Package.

All adapter classes are exported here for convenient import.
Adapters are DNS-style alignment resolvers -- they do NOT perform
heavy OSCAL/SBOM/SSP conversions. That work lives in generators/.
"""

# InfobloxAdapter export verified 2026-04-19 (task 6/6, PR #98)
from .cyberark_adapter import CyberArkAdapter
from .database_base import DatabaseAdapterBase
from .entra_adapter import EntraAdapter
from .infoblox_adapter import InfobloxAdapter
from .intune_adapter import IntuneAdapter
from .m365_adapter import M365Adapter
from .mainframe_adapter import MainframeAdapter
from .paloalto_adapter import PaloAltoAdapter
from .patchstate_adapter import PatchStateAdapter
from .pkica_adapter import PkiCaAdapter
from .scubagear_adapter import ScubaGearAdapter
from .servicenow_adapter import ServiceNowAdapter
from .siem_adapter import SiemAdapter
from .stigcompliance_adapter import StigComplianceAdapter
from .terraform_adapter import TerraformAdapter
from .vulnscan_adapter import VulnScanAdapter

__all__ = [
    "CyberArkAdapter",
    "DatabaseAdapterBase",
    "EntraAdapter",
    "InfobloxAdapter",
    "IntuneAdapter",
    "M365Adapter",
    "MainframeAdapter",
    "PaloAltoAdapter",
    "PatchStateAdapter",
    "PkiCaAdapter",
    "ScubaGearAdapter",
    "ServiceNowAdapter",
    "SiemAdapter",
    "StigComplianceAdapter",
    "TerraformAdapter",
    "VulnScanAdapter",
]
