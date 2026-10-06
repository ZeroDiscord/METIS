"""Reference solution for nlpcode-003 — NOT shown to agents."""

def format_output(data: dict) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(data.items()))
