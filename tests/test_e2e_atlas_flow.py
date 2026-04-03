import unittest
from unittest.mock import patch, MagicMock

from scripts.enforcement_orchestrator import NetworkEnforcer


class TestE2EAtlasFlow(unittest.TestCase):
    @patch.object(NetworkEnforcer, "_get_vmanage_session", return_value=MagicMock())
    @patch.object(NetworkEnforcer, "update_palo_alto_dag")
    @patch.object(NetworkEnforcer, "quarantine_ip_sdwan")
    def test_leaver_quarantine_flow(self, mock_sdwan, mock_palo, mock_session):
        # 1. Simulate a Sentinel "Leaver" signal for James Vance (Slide 6)
        mock_ip = "10.50.22.101"
        enforcer = NetworkEnforcer()

        # 2. Trigger enforcement
        enforcer.update_palo_alto_dag(mock_ip, action="add")
        enforcer.quarantine_ip_sdwan(mock_ip)

        # 3. Verify actions were taken
        mock_palo.assert_called_once_with(mock_ip, action="add")
        mock_sdwan.assert_called_once_with(mock_ip)


if __name__ == "__main__":
    unittest.main()
