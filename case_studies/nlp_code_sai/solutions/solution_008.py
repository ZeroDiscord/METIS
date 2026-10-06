"""Reference solution for nlpcode-008 — NOT shown to agents."""
from collections import defaultdict


def resolve_conflicts(entries: list) -> list:
    groups = defaultdict(list)
    for i, entry in enumerate(entries):
        groups[entry["entry_id"]].append((i, entry))

    result = []
    for entry_id in sorted(groups.keys()):
        group_entries = groups[entry_id]
        valid = [(i, e) for i, e in group_entries if e["priority"] != 0]
        if not valid:
            continue
        # sort by (priority DESC, timestamp DESC, index DESC) → take first
        winner = max(valid, key=lambda x: (x[1]["priority"], x[1]["timestamp"], x[0]))[1]
        result.append(winner)
    return result
