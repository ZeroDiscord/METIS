"""
Unified Verifier ν
===================
Single entry point combining all verifier components.
Returns the standard {valid, violated} tuple per CSS §3.

This is D3 (Verifier Implementation) of the case study deliverables.

Usage:
    verifier = CyberIRVerifier()
    report = verifier.verify(proposed_state, evidence_set, constraints)
"""

from __future__ import annotations

import sys
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from verifier.attack_graph_validator import validate_attack_graph
from verifier.ioc_consistency_checker import check_ioc_consistency
from verifier.kill_chain_completeness import check_kill_chain_completeness
from verifier.constraint_checker import check_constraints


@dataclass
class VerifierReport:
    """Standard verifier output per CSS §3."""
    valid: bool
    violated: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sub_reports: dict[str, Any] = field(default_factory=dict)
    coverage: float = 0.0  # % of evidence explained by hypothesis
    duration_ms: float = 0.0  # verifier execution time

    def to_dict(self) -> dict:
        return asdict(self)


class CyberIRVerifier:
    """
    The unified verifier ν for the Cybersecurity IR domain.

    Combines:
    1. ATT&CK Graph Validator (kill-chain ordering + evidence support)
    2. IOC Consistency Checker (temporal + attribution consistency)
    3. Kill-Chain Completeness (no tactical gaps)
    4. Constraint Checker (business/operational constraints)

    All checks are deterministic. No LLM is used. G4-compliant.
    """

    def __init__(self, strict_mode: bool = True):
        """
        Args:
            strict_mode: If True, all sub-verifier violations cause overall failure.
                         If False, only hard-constraint violations cause failure.
        """
        self.strict_mode = strict_mode
        self.call_count = 0

    def verify(
        self,
        proposed_state: dict,
        evidence_set: dict | None = None,
        constraints: list[dict] | None = None,
        ground_truth: dict | None = None,
    ) -> VerifierReport:
        """
        Run all verification checks on the proposed interpretive state.

        Args:
            proposed_state: The agent's current proposed state containing:
                - kill_chain: list[str]         (technique IDs)
                - attributed_group: str          (MITRE group ID)
                - compromised_hosts: list[str]
                - iocs: list[dict]
                - plan_actions: list[dict]
                - evidence_map: dict[str, list]  (technique → evidence items)
                - network_topology: dict | None
            evidence_set: Available evidence items
            constraints: Active constraints
            ground_truth: Optional ground truth for acceptance predicate

        Returns:
            VerifierReport with aggregated results
        """
        self.call_count += 1
        start_time = time.time()

        all_violated = []
        all_warnings = []
        sub_reports = {}

        # ── 1. Attack Graph Validation ───────────────────────────────────
        ag_result = validate_attack_graph(
            kill_chain=proposed_state.get("kill_chain", []),
            attributed_group=proposed_state.get("attributed_group", ""),
            evidence_map=proposed_state.get("evidence_map", {}),
            compromised_hosts=proposed_state.get("compromised_hosts", []),
            network_topology=proposed_state.get("network_topology"),
        )
        sub_reports["attack_graph"] = ag_result
        all_violated.extend(ag_result["violated"])
        all_warnings.extend(ag_result["warnings"])

        # ── 2. IOC Consistency ───────────────────────────────────────────
        ioc_result = check_ioc_consistency(
            iocs=proposed_state.get("iocs", []),
            attributed_group=proposed_state.get("attributed_group", ""),
            timeline_events=proposed_state.get("timeline_events", []),
            verified_evidence=evidence_set.get("verified", []) if evidence_set else None,
        )
        sub_reports["ioc_consistency"] = ioc_result
        all_violated.extend(ioc_result["violated"])
        all_warnings.extend(ioc_result["warnings"])

        # ── 3. Kill-Chain Completeness ───────────────────────────────────
        kc_result = check_kill_chain_completeness(
            kill_chain=proposed_state.get("kill_chain", []),
        )
        sub_reports["kill_chain_completeness"] = kc_result
        all_violated.extend(kc_result["violated"])
        all_warnings.extend(kc_result["warnings"])

        # ── 4. Constraint Checking ───────────────────────────────────────
        if constraints:
            cc_result = check_constraints(
                plan_actions=proposed_state.get("plan_actions", []),
                constraints=constraints,
            )
            sub_reports["constraints"] = cc_result
            all_violated.extend(cc_result["violated"])
            all_warnings.extend(cc_result["warnings"])

        # ── 5. Acceptance Predicate (if ground truth provided) ───────────
        acceptance = {}
        if ground_truth:
            # Check attribution
            attr_match = (
                proposed_state.get("attributed_group", "") ==
                ground_truth.get("threat_actor_group", "")
            )
            acceptance["attribution_correct"] = attr_match
            if not attr_match:
                all_violated.append("attribution_does_not_match_ground_truth")

            # Check scope (compromised hosts)
            gt_hosts = set(ground_truth.get("compromised_hosts", []))
            proposed_hosts = set(proposed_state.get("compromised_hosts", []))
            missing_hosts = gt_hosts - proposed_hosts
            extra_hosts = proposed_hosts - gt_hosts

            acceptance["scope_correct"] = len(missing_hosts) == 0
            acceptance["missing_hosts"] = list(missing_hosts)
            acceptance["extra_hosts"] = list(extra_hosts)

            if missing_hosts:
                all_violated.append(
                    f"missing_compromised_hosts_{'_'.join(sorted(missing_hosts))}"
                )

            # Check initial access technique
            gt_initial = ground_truth.get("initial_access", "")
            proposed_chain = proposed_state.get("kill_chain", [])
            has_correct_initial = gt_initial in proposed_chain
            acceptance["initial_access_correct"] = has_correct_initial
            if not has_correct_initial:
                all_violated.append(
                    f"wrong_initial_access_expected_{gt_initial}"
                )

            sub_reports["acceptance_predicate"] = acceptance

        # ── Compute coverage ─────────────────────────────────────────────
        evidence_items = evidence_set.get("all", []) if evidence_set else []
        explained = proposed_state.get("explained_evidence", [])
        coverage = len(explained) / max(len(evidence_items), 1) if evidence_items else 0.0

        # ── Deduplicate violations ───────────────────────────────────────
        all_violated = list(dict.fromkeys(all_violated))
        all_warnings = list(dict.fromkeys(all_warnings))

        duration_ms = (time.time() - start_time) * 1000

        return VerifierReport(
            valid=len(all_violated) == 0,
            violated=all_violated,
            warnings=all_warnings,
            sub_reports=sub_reports,
            coverage=round(coverage, 3),
            duration_ms=round(duration_ms, 2),
        )

    def reset_call_count(self):
        self.call_count = 0
