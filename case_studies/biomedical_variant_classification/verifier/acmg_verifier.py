"""
ACMG/AMP 2015 Variant Classification Verifier
Deterministic rules engine implementing standard ACMG combination rules,
conflict resolution, and structural constraint validation.
"""

from typing import Dict, List, Set, Tuple, Any

PATHOGENIC_CRITERIA = {
    "PVS1": "very_strong",
    "PS1": "strong", "PS2": "strong", "PS3": "strong", "PS4": "strong",
    "PM1": "moderate", "PM2": "moderate", "PM3": "moderate", "PM4": "moderate", "PM5": "moderate", "PM6": "moderate",
    "PP1": "supporting", "PP2": "supporting", "PP3": "supporting", "PP4": "supporting", "PP5": "supporting"
}

BENIGN_CRITERIA = {
    "BA1": "stand_alone",
    "BS1": "strong", "BS2": "strong", "BS3": "strong", "BS4": "strong",
    "BP1": "supporting", "BP2": "supporting", "BP3": "supporting", "BP4": "supporting",
    "BP5": "supporting", "BP6": "supporting", "BP7": "supporting"
}

MUTUALLY_EXCLUSIVE_PAIRS = [
    ("PM2", "BA1", "Cannot assert rare/absent frequency (PM2) and common population frequency (BA1) simultaneously."),
    ("PM2", "BS1", "Cannot assert rare frequency (PM2) and benign frequency higher than expected (BS1)."),
    ("PS3", "BS3", "Functional assay cannot be simultaneously damaging (PS3) and non-damaging (BS3)."),
    ("PP3", "BP4", "In silico tools cannot predict damaging (PP3) and benign (BP4) simultaneously."),
    ("PVS1", "BP7", "Null variant LoF (PVS1) contradicts synonymous neutral effect (BP7)."),
    ("PVS1", "PM4", "Truncating/null variant (PVS1) and in-frame protein length change (PM4) are mutually exclusive."),
    ("PS1", "PM5", "Same amino acid change (PS1) and novel missense at same position (PM5) cannot both apply to one variant."),
]

def check_constraints(active_criteria: Set[str], gene_rules: Dict[str, Any] = None) -> List[str]:
    """Check for internal logical inconsistencies and constraint violations."""
    violations = []
    
    # 1. Mutually exclusive pair checks
    for c1, c2, msg in MUTUALLY_EXCLUSIVE_PAIRS:
        if c1 in active_criteria and c2 in active_criteria:
            violations.append(f"MUTUAL_EXCLUSION_VIOLATION: {c1} vs {c2}: {msg}")
            
    # 2. Gene-specific constraint violations
    if gene_rules:
        disallowed = gene_rules.get("disallowed_criteria", [])
        for c in disallowed:
            if c in active_criteria:
                violations.append(f"GENE_SPEC_DISALLOWED: Criterion {c} is prohibited for gene {gene_rules.get('gene', 'UNKNOWN')}")
                
        if "PVS1" in active_criteria and not gene_rules.get("loss_of_function_mechanism", True):
            violations.append(f"PVS1_INVALID_MECHANISM: Loss of function is not an established disease mechanism for {gene_rules.get('gene')}")

    # 3. Double counting check
    if "PS4" in active_criteria and "PP4" in active_criteria:
        violations.append("DOUBLE_COUNTING: PS4 (prevalence in cases) and PP4 (phenotype specificity) cannot be combined without independent patient cohorts.")

    return violations

def evaluate_acmg_class(active_criteria: Set[str]) -> Tuple[str, Dict[str, int]]:
    """
    Evaluates the active criteria against Richards et al. 2015 rules.
    Returns: (classification, strength_counts)
    Classes: 'Pathogenic', 'Likely pathogenic', 'VUS', 'Likely benign', 'Benign'
    """
    p_counts = {"very_strong": 0, "strong": 0, "moderate": 0, "supporting": 0}
    for c in active_criteria:
        if c in PATHOGENIC_CRITERIA:
            p_counts[PATHOGENIC_CRITERIA[c]] += 1
            
    b_counts = {"stand_alone": 0, "strong": 0, "supporting": 0}
    for c in active_criteria:
        if c in BENIGN_CRITERIA:
            b_counts[BENIGN_CRITERIA[c]] += 1

    has_pathogenic = any(p_counts.values())
    has_benign = any(b_counts.values())

    # Stand-alone Benign
    if b_counts["stand_alone"] >= 1:
        if not has_pathogenic:
            return "Benign", {**p_counts, **b_counts}
        else:
            return "VUS", {**p_counts, **b_counts}

    # Benign combinations
    if b_counts["strong"] >= 2:
        if not has_pathogenic:
            return "Benign", {**p_counts, **b_counts}
        else:
            return "VUS", {**p_counts, **b_counts}

    # Likely Benign
    if (b_counts["strong"] == 1 and b_counts["supporting"] >= 1) or (b_counts["supporting"] >= 2):
        if not has_pathogenic:
            return "Likely benign", {**p_counts, **b_counts}
        else:
            return "VUS", {**p_counts, **b_counts}

    # Pathogenic combinations
    vs = p_counts["very_strong"]
    s = p_counts["strong"]
    m = p_counts["moderate"]
    sup = p_counts["supporting"]

    is_pathogenic = False
    if vs >= 1 and (s >= 1 or m >= 2 or (m == 1 and sup >= 1) or sup >= 2):
        is_pathogenic = True
    elif s >= 2:
        is_pathogenic = True
    elif s == 1 and (m >= 3 or (m == 2 and sup >= 2) or (m == 1 and sup >= 4)):
        is_pathogenic = True

    if is_pathogenic:
        if not has_benign:
            return "Pathogenic", {**p_counts, **b_counts}
        else:
            return "VUS", {**p_counts, **b_counts}

    # Likely Pathogenic combinations
    is_likely_pathogenic = False
    if vs == 1 and m == 1:
        is_likely_pathogenic = True
    elif s == 1 and (1 <= m <= 2):
        is_likely_pathogenic = True
    elif s == 1 and sup >= 2:
        is_likely_pathogenic = True
    elif m >= 3:
        is_likely_pathogenic = True
    elif m == 2 and sup >= 2:
        is_likely_pathogenic = True
    elif m == 1 and sup >= 4:
        is_likely_pathogenic = True

    if is_likely_pathogenic:
        if not has_benign:
            return "Likely pathogenic", {**p_counts, **b_counts}
        else:
            return "VUS", {**p_counts, **b_counts}

    return "VUS", {**p_counts, **b_counts}

def verify_interpretation(state: Dict[str, Any], gene_rules: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Main external verifier function nu(sigma, kappa).
    Checks structural validity, mutual exclusions, and rule consistency.
    """
    active_criteria = set(state.get("active_criteria", []))
    inferred_class = state.get("classification", "").strip()
    
    # 1. Structural constraint checks
    violations = check_constraints(active_criteria, gene_rules)
    
    # 2. Rule evaluation
    rule_derived_class, counts = evaluate_acmg_class(active_criteria)
    
    internal_class_consistent = (inferred_class.lower() == rule_derived_class.lower())
    if not internal_class_consistent:
        violations.append(f"CLASS_RULE_MISMATCH: Agent claimed '{inferred_class}' but criteria combine to '{rule_derived_class}'.")

    is_valid = (len(violations) == 0)

    return {
        "valid": is_valid,
        "classification": rule_derived_class,
        "violations": violations,
        "active_criteria": sorted(list(active_criteria)),
        "counts": counts
    }
