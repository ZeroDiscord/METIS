"""
ATT&CK Graph Validator
======================
Validates proposed kill chains against MITRE ATT&CK tactical ordering,
evidence support requirements, and technique-evidence consistency.

Part of the deterministic verifier suite (no LLM, G4-compliant).
"""

from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.attck_knowledge_base import (
    TECHNIQUES, TACTIC_INDEX, TACTIC_NAMES,
    get_tactic_for_technique, validate_kill_chain_order,
    is_technique_consistent_with_group, GROUPS,
)


def validate_attack_graph(
    kill_chain: list[str],
    attributed_group: str,
    evidence_map: dict[str, list[str]],
    compromised_hosts: list[str],
    network_topology: dict[str, list[str]] | None = None,
) -> dict:
    """
    Validate a proposed attack graph (kill chain + attribution + scope).

    Args:
        kill_chain: Ordered list of technique IDs (proposed kill chain)
        attributed_group: MITRE group ID (e.g., "G0096" for APT41)
        evidence_map: {technique_id: [evidence_item_ids]} — which evidence
                      supports each claimed technique
        compromised_hosts: List of host identifiers claimed as compromised
        network_topology: Optional {host: [reachable_hosts]} for lateral
                          movement validation

    Returns:
        {
            "valid": bool,
            "violated": [constraint_id_strings],
            "warnings": [warning_strings],
            "details": {per-check results}
        }
    """
    violated = []
    warnings = []
    details = {}

    # ── Check 1: All techniques must be known ────────────────────────────
    unknown = [t for t in kill_chain if t not in TECHNIQUES]
    if unknown:
        violated.extend([f"unknown_technique_{t}" for t in unknown])
    details["unknown_techniques"] = unknown

    # ── Check 2: Tactical ordering must be valid ─────────────────────────
    known_chain = [t for t in kill_chain if t in TECHNIQUES]
    order_valid, order_violations = validate_kill_chain_order(known_chain)
    if not order_valid:
        violated.extend(order_violations)
    details["ordering_valid"] = order_valid
    details["ordering_violations"] = order_violations

    # ── Check 3: Every technique must have supporting evidence ───────────
    unsupported = []
    for tech_id in known_chain:
        if tech_id not in evidence_map or len(evidence_map[tech_id]) == 0:
            unsupported.append(tech_id)
            violated.append(f"missing_evidence_for_{tech_id}")
    details["unsupported_techniques"] = unsupported

    # ── Check 4: Attribution consistency ─────────────────────────────────
    if attributed_group and attributed_group in GROUPS:
        inconsistent_techniques = []
        for tech_id in known_chain:
            if not is_technique_consistent_with_group(tech_id, attributed_group):
                inconsistent_techniques.append(tech_id)
        if len(inconsistent_techniques) > len(known_chain) * 0.5:
            violated.append(
                f"attribution_inconsistency_{attributed_group}_"
                f"{len(inconsistent_techniques)}_of_{len(known_chain)}_techniques_mismatch"
            )
        elif inconsistent_techniques:
            warnings.append(
                f"minor_attribution_mismatch_{attributed_group}_"
                f"{len(inconsistent_techniques)}_techniques"
            )
        details["attribution_consistency"] = {
            "group": attributed_group,
            "inconsistent_techniques": inconsistent_techniques,
            "consistency_ratio": (
                1 - len(inconsistent_techniques) / max(len(known_chain), 1)
            ),
        }
    elif attributed_group:
        violated.append(f"unknown_group_{attributed_group}")
        details["attribution_consistency"] = {"group": attributed_group, "error": "unknown"}
    else:
        violated.append("no_attribution_provided")
        details["attribution_consistency"] = {"group": None, "error": "missing"}

    # ── Check 5: Kill-chain must include initial access ──────────────────
    has_initial_access = any(
        TECHNIQUES.get(t, {}).get("tactic") == "TA0001" for t in known_chain
    )
    if not has_initial_access:
        violated.append("missing_initial_access_technique")
    details["has_initial_access"] = has_initial_access

    # ── Check 6: Lateral movement → must have ≥ 2 compromised hosts ─────
    # Network lateral movement (T1021, T1570) requires multiple hosts.
    # Physical/removable media (T1091) can be executed against a single host.
    has_network_lateral = any(
        t in ["T1021.001", "T1021.002", "T1021.006", "T1570"] for t in known_chain
    )
    if has_network_lateral and len(compromised_hosts) < 2:
        violated.append("lateral_movement_claimed_but_single_host")
    details["lateral_movement_consistent"] = not (
        has_network_lateral and len(compromised_hosts) < 2
    )

    # ── Check 7: Lateral movement reachability (if topology given) ───────
    if network_topology and has_lateral and len(compromised_hosts) >= 2:
        unreachable = []
        for i, host in enumerate(compromised_hosts[1:], 1):
            # Check if at least one previous host can reach this one
            reachable = False
            for prev_host in compromised_hosts[:i]:
                if host in network_topology.get(prev_host, []):
                    reachable = True
                    break
            if not reachable:
                unreachable.append(host)
        if unreachable:
            violated.extend(
                [f"unreachable_host_{h}" for h in unreachable]
            )
        details["unreachable_hosts"] = unreachable

    return {
        "valid": len(violated) == 0,
        "violated": violated,
        "warnings": warnings,
        "details": details,
    }
