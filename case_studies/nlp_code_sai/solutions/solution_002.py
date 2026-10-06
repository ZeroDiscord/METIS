"""Reference solution for nlpcode-002 — NOT shown to agents."""

def compute_score(values: list) -> float:
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n % 2 == 1:
        return sorted_vals[n // 2]
    else:
        return sorted_vals[n // 2 - 1]  # lower of the two middle elements
