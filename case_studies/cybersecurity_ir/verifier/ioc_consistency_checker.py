"""
IOC Consistency Checker
========================
Validates that Indicators of Compromise (IOCs) in a proposed attribution
are mutually consistent, temporally ordered, and not contradicted by
verified evidence.

Part of the deterministic verifier suite (no LLM, G4-compliant).
"""

from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class IOC:
    """An Indicator of Compromise."""
    id: str
    type: str  # ip | domain | hash | email | url | mutex | registry | filepath
    value: str
    first_seen: str  # ISO timestamp
    source: str  # which evidence item provided this IOC
    attributed_groups: list[str] = field(default_factory=list)
    confidence: float = 1.0
    status: str = "active"  # active | retracted | unverified


def check_ioc_consistency(
    iocs: list[dict],
    attributed_group: str,
    timeline_events: list[dict] | None = None,
    verified_evidence: list[dict] | None = None,
) -> dict:
    """
    Check consistency of a set of IOCs against attribution and timeline.

    Args:
        iocs: List of IOC dicts with keys: id, type, value, first_seen,
              attributed_groups, source
        attributed_group: The group ID the agent is attributing the attack to
        timeline_events: Ordered events with timestamps
        verified_evidence: Evidence items that are confirmed/verified (if an IOC
                           contradicts verified evidence, it's a violation)

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

    # ── Check 1: IOC attribution consistency ─────────────────────────────
    attribution_mismatches = []
    for ioc in iocs:
        groups = ioc.get("attributed_groups", [])
        if groups and attributed_group not in groups:
            attribution_mismatches.append({
                "ioc_id": ioc["id"],
                "ioc_groups": groups,
                "claimed_group": attributed_group,
            })

    if len(attribution_mismatches) > len(iocs) * 0.4:
        violated.append(
            f"attribution_IOC_mismatch_{attributed_group}_"
            f"{len(attribution_mismatches)}_of_{len(iocs)}"
        )
    elif attribution_mismatches:
        warnings.append(
            f"some_IOCs_not_attributed_to_{attributed_group}_"
            f"({len(attribution_mismatches)})"
        )
    details["attribution_mismatches"] = attribution_mismatches

    # ── Check 2: Temporal ordering of IOCs ───────────────────────────────
    temporal_violations = []
    parsed_iocs = []
    for ioc in iocs:
        try:
            ts = datetime.fromisoformat(ioc["first_seen"].replace("Z", "+00:00"))
            parsed_iocs.append((ioc["id"], ts, ioc))
        except (ValueError, KeyError):
            warnings.append(f"unparseable_timestamp_{ioc.get('id', '?')}")

    # Sort by timestamp
    parsed_iocs.sort(key=lambda x: x[1])

    # Check that C2 IOCs don't appear before initial access IOCs
    initial_access_time = None
    c2_times = []
    for ioc_id, ts, ioc in parsed_iocs:
        ioc_type = ioc.get("type", "")
        phase = ioc.get("phase", "")
        if phase == "initial_access" and initial_access_time is None:
            initial_access_time = ts
        if phase in ("c2", "exfiltration"):
            c2_times.append((ioc_id, ts))

    if initial_access_time:
        for ioc_id, ts in c2_times:
            if ts < initial_access_time:
                temporal_violations.append(
                    f"temporal_inconsistency_{ioc_id}_C2_before_initial_access"
                )
                violated.append(
                    f"temporal_inconsistency_{ioc_id}_C2_before_initial_access"
                )

    if timeline_events:
        t_init = None
        for ev in timeline_events:
            ev_phase = ev.get("phase", "")
            try:
                ev_ts = datetime.fromisoformat(ev["timestamp"].replace("Z", "+00:00"))
                if ev_phase == "initial_access" and t_init is None:
                    t_init = ev_ts
                elif ev_phase in ("c2", "exfiltration") and t_init is not None:
                    if ev_ts < t_init:
                        msg = f"temporal_order_violation_{ev.get('event', 'unknown')}_before_initial_access"
                        temporal_violations.append(msg)
                        violated.append(msg)
                elif ev_phase in ("c2", "exfiltration") and t_init is None:
                    # check if any subsequent event is initial_access
                    for other in timeline_events:
                        if other.get("phase") == "initial_access":
                            try:
                                other_ts = datetime.fromisoformat(other["timestamp"].replace("Z", "+00:00"))
                                if ev_ts < other_ts:
                                    msg = f"temporal_order_violation_{ev.get('event', 'unknown')}_before_initial_access"
                                    temporal_violations.append(msg)
                                    violated.append(msg)
                            except Exception:
                                pass
            except Exception:
                warnings.append(f"unparseable_timeline_timestamp_{ev.get('event', '?')}")

    details["temporal_violations"] = temporal_violations

    # ── Check 3: Contradictions with verified evidence ───────────────────
    contradictions = []
    if verified_evidence:
        verified_ioc_values = {
            e["value"]: e for e in verified_evidence
            if "value" in e and e.get("status") == "verified"
        }
        for ioc in iocs:
            val = ioc.get("value", "")
            if val in verified_ioc_values:
                verified = verified_ioc_values[val]
                # If the verified evidence marks this IOC as benign
                # but the proposed state treats it as malicious
                if verified.get("classification") == "benign" and ioc.get("classification", "malicious") == "malicious":
                    contradictions.append({
                        "ioc_id": ioc["id"],
                        "proposed": "malicious",
                        "verified": "benign",
                    })
                    violated.append(
                        f"contradiction_verified_evidence_{ioc['id']}"
                    )
    details["contradictions_with_verified"] = contradictions

    # ── Check 4: Duplicate IOCs with conflicting attribution ─────────────
    value_to_groups: dict[str, set] = {}
    conflicting_iocs = []
    for ioc in iocs:
        val = ioc.get("value", "")
        groups = set(ioc.get("attributed_groups", []))
        if val in value_to_groups:
            prev_groups = value_to_groups[val]
            if groups and prev_groups and groups != prev_groups:
                conflicting_iocs.append({
                    "value": val,
                    "groups_a": list(prev_groups),
                    "groups_b": list(groups),
                })
            value_to_groups[val] = prev_groups | groups
        else:
            value_to_groups[val] = groups

    if conflicting_iocs:
        warnings.extend(
            [f"conflicting_attribution_for_{c['value']}" for c in conflicting_iocs]
        )
    details["conflicting_iocs"] = conflicting_iocs

    # ── Check 5: Minimum IOC coverage ────────────────────────────────────
    ioc_types_present = {ioc.get("type") for ioc in iocs}
    required_types = {"ip", "hash"}  # minimum for a valid attribution
    missing_types = required_types - ioc_types_present
    if missing_types:
        warnings.append(f"missing_ioc_types_{','.join(missing_types)}")
    details["ioc_types_present"] = list(ioc_types_present)
    details["missing_required_types"] = list(missing_types)

    return {
        "valid": len(violated) == 0,
        "violated": violated,
        "warnings": warnings,
        "details": details,
    }
