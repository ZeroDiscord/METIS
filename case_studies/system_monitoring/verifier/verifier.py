"""
verifier/verifier.py — Generic Deterministic Verifier for System Performance Diagnosis.

Evaluates diagnosis submissions against hidden ground truth and acceptance criteria
for all 10 instances strictly deterministically without any LLM judge.
"""

from __future__ import annotations
from typing import Dict, Any, List


def verify_diagnosis(
    submission: Dict[str, Any],
    instance: Dict[str, Any],
    injected_perturbations_count: int,
) -> Dict[str, Any]:
    """
    Deterministically evaluates a submitted diagnosis for any instance.

    Args:
        submission: Dict returned by submit_diagnosis tool.
        instance: Loaded instance YAML dict.
        injected_perturbations_count: Count of scheduled perturbations injected so far.

    Returns:
        Structured evaluation output.
    """
    violations: List[str] = []
    ground_truth = instance.get("hidden_ground_truth", {})
    total_scheduled = len(instance.get("evidence_schedule", []))

    if not isinstance(submission, dict) or submission.get("submission_type") != "final_diagnosis":
        return {
            "passed": False,
            "primary_cause_correct": False,
            "required_evidence_present": False,
            "ruled_out_causes_checked": False,
            "all_perturbations_survived": False,
            "violations": ["Invalid submission format: submit_diagnosis tool was not called properly."],
        }

    # ── 1. Primary Cause Check ──────────────────────────────────────────────
    submitted_cause = str(submission.get("primary_cause", "")).lower().strip()
    target_causes = ground_truth.get("primary_cause_aliases", [ground_truth.get("primary_cause", "")])
    if isinstance(target_causes, str):
        target_causes = [target_causes]
    
    target_causes_lower = [str(c).lower().strip() for c in target_causes]

    primary_cause_correct = any(
        target in submitted_cause or submitted_cause in target
        for target in target_causes_lower
    )
    if not primary_cause_correct:
        violations.append(
            f"Incorrect primary cause: '{submission.get('primary_cause')}' (expected one of {target_causes})."
        )

    # ── 2. Required Evidence Check ──────────────────────────────────────────
    required_keywords = [kw.lower() for kw in ground_truth.get("required_evidence_keywords", [])]
    evidence_text = " ".join([str(e) for e in submission.get("supporting_evidence", [])]).lower()
    full_text = (
        evidence_text + " " +
        str(submission.get("primary_cause", "")).lower() + " " +
        " ".join([str(f) for f in submission.get("contributing_factors", [])]).lower()
    )

    missing_keywords = [kw for kw in required_keywords if kw not in full_text]
    required_evidence_present = len(missing_keywords) == 0
    if not required_evidence_present:
        violations.append(f"Missing required evidence keywords: {missing_keywords}.")

    # ── 3. Ruled Out Causes Check ───────────────────────────────────────────
    rejected_text = " ".join([str(r) for r in submission.get("rejected_alternatives", [])]).lower()
    expected_ruled_out = [str(r).lower() for r in ground_truth.get("ruled_out_causes", [])]

    missing_ruled_out = []
    for expected in expected_ruled_out:
        if expected not in rejected_text and not any(part in rejected_text for part in expected.split("_")):
            missing_ruled_out.append(expected)

    ruled_out_causes_checked = len(missing_ruled_out) == 0
    if not ruled_out_causes_checked:
        violations.append(f"Failed to explicitly rule out expected alternatives: {missing_ruled_out}.")

    # ── 4. Perturbations Check (Req 5 & 10) ─────────────────────────────────
    all_perturbations_survived = injected_perturbations_count >= total_scheduled
    if not all_perturbations_survived:
        violations.append(
            f"Premature submission: survived {injected_perturbations_count}/{total_scheduled} scheduled perturbations."
        )

    # Acceptance predicate
    passed = (
        primary_cause_correct
        and required_evidence_present
        and ruled_out_causes_checked
        and all_perturbations_survived
    )

    return {
        "passed": passed,
        "primary_cause_correct": primary_cause_correct,
        "required_evidence_present": required_evidence_present,
        "ruled_out_causes_checked": ruled_out_causes_checked,
        "all_perturbations_survived": all_perturbations_survived,
        "violations": violations,
    }
