"""
nlp_code_arm_a.py — Standard (Arm A) agentic workflow for the NLP/Code case study.

Architecture (CSS §4, Arm A):
    START → agent_node → [tool_node → agent_node]* → END

No explicit interpretive state. The agent sees raw observations (tool results +
injected perturbations) and decides what to do next. After each run_tests call
the experiment runner injects the next scheduled perturbation into observations.
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
MAX_STEPS = 20  # hard cap: prevents infinite loops


# ── State ──────────────────────────────────────────────────────────────────
class ArmAState(TypedDict):
    instance_id: str
    task: str                       # initial spec goal text (set by experiment runner)
    observations: list              # list of {"tool": ..., "result": ...} dicts
    tools_called: list
    pending_tool_calls: list
    final_answer: str
    test_run_count: int             # incremented each time run_tests is called
    evidence_schedule: list         # from instance YAML, managed by tool_node
    available_perturbations: list   # perturbations already injected
    accepted: bool                  # True once all tests pass
    step_count: int                 # FIX #3: total agent steps taken (for cap)


# ── LLM ───────────────────────────────────────────────────────────────────
_llm = ChatGroq(
    model="llama-3.1-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
    max_retries=20,
)
_llm_with_tools = _llm.bind_tools(ALL_TOOLS)


# ── Nodes ──────────────────────────────────────────────────────────────────
def agent_node(state: ArmAState) -> dict:
    """
    Standard agent: reads task + observations, picks one tool (or concludes).
    No explicit interpretation layer.
    """
    time.sleep(2)  # rate-limit pacing
    # FIX #4: if already accepted, stop immediately without calling LLM
    if state["accepted"]:
        return {"pending_tool_calls": [], "final_answer": state["final_answer"]}

    observations_text = "\n".join(
        f"[{o['tool']}] {o['result']}" for o in state["observations"]
    )

    prompt = f"""You are a Python coding agent. Your job is to implement a Python
function so that all unit tests pass.

INSTANCE: {state["instance_id"]}

TASK:
{state["task"]}

OBSERVATIONS SO FAR (tool results + any new clarifications):
{observations_text if observations_text else "(none yet)"}

INSTRUCTIONS:
- Choose EXACTLY ONE action per turn. Do NOT call multiple tools.
- Recommended sequence: read_spec → write_code → run_tests → (fix if needed) → run_tests
- Pay close attention to any lines starting with "NEW REQUIREMENT" or
  "CLARIFICATION" or "DEPENDENCY REVEALED" or "ENVIRONMENT CHANGE" in the
  observations — these update the requirements and OVERRIDE earlier assumptions.
- When writing code, provide a COMPLETE Python module (all imports + full
  function body). Do not write partial code.
- When run_tests shows all tests passing (passed == True), stop calling tools
  and provide your final answer summarising the implementation.
- If you have tried ≥ 8 times and tests still fail, conclude with your best
  attempt and explain what is still failing.
"""

    response = _llm_with_tools.invoke(prompt)

    print("\n===== [ARM A] AGENT RESPONSE =====")
    print(f"Content: {response.content}")
    print(f"Tool calls: {response.tool_calls}")

    return {
        "pending_tool_calls": response.tool_calls,
        "final_answer": str(response.content),
        "step_count": state["step_count"] + 1,
    }


def tool_node(state: ArmAState) -> dict:
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
        if tool_fn is None:
            result = {"error": f"Unknown tool: {tool_name}"}
        else:
            result = tool_fn.invoke(tool_args)

        print(f"\n===== [ARM A] TOOL: {tool_name} =====")
        print(result)

        observations.append({"tool": tool_name, "result": result})
        tools_called.append(tool_name)

        # ── Perturbation injection ─────────────────────────────────────────
        if tool_name == "run_tests":
            test_run_count += 1

            # Check if tests are now all passing
            if isinstance(result, dict) and result.get("passed"):
                accepted = True

            # Inject the next scheduled perturbation (if due at this step t)
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
                    print(f"\n===== [ARM A] PERTURBATION INJECTED (t={t}) =====")
                    print(event["content"].strip())

    return {
        "observations": observations,
        "tools_called": tools_called,
        "pending_tool_calls": [],
        "test_run_count": test_run_count,
        "available_perturbations": available_perturbations,
        "accepted": accepted,
    }


def should_continue(state: ArmAState) -> str:
    """
    Route decision:
    - Stop if no pending tool calls (agent chose to conclude)
    - Stop if accepted (all tests pass) — FIX #4
    - Stop if step cap reached — FIX #3
    - Otherwise execute the tool call
    """
    if state["accepted"]:
        return "end"
    if state["step_count"] >= MAX_STEPS:
        print(f"\n[ARM A] Step cap ({MAX_STEPS}) reached — terminating.")
        return "end"
    if state["pending_tool_calls"]:
        return "tool"
    return "end"


# ── Graph ──────────────────────────────────────────────────────────────────
def build_arm_a_graph():
    builder = StateGraph(ArmAState)
    builder.add_node("agent", agent_node)
    builder.add_node("tool", tool_node)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue, {"tool": "tool", "end": END})
    builder.add_edge("tool", "agent")

    return builder.compile()


arm_a_graph = build_arm_a_graph()


# ── Entry point for manual testing ────────────────────────────────────────
def run_arm_a(instance_id: str, task: str, evidence_schedule: list) -> dict:
    """Run Arm A on a single instance. Returns final state."""
    initial_state: ArmAState = {
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
    }
    return arm_a_graph.invoke(initial_state)


if __name__ == "__main__":
    # Quick smoke-test on instance 001
    import yaml
    inst_path = os.path.join(
        os.path.dirname(__file__),
        "case_studies", "nlp_code_sai", "instances", "nlpcode-001.yaml",
    )
    with open(inst_path) as f:
        inst = yaml.safe_load(f)
    result = run_arm_a(
        instance_id="nlpcode-001",
        task=inst["initial_spec"]["goal"],
        evidence_schedule=inst["evidence_schedule"],
    )
    print("\n===== FINAL STATE =====")
    print(f"Accepted: {result['accepted']}")
    print(f"Tools called: {result['tools_called']}")
    print(f"Test runs: {result['test_run_count']}")
