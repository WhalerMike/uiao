from datetime import datetime
from typing import Dict, Any, Type
from pydantic import BaseModel

# --- Core Provider Adapters ---
from core.providers.entra.entra_adapter import EntraIDAdapter
from core.providers.azure.azure_adapter import AzureResourceGraphAdapter
from core.providers.aws.aws_adapter import AWSConfigAdapter
from core.providers.m365.m365_adapter import M365ComplianceAdapter
from core.providers.github.github_adapter import GitHubAdapter
from core.providers.servicenow.servicenow_adapter import ServiceNowAdapter

# --- Entra Sub-Provider Adapters (Task 31 Expansion) ---
from core.providers.entra.npi_adapter import NPIAdapter
from core.providers.entra.ad_groups_adapter import ADGroupsAdapter
from core.providers.entra.kerberos_adapter import KerberosAdapter
from core.providers.entra.intune_adapter import IntuneAdapter


class ProviderHealth(BaseModel):
        provider: str
        healthy: bool
        checked_at: datetime
        details: Dict[str, Any]


class ProviderRegistry:
        """
            Deterministic provider registry for UIAO-GOS.
                Maps provider names to adapter classes.
                    Supports core providers and Entra sub-providers
                        (NPI, AD Groups, Kerberos, Intune).

                            Classification: Controlled | Boundary: GCC-Moderate
                                """

    def __init__(self):
                self._registry: Dict[str, Type] = {}

        # Core providers
                self.register("entra", EntraIDAdapter)
                self.register("azure", AzureResourceGraphAdapter)
                self.register("aws", AWSConfigAdapter)
                self.register("m365", M365ComplianceAdapter)
                self.register("github", GitHubAdapter)
                self.register("servicenow", ServiceNowAdapter)

        # Entra sub-providers (Task 31)
                self.register("entra_npi", NPIAdapter)
                self.register("entra_ad_groups", ADGroupsAdapter)
                self.register("entra_kerberos", KerberosAdapter)
                self.register("entra_intune", IntuneAdapter)

    def register(self, name: str, adapter_cls: Type):
                self._registry[name] = adapter_cls

    def get(self, name: str) -> Type:
                if name not in self._registry:
                                raise KeyError(f"No provider registered for: {name}")
                            return self._registry[name]

    def list(self) -> Dict[str, Type]:
                return dict(self._registry)

    def list_entra_subproviders(self) -> Dict[str, Type]:
                """Return only Entra sub-provider adapters."""
        return {
                        k: v for k, v in self._registry.items()
                        if k.startswith("entra_")
        }

    def healthcheck_all(self) -> list:
                """Run healthcheck across all registered providers."""
        results = []
        for name, adapter_cls in self._registry.items():
                        adapter = adapter_cls()
                        health = adapter.healthcheck()
                        results.append(ProviderHealth(
                                            provider=name,
                            healthy=health.get("healthy", False),
                            checked_at=datetime.utcnow(),
                            details=health
            ))
        return results
            
