"""Reference solution for nlpcode-009 — NOT shown to agents."""

def batch_process(items: list, config: dict) -> list:
    multiplier = config["multiplier"]
    strict = config.get("mode") == "strict"
    result = []
    for item in items:
        if item is None:
            if strict:
                raise ValueError("None item in strict mode")
            continue
        result.append({"result": int(item["value"] * multiplier)})
    return result
