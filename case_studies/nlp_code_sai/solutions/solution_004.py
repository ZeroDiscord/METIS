"""Reference solution for nlpcode-004 — NOT shown to agents."""

def sort_records(records: list, key: str) -> list:
    result = list(records)
    for r in result:
        if key not in r:
            raise KeyError(f"Missing sort key: {key}")
    non_neg = [r for r in result if r[key] >= 0]
    neg = [r for r in result if r[key] < 0]
    non_neg.sort(key=lambda r: r[key])
    neg.sort(key=lambda r: abs(r[key]))
    return non_neg + neg
