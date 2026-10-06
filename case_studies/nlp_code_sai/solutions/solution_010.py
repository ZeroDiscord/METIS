"""Reference solution for nlpcode-010 — NOT shown to agents."""


def aggregate_results(groups: dict) -> dict:
    result = {}
    for group_id, records in groups.items():
        agg = {"_count": len(records)}
        if not records:
            result[group_id] = agg
            continue

        all_keys = set()
        for record in records:
            all_keys.update(record.keys())

        for key in all_keys:
            values = [record.get(key) for record in records]

            # Determine if all values are numeric (int/float but NOT bool)
            def is_numeric(v):
                return isinstance(v, (int, float)) and not isinstance(v, bool)

            all_numeric_or_none = all(is_numeric(v) or v is None for v in values)

            if all_numeric_or_none:
                # Sum numeric field; None → 0
                agg[key] = sum(v if v is not None else 0 for v in values)
            else:
                # Non-numeric: carry over only if identical across all records
                if len({str(v) for v in values}) == 1:
                    agg[key] = values[0]
                # else omit the field

        # '_count' always overwritten with record count (injected field takes priority)
        agg["_count"] = len(records)
        result[group_id] = agg
    return result
