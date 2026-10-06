"""
Constraint Checker
==================
Validates that the proposed IR plan satisfies all active business,
operational, and legal constraints.

Part of the deterministic verifier suite (no LLM, G4-compliant).
"""

from __future__ import annotations


# ── Constraint evaluation rules ──────────────────────────────────────────────
# Each rule maps a constraint_id pattern to a checker function.
# The checker receives (plan_actions, constraint, context) and returns
# (satisfied: bool, details: str).

def _check_system_availability(
    plan_actions: list[dict],
    constraint: dict,
    context: dict,
) -> tuple[bool, str]:
    """Check that no plan action takes a specified system offline."""
    protected_system = constraint.get("protected_system", "")
    if not protected_system:
        return True, "no_protected_system_specified"

    for action in plan_actions:
        target = action.get("target", "")
        category = action.get("category", "")
        action_text = action.get("action", "").lower()

        # Actions that would take a system offline
        disruptive_actions = [
            "isolate", "shutdown", "reimage", "take_offline",
            "disconnect", "quarantine", "block",
        ]

        if target == protected_system:
            for da in disruptive_actions:
                if da in action_text:
                    return False, (
                        f"action_{action.get('id', '?')}_would_disrupt_"
                        f"{protected_system}_via_{da}"
                    )

    return True, "no_disruptive_actions_on_protected_system"


def _check_evidence_preservation(
    plan_actions: list[dict],
    constraint: dict,
    context: dict,
) -> tuple[bool, str]:
    """Check that plan actions preserve forensic evidence."""
    for action in plan_actions:
        action_text = action.get("action", "").lower()
        category = action.get("category", "")

        destructive_actions = [
            "reimage", "wipe", "format", "delete_logs",
            "overwrite", "factory_reset",
        ]

        for da in destructive_actions:
            if da in action_text:
                # Check if a forensic copy is taken first
                target = action.get("target", "")
                has_forensic_copy = any(
                    "forensic" in a.get("action", "").lower()
                    and a.get("target", "") == target
                    for a in plan_actions
                    if plan_actions.index(a) < plan_actions.index(action)
                )
                if not has_forensic_copy:
                    return False, (
                        f"action_{action.get('id', '?')}_destroys_evidence_"
                        f"on_{target}_without_prior_forensic_copy"
                    )

    return True, "evidence_preservation_satisfied"


def _check_time_constraint(
    plan_actions: list[dict],
    constraint: dict,
    context: dict,
) -> tuple[bool, str]:
    """Check that plan actions fit within time budget."""
    max_hours = constraint.get("max_hours", float("inf"))
    estimated_hours = sum(
        action.get("estimated_hours", 1) for action in plan_actions
    )

    if estimated_hours > max_hours:
        return False, (
            f"estimated_{estimated_hours}h_exceeds_budget_{max_hours}h"
        )
    return True, f"within_time_budget_{estimated_hours}h_of_{max_hours}h"


def _check_no_alert_attacker(
    plan_actions: list[dict],
    constraint: dict,
    context: dict,
) -> tuple[bool, str]:
    """Check that plan actions don't tip off the attacker."""
    alerting_actions = [
        "block_c2", "sinkhole", "change_firewall",
        "reset_all_passwords", "send_notification",
    ]

    for action in plan_actions:
        action_text = action.get("action", "").lower()
        for aa in alerting_actions:
            if aa in action_text and action.get("covert", False) is not True:
                return False, (
                    f"action_{action.get('id', '?')}_may_alert_attacker_via_{aa}"
                )

    return True, "stealth_constraint_satisfied"


CONSTRAINT_CHECKERS = {
    "system_availability": _check_system_availability,
    "evidence_preservation": _check_evidence_preservation,
    "time_constraint": _check_time_constraint,
    "no_alert_attacker": _check_no_alert_attacker,
}


def check_constraints(
    plan_actions: list[dict],
    constraints: list[dict],
    context: dict | None = None,
) -> dict:
    """
    Check all constraints against the proposed plan.

    Args:
        plan_actions: List of plan action dicts with keys:
                      id, action, target, category, estimated_hours, covert
        constraints: List of constraint dicts with keys:
                     id, text, type, hard, parameters
        context: Optional additional context

    Returns:
        {
            "valid": bool,
            "violated": [constraint_ids],
            "warnings": [strings],
            "details": {constraint_id: {satisfied, details}}
        }
    """
    context = context or {}
    violated = []
    warnings = []
    details = {}

    for constraint in constraints:
        c_id = constraint.get("id", "unknown")
        c_type = constraint.get("type", "generic")
        c_hard = constraint.get("hard", True)

        checker = CONSTRAINT_CHECKERS.get(c_type)

        if checker:
            satisfied, detail_msg = checker(plan_actions, constraint, context)
        else:
            # Generic check: constraint is assumed satisfied if no checker
            satisfied = True
            detail_msg = "no_specific_checker_generic_pass"
            warnings.append(f"no_checker_for_constraint_type_{c_type}")

        details[c_id] = {
            "satisfied": satisfied,
            "hard": c_hard,
            "details": detail_msg,
        }

        if not satisfied:
            if c_hard:
                violated.append(c_id)
            else:
                warnings.append(f"soft_constraint_violated_{c_id}")

    return {
        "valid": len(violated) == 0,
        "violated": violated,
        "warnings": warnings,
        "details": details,
    }
