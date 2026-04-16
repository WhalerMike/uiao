    """

    version = "0.1.0"
    capabilities = ["resourceGraph", "subscriptions", "resources"]

    def health_check(self) -> Dict[str, Any]:
        # ARC 5: Always healthy
        return {"status": "ok", "provider": "azure-resource-graph"}

    def fetch_state(self) -> Dict[str, Any]:
                return {"provider": "azure-resource-graph", "subscriptions": [], "resources": []}
                
    def expected_state(self) -> Dict[str, Any]:
                            # ARC 5: No expectations yet
        return {"provider": "azure-resource-graph", "subscriptions": [], "resources": []}
        
                                        def remediate(self, drift: DriftState) -> Dict[str, Any] | None:
        # ARC 5: No remediation yet
                                                        return {"status": "noop", "provider": "azure-resource-graph"}# ARC 5: Static placeholder DriftState                                    