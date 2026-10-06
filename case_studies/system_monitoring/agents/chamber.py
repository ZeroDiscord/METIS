"""
chamber.py — Hermeneutic Chamber for System Performance Diagnosis.

Maintains and updates explicit interpretive state σ across diagnostic tool steps
and dynamic evidence perturbations.
"""

from __future__ import annotations
import os
import time
from typing import Dict, Any, List
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

def get_llm():
    return ChatGroq(
        model="openai/gpt-oss-20b",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
        max_retries=20,
    )


HEADERS = [
    "CURRENT_UNDERSTANDING",
    "ASSUMPTIONS",
    "HYPOTHESES",
    "WHAT_CHANGED",
    "DIAGNOSTIC_NOTES",
    "UNCERTAINTIES",
]


def update_chamber_state(
    task: str,
    observations: List[Dict[str, Any]],
    prior_state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Executes the Hermeneutic Chamber to revise interpretive state σ.
    """
    time.sleep(1)

    obs_text = "\n".join(
        f"[{o['tool']}] {o['result']}" for o in observations
    )

    assumptions_text = "\n".join(f"  • {a}" for a in prior_state.get("assumptions", [])) or "  (none)"
    hypotheses_text  = "\n".join(f"  • {h}" for h in prior_state.get("hypotheses", []))  or "  (none)"
    notes_text       = "\n".join(f"  • {n}" for n in prior_state.get("diagnostic_notes", [])) or "  (none)"
    uncert_text      = "\n".join(f"  • {u}" for u in prior_state.get("uncertainties", [])) or "  (none)"

    prompt = f"""You are the Hermeneutic Chamber in a System Performance Diagnosis AI system.

Your SOLE RESPONSIBILITY is to interpret the system telemetry and dynamic evidence, maintain explicit hypotheses, and update the system's diagnostic understanding.
Do NOT call tools. Do NOT submit a diagnosis. Focus purely on interpretation.

INITIAL TASK:
{task}

ALL TELEMETRY OBSERVATIONS & SYSTEM ALERTS SO FAR:
{obs_text if obs_text else "(no telemetry collected yet)"}

PREVIOUS INTERPRETIVE STATE (σ):
  Current Understanding: {prior_state.get("understanding") or "(initial state)"}
  Assumptions:
{assumptions_text}
  Hypotheses:
{hypotheses_text}
  Diagnostic Notes:
{notes_text}
  Uncertainties:
{uncert_text}

INSTRUCTIONS FOR REVISION:
1. Carefully analyze any NEW TELEMETRY ALERT, SYSTEM EVENT, or tool observation.
2. Re-evaluate competing hypotheses (e.g. GPU limit vs CPU game-thread vs thermal throttling vs asset streaming vs driver update).
3. If new evidence contradicts an earlier assumption (e.g. 97% GPU utilization is actually waiting on asset buffers, or temps are normal), EXPLICITLY INVALIDATE or DOWNGRADE the old assumption/hypothesis.
4. Identify which hypothesis is strengthened, which is weakened, and what tool should be run next to verify.

Return your response in this EXACT structured format. Each section header must appear on its own line followed by a colon:

CURRENT_UNDERSTANDING:
<Synthesize the true state of the system based on all telemetry so far>

ASSUMPTIONS:
- <active assumption> | status: <valid/invalidated>

HYPOTHESES:
- <Hypothesis 1: description> | probability: <high/medium/low>
- <Hypothesis 2: description> | probability: <high/medium/low>

WHAT_CHANGED:
<Explicit statement of how new evidence changed or revised the previous hypotheses/assumptions>

DIAGNOSTIC_NOTES:
- <Concrete telemetry fact or constraint that MUST be considered>

UNCERTAINTIES:
- <What remains uncertain and which diagnostic tool should be called next>
"""

    llm = get_llm()
    for attempt in range(10):
        try:
            response = llm.invoke(prompt)
            break
        except Exception as exc:
            if "429" in str(exc) or "rate_limit" in str(exc).lower():
                print(f"  [RATE LIMIT 429] Groq daily token limit reached. Retrying in 65s (attempt {attempt+1}/10)...")
                time.sleep(65)
            else:
                raise exc

    content = str(response.content)

    print("\n" + "="*70)
    print("  [ARM B'] HERMENEUTIC CHAMBER UPDATE")
    print("="*70)
    try:
        print(content)
    except UnicodeEncodeError:
        print(content.encode("ascii", errors="replace").decode("ascii"))

    # ── Parser ─────────────────────────────────────────────────────────────
    def extract_section(text: str, header: str) -> str:
        lines = text.split("\n")
        capturing = False
        result_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped == f"{header}:" or stripped.startswith(f"{header}:"):
                capturing = True
                after_colon = stripped[len(header) + 1:].strip()
                if after_colon:
                    result_lines.append(after_colon)
                continue
            if capturing:
                if any(stripped == f"{h}:" or stripped.startswith(f"{h}:") for h in HEADERS):
                    break
                result_lines.append(line)
        return "\n".join(result_lines).strip()

    def extract_bullets(text: str, header: str) -> List[str]:
        section = extract_section(text, header)
        bullets = []
        for line in section.splitlines():
            s = line.strip()
            if s.startswith("- ") or s.startswith("• "):
                bullets.append(s[2:].strip())
        return bullets if bullets else []

    understanding = extract_section(content, "CURRENT_UNDERSTANDING")
    assumptions   = extract_bullets(content, "ASSUMPTIONS")
    hypotheses    = extract_bullets(content, "HYPOTHESES")
    what_changed   = extract_section(content, "WHAT_CHANGED")
    diag_notes    = extract_bullets(content, "DIAGNOSTIC_NOTES")
    uncertainties = extract_bullets(content, "UNCERTAINTIES")

    return {
        "understanding": understanding or content[:400],
        "assumptions": assumptions,
        "hypotheses": hypotheses,
        "what_changed": what_changed,
        "diagnostic_notes": diag_notes,
        "uncertainties": uncertainties,
        "raw_chamber_output": content,
    }
