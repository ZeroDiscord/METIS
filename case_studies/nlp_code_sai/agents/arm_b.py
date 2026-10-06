"""
nlp_code_arm_b.py — Hermeneutic (Arm B') agentic workflow for the NLP/Code case study.

Architecture (CSS §4, Arm B'):
    START → agent_node → [tool_node → chamber_node → agent_node]* → END

The Hermeneutic Chamber (chamber_node) fires after EVERY tool execution.
It maintains an explicit interpretive state σ = {understanding, assumptions,
hypotheses, implementation_notes, uncertainties} and updates it each cycle.
The agent_node receives this structured interpretation before deciding next action.
"""

from __future__ import annotations

import os
import time
from typing import TypedDict

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph

from tools.nlp_code_tools import ALL_TOOLS

load_dotenv()

# ── Constants ──────────────────────────────────────────────────────────────
MAX_STEPS = 20  # hard cap


# ── State ──────────────────────────────────────────────────────────────────
class ArmBState(TypedDict):
    instance_id: str
    task: str
    observations: list
    tools_called: list
    pending_tool_calls: list
    final_answer: str
    test_run_count: int
    evidence_schedule: list
    available_perturbations: list
    accepted: bool
    step_count: int                 # FIX #3: step cap

    # ── Hermeneutic interpretive state (σ) ────────────────────────────────
    understanding: str          # γ + β: current goal understanding + beliefs
    assumptions: list           # α: explicit assumptions made
    hypotheses: list            # H: competing interpretations of ambiguous reqs
    implementation_notes: list  # κ + π: what the code must/must-not do
    uncertainties: list         # remaining unknowns


# ── LLM ───────────────────────────────────────────────────────────────────
_llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
    max_retries=20,
)
_llm_with_tools = _llm.bind_tools(ALL_TOOLS)


# ── Nodes ──────────────────────────────────────────────────────────────────
def agent_node(state: ArmBState) -> dict:
    """
    Hermeneutic agent: reads the Chamber's interpretation before deciding.
    Unlike Arm A, the agent prompt includes the structured σ state.
    """
    time.sleep(2)  # rate-limit pacing
    # FIX #4: stop immediately if already accepted
    if state["accepted"]:
        return {"pending_tool_calls": [], "final_answer": state["final_answer"]}

    obs_text = "\n".join(
        f"[{o['tool']}] {o['result']}" for o in state["observations"]
    )
    assumptions_text = "\n".join(f"  • {a}" for a in state["assumptions"]) or "  (none)"
    hypotheses_text  = "\n".join(f"  • {h}" for h in state["hypotheses"])  or "  (none)"
    notes_text       = "\n".join(f"  • {n}" for n in state["implementation_notes"]) or "  (none)"
    uncert_text      = "\n".join(f"  • {u}" for u in state["uncertainties"]) or "  (none)"

    prompt = f"""You are a Python coding agent with an explicit interpretation layer.
Your job is to implement a Python function so that all unit tests pass.

INSTANCE: {state["instance_id"]}

━━━━ HERMENEUTIC CHAMBER OUTPUT (updated interpretation of the spec) ━━━━
CURRENT UNDERSTANDING:
{state["understanding"] or "(not yet interpreted)"}

EXPLICIT ASSUMPTIONS:
{assumptions_text}

COMPETING HYPOTHESES (ambiguous requirements):
{hypotheses_text}

IMPLEMENTATION NOTES (what the code MUST do):
{notes_text}

REMAINING UNCERTAINTIES:
{uncert_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RAW OBSERVATIONS (tool results + clarifications):
{obs_text if obs_text else "(none yet)"}

INSTRUCTIONS:
- Choose EXACTLY ONE action per turn. Do NOT call multiple tools.
- Use the interpretation above to guide your implementation decisions.
- When you see NEW CLARIFICATION in observations, the Chamber will update
  the interpretation — trust the updated IMPLEMENTATION NOTES.
- When writing code, provide a COMPLETE Python module (all imports + full
  function body). Do not write partial code.
- When run_tests shows passed == True, provide your final answer.
- If you have tried ≥ 8 times and tests still fail, conclude with your best
  attempt and explain the remaining failures.
"""

    response = _llm_with_tools.invoke(prompt)

    print("\n===== [ARM B'] AGENT RESPONSE =====")
    print(f"Content: {response.content}")
    print(f"Tool calls: {response.tool_calls}")

    return {
        "pending_tool_calls": response.tool_calls,
        "final_answer": str(response.content),
        "step_count": state["step_count"] + 1,
    }


def tool_node(state: ArmBState) -> dict:
    """Execute pending tool calls and inject due perturbations after run_tests."""
    tool_map = {t.name: t for t in ALL_TOOLS}

    observations = list(state["observations"])
    tools_called = list(state["tools_called"])
    test_run_count = state["test_run_count"]
    available_perturbations = list(state["available_perturbations"])
    accepted = state["accepted"]

    for tc in state["pending_tool_calls"]:
        tool_name = tc["name"]
        tool_args = tc.get("args", {})

        tool_fn = tool_map.get(tool_name)
        result = tool_fn.invoke(tool_args) if tool_fn else {"error": f"Unknown tool: {tool_name}"}

        print(f"\n===== [ARM B'] TOOL: {tool_name} =====")
        print(result)

        observations.append({"tool": tool_name, "result": result})
        tools_called.append(tool_name)

        if tool_name == "run_tests":
            test_run_count += 1
            if isinstance(result, dict) and result.get("passed"):
                accepted = True

            for event in state["evidence_schedule"]:
                t = event["t"]
                if t == test_run_count and event not in available_perturbations:
                    perturbation_obs = {
                        "tool": "NEW_CLARIFICATION",
                        "result": {
                            "perturbation_type": event["type"],
                            "content": event["content"].strip(),
                        },
                    }
                    observations.append(perturbation_obs)
                    available_perturbations.append(event)
                    print(f"\n===== [ARM B'] PERTURBATION INJECTED (t={t}) =====")
                    print(event["content"].strip())

    return {
        "observations": observations,
        "tools_called": tools_called,
        "pending_tool_calls": [],
        "test_run_count": test_run_count,
        "available_perturbations": available_perturbations,
        "accepted": accepted,
    }


def chamber_node(state: ArmBState) -> dict:
    """
    Hermeneutic Chamber — the key differentiator vs Arm A.

    Receives all current observations (including any newly injected
    perturbation) and updates the explicit interpretive state σ.
    Does NOT choose tools or write code — purely interpretive.
    """
    time.sleep(2)  # rate-limit pacing
    obs_text = "\n".join(
        f"[{o['tool']}] {o['result']}" for o in state["observations"]
    )

    prompt = f"""You are the Hermeneutic Chamber in an AI coding assistant system.

Your ONLY job is to interpret the specification and evidence collected so far,
and update the system's explicit understanding of what the function must do.
Do NOT write code. Do NOT choose tools.

ORIGINAL TASK:
{state["task"]}

ALL OBSERVATIONS SO FAR (tool results + clarifications):
{obs_text}

PREVIOUS INTERPRETIVE STATE:
  Understanding:         {state["understanding"] or "(empty)"}
  Assumptions:          {state["assumptions"]}
  Hypotheses:           {state["hypotheses"]}
  Implementation Notes: {state["implementation_notes"]}
  Uncertainties:        {state["uncertainties"]}

Carefully analyse any NEW_CLARIFICATION, ENVIRONMENT CHANGE, DEPENDENCY REVEALED,
or test failures in the observations. Update the interpretation accordingly.

Return your response in this EXACT structure. Each section header must appear on
its own line followed immediately by a colon and newline. Do not add any other
sections or markdown formatting:

CURRENT_UNDERSTANDING:
<One paragraph: precise description of what the function must do, incorporating ALL clarifications>

ASSUMPTIONS:
- <assumption> | confidence: <0.0-1.0>

HYPOTHESES:
- <competing interpretation if spec is still ambiguous> | confidence: <0.0-1.0>

WHAT_CHANGED:
<What new information changed the understanding from the previous state, or "No change.">

IMPLEMENTATION_NOTES:
- <Specific, concrete implementation requirement the code must satisfy>

UNCERTAINTIES:
- <What is still unclear and could affect correctness>
"""

    response = _llm.invoke(prompt)

    print("\n===== [ARM B'] HERMENEUTIC CHAMBER =====")
    print(response.content)

    # ── FIX #5/#9: Robust structured response parser ──────────────────────
    # Use all known section headers as delimiters so boundaries are reliable.
    HEADERS = [
        "CURRENT_UNDERSTANDING",
        "ASSUMPTIONS",
        "HYPOTHESES",
        "WHAT_CHANGED",
        "IMPLEMENTATION_NOTES",
        "UNCERTAINTIES",
    ]

    def extract_section(text: str, header: str) -> str:
        """Extract text between 'header:' and the next known section header."""
        lines = text.split("\n")
        capturing = False
        result_lines = []
        for line in lines:
            stripped = line.strip()
            # Start capturing after the target header line
            if stripped == f"{header}:" or stripped.startswith(f"{header}:"):
                capturing = True
                # Capture inline content after the colon if present
                after_colon = stripped[len(header) + 1:].strip()
                if after_colon:
                    result_lines.append(after_colon)
                continue
            if capturing:
                # Stop at any known section header
                if any(stripped == f"{h}:" or stripped.startswith(f"{h}:") for h in HEADERS):
                    break
                result_lines.append(line)
        return "\n".join(result_lines).strip()

    def extract_bullets(text: str, header: str) -> list:
        section = extract_section(text, header)
        bullets = []
        for line in section.splitlines():
            s = line.strip()
            if s.startswith("- ") or s.startswith("• "):
                bullets.append(s[2:].strip())
        return bullets if bullets else []

    content = response.content
    understanding = extract_section(content, "CURRENT_UNDERSTANDING")
    assumptions   = extract_bullets(content, "ASSUMPTIONS")
    hypotheses    = extract_bullets(content, "HYPOTHESES")
    impl_notes    = extract_bullets(content, "IMPLEMENTATION_NOTES")
    uncertainties = extract_bullets(content, "UNCERTAINTIES")

    return {
        "understanding":        understanding or content[:500],
        "assumptions":          assumptions,
        "hypotheses":           hypotheses,
        "implementation_notes": impl_notes,
        "uncertainties":        uncertainties,
    }


def should_continue(state: ArmBState) -> str:
    """
    Route decision:
    - Stop if accepted — FIX #4
    - Stop if step cap reached — FIX #3
    - Execute tool call if pending
    - Otherwise end
    """
    if state["accepted"]:
        return "end"
    if state["step_count"] >= MAX_STEPS:
        print(f"\n[ARM B'] Step cap ({MAX_STEPS}) reached — terminating.")
        return "end"
    if state["pending_tool_calls"]:
        return "tool"
    return "end"


# ── Graph ──────────────────────────────────────────────────────────────────
def build_arm_b_graph():
    builder = StateGraph(ArmBState)
    builder.add_node("agent",   agent_node)
    builder.add_node("tool",    tool_node)
    builder.add_node("chamber", chamber_node)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue, {"tool": "tool", "end": END})
    builder.add_edge("tool", "chamber")
    builder.add_edge("chamber", "agent")

    return builder.compile()


arm_b_graph = build_arm_b_graph()


# ── Entry point ────────────────────────────────────────────────────────────
def run_arm_b(instance_id: str, task: str, evidence_schedule: list) -> dict:
    """Run Arm B' on a single instance. Returns final state."""
    initial_state: ArmBState = {
        "instance_id": instance_id,
        "task": task,
        "observations": [],
        "tools_called": [],
        "pending_tool_calls": [],
        "final_answer": "",
        "test_run_count": 0,
        "evidence_schedule": evidence_schedule,
        "available_perturbations": [],
        "accepted": False,
        "step_count": 0,
        # Hermeneutic σ — initially empty
        "understanding": "",
        "assumptions": [],
        "hypotheses": [],
        "implementation_notes": [],
        "uncertainties": [],
    }
    return arm_b_graph.invoke(initial_state)


if __name__ == "__main__":
    import yaml
    inst_path = os.path.join(
        os.path.dirname(__file__),
        "case_studies", "nlp_code_sai", "instances", "nlpcode-001.yaml",
    )
    with open(inst_path) as f:
        inst = yaml.safe_load(f)
    result = run_arm_b(
        instance_id="nlpcode-001",
        task=inst["initial_spec"]["goal"],
        evidence_schedule=inst["evidence_schedule"],
    )
    print("\n===== FINAL STATE =====")
    print(f"Accepted: {result['accepted']}")
    print(f"Tools called: {result['tools_called']}")
    print(f"Test runs: {result['test_run_count']}")
    print(f"Final understanding: {result['understanding'][:300]}")
