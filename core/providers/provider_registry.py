from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel

from core.providers.entra.entra_adapter import EntraIDAdapter
from core.providers.azure.azure_adapter import AzureResourceGraphAdapter
from core.providers.aws.aws_adapter import AWSConfigAdapter

class ProviderHealth(BaseModelfrom typing import Dict, Type


class ProviderRegistry:
    """
        Minimal deterministic provider registry.
            Maps provider names to adapter classes.
                Early UIAO-GOS ships with a demo adapter.
                    """
                    
                        def __init__(self):
                                self._registry: Dict[str, Type] = {}
        self.register("entra", EntraIDAdapter)                                
        self.register("azure", AzureResourceGraphAdapter)                                
        self.register("aws", AWSConfigAdapter)        
                                    def register(self, name: str, adapter_cls: Type):
                                            self._registry[name] = adapter_cls
                                            
                                                def get(self, name: str) -> Type:
                                                        if name not in self._registry:
                                                                    raise KeyError(f"No provider registered for: {name}")
                                                                            return self._registry[name]
                                                                            
                                                                                def list(self) -> Dict[str, Type]:
                                                                                        return dict(self._registry)
                                                                                        ):
    provider: str
        healthy: bool
            checked_at: datetime
                details: Dict[str, Any]
                