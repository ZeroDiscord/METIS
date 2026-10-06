"""Reference solution for nlpcode-005 — NOT shown to agents."""

def merge_streams(stream_a: list, stream_b: list) -> list:
    a = stream_a if stream_a is not None else []
    b = stream_b if stream_b is not None else []
    seen_ids = {e["event_id"] for e in a}
    deduped_b = [e for e in b if e["event_id"] not in seen_ids]
    merged = list(a) + deduped_b
    merged.sort(key=lambda e: e["timestamp"])
    return merged
