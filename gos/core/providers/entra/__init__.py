"""UIAO-GOS Entra Provider Package

Canon-aligned provider adapters for Microsoft Entra ID governance.
Classification: Controlled | Boundary: GCC-Moderate

Providers:
    - EntraAdapter: Core Entra ID identity governance
        - NPIAdapter: Non-Person Identity (service principals, managed identities, workload identities)
            - ADGroupsAdapter: All AD group types (security, distribution, M365, dynamic, administrative units)
                - KerberosAdapter: Kerberos authentication governance (SPNs, keytabs, delegation, realm trusts)
                    - IntuneAdapter: Entra Intune device compliance and configuration governance
                    """

from .entra_adapter import EntraAdapter
from .npi_adapter import NPIAdapter
from .ad_groups_adapter import ADGroupsAdapter
from .kerberos_adapter import KerberosAdapter
from .intune_adapter import IntuneAdapter

__all__ = [
      "EntraAdapter",
      "NPIAdapter",
      "ADGroupsAdapter",
      "KerberosAdapter",
      "IntuneAdapter",
]

PROVIDER_REGISTRY = {
      "entra.identity": EntraAdapter,
      "entra.npi": NPIAdapter,
      "entra.groups": ADGroupsAdapter,
      "entra.kerberos": KerberosAdapter,
      "entra.intune": IntuneAdapter,
}
