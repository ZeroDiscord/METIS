"""Reference solution for nlpcode-001 — NOT shown to agents."""

def filter_records(records: list, threshold: float) -> list:
    result = []
    for record in records:
        score = record.get("score", 0)
        if score > threshold:
            result.append(record)
    return result
