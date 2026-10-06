"""Reference solution for nlpcode-006 — NOT shown to agents."""

def find_largest(items: list):
    if not items:
        return None
    return min(items, key=lambda x: x["priority_rank"])
