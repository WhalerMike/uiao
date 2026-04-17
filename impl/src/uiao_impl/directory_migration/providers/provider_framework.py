from datetime import datetime
from typing import Dict

from core.providers.provider_registry import ProviderRegistry
from core.providers.provider_metadata import ProviderMetadata
from core.providers.provider_health import ProviderHealth


class ProviderFramework:
    """
        Deterministic provider expansion framework.
            Allows UIAO-GOS to query provider metadata and health.
                """

                    def __init__(self):
                            self.registry = ProviderRegistry()

                                def metadata(self) -> Dict[str, ProviderMetadata]:
                                        result = {}
                                                for name, adapter_cls in self.registry.list().items():
                                                            adapter = adapter_cls()
                                                                        result[name] = ProviderMetadata(
                                                                                        name=name,
                                                                                                        version=getattr(adapter, "version", "0.1.0"),
                                                                                                                        capabilities=getattr(adapter, "capabilities", []),
                                                                                                                                        details={},
                                                                                                                                                    )
                                                                                                                                                            return result

                                                                                                                                                                def health(self) -> Dict[str, ProviderHealth]:
                                                                                                                                                                        result = {}
                                                                                                                                                                                for name, adapter_cls in self.registry.list().items():
                                                                                                                                                                                            adapter = adapter_cls()
                                                                                                                                                                                                        try:
                                                                                                                                                                                                                        healthy = adapter.health_check()
                                                                                                                                                                                                                                        result[name] = ProviderHealth(
                                                                                                                                                                                                                                                            provider=name,
                                                                                                                                                                                                                                                                                healthy=bool(healthy),
                                                                                                                                                                                                                                                                                                    checked_at=datetime.utcnow(),
                                                                                                                                                                                                                                                                                                                        details={"raw": healthy},
                                                                                                                                                                                                                                                                                                                                        )
                                                                                                                                                                                                                                                                                                                                                    except Exception as e:
                                                                                                                                                                                                                                                                                                                                                                    result[name] = ProviderHealth(
                                                                                                                                                                                                                                                                                                                                                                                        provider=name,
                                                                                                                                                                                                                                                                                                                                                                                                            healthy=False,
                                                                                                                                                                                                                                                                                                                                                                                                                                checked_at=datetime.utcnow(),
                                                                                                                                                                                                                                                                                                                                                                                                                                                    details={"error": str(e)},
                                                                                                                                                                                                                                                                                                                                                                                                                                                                    )
                                                                                                                                                                                                                                                                                                                                                                                                                                                                            return result
                                                                                                                                                                                                                                                                                                                                                                                                                                                                            