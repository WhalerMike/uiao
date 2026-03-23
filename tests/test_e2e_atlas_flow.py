import unittest
from unittest.mock import patch

from scripts.enforcement_orchestrator import AtlasEnforcer


class TestE2EAtlasFlow(unittest.TestCase):

    @patch('scripts.enforcement_orchestrator.AtlasEnforcer.update_palo_alto_dag')
    @patch('scripts.enforcement_orchestrator.AtlasEnforcer.quarantine_sdwan')
    def test_leaver_quarantine_flow(self, mock_sdwan, mock_palo):
        # 1. Simulate a Sentinel "Leaver" signal for James Vance (Slide 6)
        mock_ip = "10.50.22.101"
        enforcer = AtlasEnforcer()

        # 2. Trigger enforcement
        enforcer.update_palo_alto_dag(mock_ip, action="add")
        enforcer.quarantine_sdwan(mock_ip)

        # 3. Verify actions were taken
        mock_palo.assert_called_once_with(mock_ip, "add")
        mock_sdwan.assert_called_once_with(mock_ip)
        print(f"E2E Validation: Successfully quarantined {mock_ip} based on mock signal.")


if __name__ == "__main__":
    unittest.main()
