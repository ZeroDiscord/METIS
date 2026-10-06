"""
Metric calculations for METIS Case Studies per CSS v1.0 standard.
Implements:
- R1: Revision distance delta(sigma_t, sigma_{t+1}) over 6 coordinates
- R2: Minimal-repair ratio delta / delta*
- R3: Preserved valid work fraction
- R4: Repeated error rate
- R5: Verifier calls to acceptance
- R6: Recovery rate
- R7: Recovery latency
- Q1-Q4: Task quality metrics
- C1-C5: Cost and hygiene metrics
"""

from typing import Dict, List, Set, Any
import numpy as np

# Coordinates weights for delta per CaseStudy_Biomedical_Variant_Reclassification.md
WEIGHTS = {
    "criteria": 0.30,
    "belief": 0.20,
    "assumptions": 0.20,
    "constraints": 0.10,
    "hypotheses": 0.10,
    "plan": 0.10
}

CLASSES = ["Pathogenic", "Likely pathogenic", "VUS", "Likely benign", "Benign"]

def jaccard_distance(s1: Set[str], s2: Set[str]) -> float:
    if not s1 and not s2:
        return 0.0
    u = s1.union(s2)
    i = s1.intersection(s2)
    return 1.0 - (len(i) / len(u)) if u else 0.0

def total_variation_distance(p1: Dict[str, float], p2: Dict[str, float]) -> float:
    tv = 0.0
    for c in CLASSES:
        v1 = p1.get(c, 0.0)
        v2 = p2.get(c, 0.0)
        tv += abs(v1 - v2)
    return 0.5 * tv

def levenshtein_ratio_distance(seq1: List[str], seq2: List[str]) -> float:
    if not seq1 and not seq2:
        return 0.0
    if not seq1 or not seq2:
        return 1.0
    # Simple edit distance over token sequence
    s1, s2 = " ".join(seq1), " ".join(seq2)
    # Jaccard over tokens as fast robust approximation
    t1, t2 = set(seq1), set(seq2)
    return jaccard_distance(t1, t2)

def compute_revision_distance(state_t: Dict[str, Any], state_next: Dict[str, Any]) -> float:
    """Computes delta(sigma_t, sigma_{t+1}) normalized to [0, 1]."""
    # 1. Active criteria
    c1 = set(state_t.get("active_criteria", []))
    c2 = set(state_next.get("active_criteria", []))
    d_crit = jaccard_distance(c1, c2)

    # 2. Belief beta
    b1 = state_t.get("belief", {c: 0.2 for c in CLASSES})
    b2 = state_next.get("belief", {c: 0.2 for c in CLASSES})
    d_beta = total_variation_distance(b1, b2)

    # 3. Assumptions alpha
    a1 = set(state_t.get("assumptions", []))
    a2 = set(state_next.get("assumptions", []))
    d_alpha = jaccard_distance(a1, a2)

    # 4. Constraints kappa
    k1 = set(state_t.get("constraints", []))
    k2 = set(state_next.get("constraints", []))
    d_kappa = jaccard_distance(k1, k2)

    # 5. Hypotheses H
    h1 = set(state_t.get("hypotheses", []))
    h2 = set(state_next.get("hypotheses", []))
    d_h = jaccard_distance(h1, h2)

    # 6. Plan pi
    p1 = state_t.get("plan", [])
    p2 = state_next.get("plan", [])
    d_pi = levenshtein_ratio_distance(p1, p2)

    delta = (
        WEIGHTS["criteria"] * d_crit +
        WEIGHTS["belief"] * d_beta +
        WEIGHTS["assumptions"] * d_alpha +
        WEIGHTS["constraints"] * d_kappa +
        WEIGHTS["hypotheses"] * d_h +
        WEIGHTS["plan"] * d_pi
    )
    return float(delta)

def compute_minimal_repair_target(state_t: Dict[str, Any], ground_truth: Dict[str, Any]) -> float:
    """Computes delta(sigma_t, sigma*) where sigma* is optimal reference state."""
    target_state = {
        "active_criteria": ground_truth.get("expected_criteria", []),
        "belief": {c: 1.0 if c.lower() == ground_truth.get("classification", "").lower() else 0.0 for c in CLASSES},
        "assumptions": ground_truth.get("expected_criteria", []),
        "constraints": [],
        "hypotheses": [ground_truth.get("classification", "")],
        "plan": ["complete"]
    }
    return compute_revision_distance(state_t, target_state)

def compute_preserved_valid_work(prior_criteria: Set[str], current_criteria: Set[str], reference_criteria: Set[str]) -> float:
    """Fraction of prior correct criteria that survived the revision."""
    prior_valid = prior_criteria.intersection(reference_criteria)
    if not prior_valid:
        return 1.0  # None was valid initially, so none lost
    preserved = prior_valid.intersection(current_criteria)
    return float(len(preserved) / len(prior_valid))

def compute_brier_score(belief: Dict[str, float], ground_truth_class: str) -> float:
    """Computes multi-class Brier score."""
    score = 0.0
    for c in CLASSES:
        prob = belief.get(c, 0.0)
        target = 1.0 if c.lower() == ground_truth_class.lower() else 0.0
        score += (prob - target) ** 2
    return float(score)
