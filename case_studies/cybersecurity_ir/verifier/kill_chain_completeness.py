"""
Kill-Chain Completeness Checker
================================
Verifies that a proposed kill chain has no tactical gaps between
the initial access technique and the observed impact/objective.

Part of the deterministic verifier suite (no LLM, G4-compliant).
"""

from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.attck_knowledge_base import TECHNIQUES, TACTICS_ORDER, TACTIC_INDEX, TACTIC_NAMES


def check_kill_chain_completeness(
    kill_chain: list[str],
    required_coverage: dict | None = None,
    allow_gaps: list[str] | None = None,
) -> dict:
    """
    Check that the kill chain covers all expected tactical stages between
    the first and last tactic used.

    Args:
        kill_chain: Ordered list of technique IDs
        required_coverage: Optional dict of {tactic_id: min_techniques}
                           specifying minimum techniques per tactic
        allow_gaps: Optional list of tactic IDs that may be skipped
                    (e.g., "TA0040" Impact is not always present)

    Returns:
        {
            "valid": bool,
            "violated": [constraint_ids],
            "warnings": [strings],
            "details": {...}
        }
    """
    violated = []
    warnings = []
    details = {}

    if not kill_chain:
        violated.append("empty_kill_chain")
        return {"valid": False, "violated": violated, "warnings": [], "details": {}}

    allow_gaps = set(allow_gaps or [])
    # These tactics are commonly optional
    default_optional = {"TA0043", "TA0042", "TA0040"}  # Recon, Resource Dev, Impact
    allow_gaps = allow_gaps | default_optional

    # ── Map techniques to tactics ────────────────────────────────────────
    tactic_to_techniques: dict[str, list[str]] = {}
    unknown_techniques = []

    for tech_id in kill_chain:
        tech = TECHNIQUES.get(tech_id)
        if tech is None:
            unknown_techniques.append(tech_id)
            continue
        tactic = tech["tactic"]
        tactic_to_techniques.setdefault(tactic, []).append(tech_id)

    details["tactic_coverage"] = {
        TACTIC_NAMES.get(t, t): techs
        for t, techs in tactic_to_techniques.items()
    }
    details["unknown_techniques"] = unknown_techniques

    # ── Find the range of tactics covered ────────────────────────────────
    tactic_indices = [
        TACTIC_INDEX[t] for t in tactic_to_techniques if t in TACTIC_INDEX
    ]

    if not tactic_indices:
        violated.append("no_valid_tactics_in_kill_chain")
        return {
            "valid": False,
            "violated": violated,
            "warnings": warnings,
            "details": details,
        }

    min_idx = min(tactic_indices)
    max_idx = max(tactic_indices)

    # ── Check for tactical gaps in the range (warnings unless in required_coverage) ───
    gaps = []
    for idx in range(min_idx, max_idx + 1):
        tactic = TACTICS_ORDER[idx]
        if tactic not in tactic_to_techniques and tactic not in allow_gaps:
            gaps.append(tactic)
            warnings.append(
                f"unobserved_intermediate_tactic_{TACTIC_NAMES.get(tactic, tactic)}"
            )

    details["gaps"] = [
        {"tactic": t, "name": TACTIC_NAMES.get(t, t)} for t in gaps
    ]

    # ── Check required coverage ──────────────────────────────────────────
    if required_coverage:
        for tactic, min_count in required_coverage.items():
            actual = len(tactic_to_techniques.get(tactic, []))
            if actual < min_count:
                violated.append(
                    f"insufficient_coverage_{tactic}_need_{min_count}_have_{actual}"
                )

    # ── Check that initial access or recon is present ────────────────────
    has_entry = "TA0001" in tactic_to_techniques or "TA0043" in tactic_to_techniques
    if not has_entry:
        violated.append("missing_initial_access_or_entry_tactic")

    # ── Check that execution is present (or interactive valid accounts) ─
    has_exec = "TA0002" in tactic_to_techniques or "T1078" in kill_chain or "T1078.002" in kill_chain
    if not has_exec:
        violated.append("missing_execution_tactic")

    # ── Check that objective / continuation tactic is present ────────────
    post_access_tactics = {"TA0003", "TA0008", "TA0009", "TA0011", "TA0010", "TA0040"}
    has_post_access = any(t in tactic_to_techniques for t in post_access_tactics)
    if not has_post_access:
        violated.append("missing_post_access_or_objective_tactic")

    # ── Completeness score ───────────────────────────────────────────────
    total_required = max_idx - min_idx + 1 - len(
        [t for t in allow_gaps if min_idx <= TACTIC_INDEX.get(t, -1) <= max_idx]
    )
    covered = len(tactic_to_techniques)
    completeness_score = covered / max(total_required, 1)
    details["completeness_score"] = round(completeness_score, 3)

    if completeness_score < 0.3:
        warnings.append(f"low_completeness_score_{completeness_score:.2f}")

    return {
        "valid": len(violated) == 0,
        "violated": violated,
        "warnings": warnings,
        "details": details,
    }
