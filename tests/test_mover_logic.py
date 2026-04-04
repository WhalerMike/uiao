"""Tests for ABAC Mover Logic - Sarah Miller Dept 400 -> 800 Transition.

Validates that the JML canon correctly defines the revoke/grant actions
for an internal department transfer scenario.
"""

import os
import unittest

import yaml


class TestMoverLogic(unittest.TestCase):
    """Validates the Mover transition rules in the JML Logic Canon."""

    @classmethod
    def setUpClass(cls):
        """Load the JML Logic Canon YAML."""
        canon_path = os.path.join(os.path.dirname(__file__), "..", "generation-inputs", "uiao_jml_logic_v1.0.yaml")
        with open(canon_path) as f:
            cls.logic = yaml.safe_load(f)

    def test_mover_trigger_is_department_change(self):
        """Verify the mover logic triggers on Department_Change."""
        mover = self.logic["jml_transitions"]["mover_logic"]
        self.assertEqual(mover["trigger"], "Department_Change")

    def test_sarah_miller_transition_exists(self):
        """Verify the Dept_400_Field -> Dept_800_Cyber action exists."""
        actions = self.logic["jml_transitions"]["mover_logic"]["actions"]
        sarah_action = None
        for action in actions:
            if action["from"] == "Dept_400_Field" and action["to"] == "Dept_800_Cyber":
                sarah_action = action
                break
        self.assertIsNotNone(sarah_action, "Sarah Miller transition (400->800) not found in canon.")

    def test_sarah_miller_revoke_groups(self):
        """Verify Field_Ops_Access is revoked on Dept 400 -> 800 move."""
        actions = self.logic["jml_transitions"]["mover_logic"]["actions"]
        sarah_action = [a for a in actions if a["from"] == "Dept_400_Field"][0]
        self.assertIn("Field_Ops_Access", sarah_action["revoke_groups"])

    def test_sarah_miller_grant_groups(self):
        """Verify Policy_Analyst_Access and Sentinel_Contributors are granted."""
        actions = self.logic["jml_transitions"]["mover_logic"]["actions"]
        sarah_action = [a for a in actions if a["from"] == "Dept_400_Field"][0]
        self.assertIn("Policy_Analyst_Access", sarah_action["grant_groups"])
        self.assertIn("Sentinel_Contributors", sarah_action["grant_groups"])

    def test_revoke_and_grant_are_mutually_exclusive(self):
        """Ensure no group appears in both revoke and grant lists."""
        actions = self.logic["jml_transitions"]["mover_logic"]["actions"]
        for action in actions:
            revoked = set(action["revoke_groups"])
            granted = set(action["grant_groups"])
            overlap = revoked & granted
            self.assertEqual(len(overlap), 0, f"Overlap detected in {action['from']}->{action['to']}: {overlap}")

    def test_leaver_sla_under_threshold(self):
        """Verify leaver revocation SLA is <= 120 seconds."""
        leaver = self.logic["jml_transitions"]["leaver_logic"]
        self.assertLessEqual(leaver["sla_seconds"], 120)

    def test_leaver_enforcement_includes_network_quarantine(self):
        """Verify network quarantine is part of leaver enforcement."""
        enforcement = self.logic["jml_transitions"]["leaver_logic"]["enforcement"]
        self.assertIn("Network_Quarantine_IP", enforcement)

    def test_joiner_provisioning_steps(self):
        """Verify joiner logic includes all required provisioning steps."""
        joiner = self.logic["jml_transitions"]["joiner_logic"]
        required_steps = [
            "Create_Entra_ID_Account",
            "Assign_Dynamic_Groups",
            "Provision_Intune_Device",
            "Issue_PIV_Card",
        ]
        for step in required_steps:
            self.assertIn(step, joiner["provisioning"], f"Missing provisioning step: {step}")


if __name__ == "__main__":
    print("Running ABAC Mover Logic Validation...")
    unittest.main(verbosity=2)
