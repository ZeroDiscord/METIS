"""
Unit Tests for Deterministic Cybersecurity IR Verifier Suite
============================================================
Tests D3 verifier components:
1. ATT&CK Graph Validator
2. IOC Consistency Checker
3. Kill Chain Completeness Checker
4. Constraint Checker
5. Unified CyberIRVerifier
"""

import unittest
import os
import sys

# Ensure paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from verifier.attack_graph_validator import validate_attack_graph
from verifier.ioc_consistency_checker import check_ioc_consistency
from verifier.kill_chain_completeness import check_kill_chain_completeness
from verifier.constraint_checker import check_constraints
from verifier.verifier import CyberIRVerifier


class TestAttackGraphValidator(unittest.TestCase):
    def test_valid_attack_graph(self):
        kill_chain = ["T1566.001", "T1059.001", "T1071.001", "T1041"]
        evidence_map = {
            "T1566.001": ["ev-phishing"],
            "T1059.001": ["ev-powershell"],
            "T1071.001": ["ev-c2"],
            "T1041": ["ev-exfil"],
        }
        res = validate_attack_graph(
            kill_chain=kill_chain,
            attributed_group="G0007",
            evidence_map=evidence_map,
            compromised_hosts=["HOST-1"],
        )
        self.assertTrue(res["valid"])
        self.assertEqual(len(res["violated"]), 0)

    def test_invalid_technique_order(self):
        # Exfiltration before Initial Access
        kill_chain = ["T1041", "T1566.001"]
        evidence_map = {"T1041": ["ev1"], "T1566.001": ["ev2"]}
        res = validate_attack_graph(
            kill_chain=kill_chain,
            attributed_group="G0007",
            evidence_map=evidence_map,
            compromised_hosts=["HOST-1"],
        )
        self.assertFalse(res["valid"])
        self.assertTrue(any("ordering_violation" in v for v in res["violated"]))

    def test_missing_evidence(self):
        kill_chain = ["T1566.001", "T1059.001"]
        evidence_map = {"T1566.001": ["ev1"]}  # T1059.001 missing evidence
        res = validate_attack_graph(
            kill_chain=kill_chain,
            attributed_group="G0007",
            evidence_map=evidence_map,
            compromised_hosts=["HOST-1"],
        )
        self.assertFalse(res["valid"])
        self.assertIn("missing_evidence_for_T1059.001", res["violated"])


class TestIOCConsistencyChecker(unittest.TestCase):
    def test_consistent_iocs(self):
        iocs = [
            {"id": "ioc1", "type": "ip", "value": "198.51.100.42", "attributed_groups": ["G0007"], "first_seen": "2024-01-01"},
            {"id": "ioc2", "type": "hash", "value": "abc123hash", "attributed_groups": ["G0007"], "first_seen": "2024-01-02"},
        ]
        res = check_ioc_consistency(iocs=iocs, attributed_group="G0007")
        self.assertTrue(res["valid"])

    def test_temporal_inconsistency(self):
        timeline = [
            {"event": "C2 callback", "timestamp": "2024-01-01T10:00:00Z", "phase": "c2"},
            {"event": "Phishing email clicked", "timestamp": "2024-01-01T11:00:00Z", "phase": "initial_access"},
        ]
        res = check_ioc_consistency(iocs=[], attributed_group="G0007", timeline_events=timeline)
        self.assertFalse(res["valid"])
        self.assertTrue(any("temporal_order_violation" in v for v in res["violated"]))


class TestKillChainCompleteness(unittest.TestCase):
    def test_complete_kill_chain(self):
        chain = ["T1566.001", "T1059.001", "T1071.001"]
        res = check_kill_chain_completeness(chain)
        self.assertTrue(res["valid"])

    def test_missing_execution(self):
        # Entry + C2 without execution
        chain = ["T1566.001", "T1071.001"]
        res = check_kill_chain_completeness(chain)
        self.assertFalse(res["valid"])
        self.assertIn("missing_execution_tactic", res["violated"])

    def test_missing_initial_access(self):
        chain = ["T1059.001", "T1071.001"]
        res = check_kill_chain_completeness(chain)
        self.assertFalse(res["valid"])
        self.assertIn("missing_initial_access_or_entry_tactic", res["violated"])


class TestConstraintChecker(unittest.TestCase):
    def test_availability_constraint_violation(self):
        actions = [
            {"id": "act-1", "action": "isolate_server_from_network", "target": "PORTAL-WEB-01"}
        ]
        constraints = [
            {"id": "K1", "type": "system_availability", "protected_system": "PORTAL-WEB-01", "hard": True, "text": "Keep portal online"}
        ]
        res = check_constraints(actions, constraints)
        self.assertFalse(res["valid"])
        self.assertIn("K1", res["violated"])
        self.assertIn("disrupt", res["details"]["K1"]["details"])

    def test_evidence_preservation_violation(self):
        actions = [
            {"id": "act-1", "action": "reimage_endpoint", "target": "HOST-01"}
        ]
        constraints = [
            {"id": "K2", "type": "evidence_preservation", "hard": True, "text": "Preserve evidence"}
        ]
        res = check_constraints(actions, constraints)
        self.assertFalse(res["valid"])
        self.assertIn("K2", res["violated"])


class TestCyberIRVerifier(unittest.TestCase):
    def setUp(self):
        self.verifier = CyberIRVerifier()

    def test_unified_verification_pass(self):
        state = {
            "attributed_group": "G0007",
            "kill_chain": ["T1566.001", "T1059.001", "T1071.001"],
            "compromised_hosts": ["WORKSTATION-12"],
            "plan_actions": [{"id": "a1", "action": "forensic_image", "target": "WORKSTATION-12"}],
            "evidence_map": {
                "T1566.001": ["ev1"],
                "T1059.001": ["ev2"],
                "T1071.001": ["ev3"],
            },
            "explained_evidence": ["ev1", "ev2", "ev3"],
        }
        evidence_set = {"all": ["ev1", "ev2", "ev3"], "verified": []}
        report = self.verifier.verify(state, evidence_set=evidence_set)
        self.assertTrue(report.valid)
        self.assertEqual(len(report.violated), 0)


if __name__ == "__main__":
    unittest.main()
