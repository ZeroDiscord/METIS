"""Reference solution for nlpcode-007 — NOT shown to agents."""

def classify_tokens(tokens: list, rules: dict) -> list:
    lower_rules = {k.lower(): v for k, v in rules.items()}
    result = []
    for token in tokens:
        str_token = str(token)
        label = lower_rules.get(str_token.lower(), "unknown")
        result.append((token, label))
    return result
