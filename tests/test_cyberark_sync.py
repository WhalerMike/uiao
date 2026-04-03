import json
import unittest
from unittest.mock import MagicMock, patch

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from cyberark_sync_orchestrator import SyncOrchestrator


TEST_DIR = os.path.dirname(os.path.abspath(__file__))

def load_mock(filename):
    filepath = os.path.join(TEST_DIR, "data", filename)
    with open(filepath) as f:
        return json.load(f)


class TestCyberArkSync(unittest.TestCase):
    @patch("requests.post")
    @patch("requests.get")
    @patch("requests.patch")
    def test_full_pipeline(self, mock_patch, mock_get, mock_post):
        # 1. Setup Mock Data
        mock_ca_accounts = load_mock("mock_cyberark.json")

        # Simulate ServiceNow finding the first account but not the second
        mock_sn_lookup_exists = {"result": [{"sys_id": "sn_999", "correlation_id": "123_45_6789_admin"}]}
        mock_sn_lookup_empty = {"result": []}

        # 2. Define Mock Behavior
        # First POST: CyberArk Logon (Returns Token)
        # Second POST: ServiceNow Insert (For the new record)
        mock_post.side_effect = [
            MagicMock(status_code=200, text='"mock_token_abc_123"'),  # CyberArk Logon
            MagicMock(status_code=201),  # ServiceNow Create
        ]

        # First GET: CyberArk Accounts
        # Second GET: SN Lookup (Exists)
        # Third GET: SN Lookup (New)
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: mock_ca_accounts),
            MagicMock(status_code=200, json=lambda: mock_sn_lookup_exists),
            MagicMock(status_code=200, json=lambda: mock_sn_lookup_empty),
        ]

        # 3. Run the Orchestrator (Dry Run = False to test write calls)
        print("Starting CyberArk Sync Validation...")
        orchestrator = SyncOrchestrator(dry_run=False)
        orchestrator.run()

        # 4. Assertions
        self.assertEqual(orchestrator.summary.total_processed, 2)
        self.assertEqual(orchestrator.summary.updated, 1)
        self.assertEqual(orchestrator.summary.created, 1)

        # Verify specific API calls
        self.assertTrue(mock_patch.called, "Should have called PATCH for existing account")
        self.assertTrue(mock_post.called, "Should have called POST for new account")
        print("Validation Successful: CyberArk-to-ServiceNow logic verified.")


if __name__ == "__main__":
    unittest.main()
