"""
arm_b.py — Hermeneutic (Arm B') Agentic Workflow for System Performance Diagnosis.

Architecture (CSS §4, Arm B'):
    START → agent_node → [tool_node → chamber_node → agent_node]* → END

The Hermeneutic Chamber (chamber_node) fires after EVERY tool execution.
It maintains an explicit interpretive state σ = {understanding, assumptions,
hypotheses, diagnostic_notes, uncertainties} and updates it each cycle.
The agent_node receives this structured interpretation before deciding next action.
"""

from __future__ import annotations
import os
import time
from typing import TypedDict, List, Dict, Any

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph

from environment import SystemEnvironment
from tools import ALL_TOOLS, set_active_environment
from verifier import verify_diagnosis
from chamber import update_chamber_state

load_dotenv()

MAX_STEPS = 20


class ArmBState(TypedDict):
    instance_id: str
    instance: dict
    task: str
    observations: list
    tools_called: list
    pending_tool_calls: list
    final_answer: str
    tool_step_count: int
    evidence_schedule: list
    available_perturbations: list
    accepted: bool
    step_count: int
    submission: dict
    verifier_result: dict

    # Hermeneutic interpretive state σ
    understanding: str
    assumptions: list
    hypotheses: list
    what_changed: str
    diagnostic_notes: list
    uncertainties: list
    chamber_history: list


_llm = ChatGroq(
    model="openai/gpt-oss-20b",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
    max_retries=20,
)
_llm_with_tools = _llm.bind_tools(ALL_TOOLS)


def agent_node(state: ArmBState) -> dict:
    time.sleep(1)
    if state["accepted"]:
        return {"pending_tool_calls": [], "final_answer": state["final_answer"]}

    obs_text = "\n".join(
        f"[{o['tool']}] {o['result']}" for o in state["observations"]
    )
    assumptions_text = "\n".join(f"  • {a}" for a in state["assumptions"]) or "  (none)"
    hypotheses_text  = "\n".join(f"  • {h}" for h in state["hypotheses"])  or "  (none)"
    notes_text       = "\n".join(f"  • {n}" for n in state["diagnostic_notes"]) or "  (none)"
    uncert_text      = "\n".join(f"  • {u}" for u in state["uncertainties"]) or "  (none)"

    prompt = f"""You are a System Diagnostics Agent equipped with an EXPLICIT HERMENEUTIC CHAMBER (interpretation layer).

INSTANCE: {state["instance_id"]}

━━━━ HERMENEUTIC CHAMBER OUTPUT (Updated System Interpretation σ) ━━━━
CURRENT UNDERSTANDING:
{state["understanding"] or "(initial assessment pending)"}

ACTIVE ASSUMPTIONS:
{assumptions_text}

COMPETING HYPOTHESES (Probabilities & Stance):
{hypotheses_text}

DIAGNOSTIC NOTES (Key telemetry constraints to enforce):
{notes_text}

REMAINING UNCERTAINTIES & RECOMMENDED NEXT TOOL:
{uncert_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OBSERVATIONS & SYSTEM ALERTS SO FAR:
{obs_text if obs_text else "(none yet)"}

INSTRUCTIONS:
- Choose EXACTLY ONE diagnostic tool per turn.
- Use the Hermeneutic Chamber interpretation above to guide your diagnostic search.
- When new telemetry or system alerts arrive, trust the updated Chamber hypotheses over earlier assumptions.
- When you are confident in your diagnosis, call `submit_diagnosis` with:
    • primary_cause
    • contributing_factors
    • supporting_evidence
    • confidence
    • rejected_alternatives
"""

    response = _llm_with_tools.invoke(prompt)

    try:
        print("\n" + "="*70)
        print("  [ARM B'] AGENT RESPONSE")
        print(f"  Content: {response.content}")
        print(f"  Tool calls: {response.tool_calls}")
        print("="*70)
    except UnicodeEncodeError:
        print("  [ARM B'] AGENT RESPONSE (unicode suppressed)")

    return {
        "pending_tool_calls": response.tool_calls,
        "final_answer": str(response.content),
        "step_count": state["step_count"] + 1,
    }


def tool_node(state: ArmBState) -> dict:
    tool_map = {t.name: t for t in ALL_TOOLS}

    observations = list(state["observations"])
    tools_called = list(state["tools_called"])
    tool_step_count = state["tool_step_count"]
    available_perturbations = list(state["available_perturbations"])
    accepted = state["accepted"]
    submission = dict(state.get("submission", {}))
    verifier_result = dict(state.get("verifier_result", {}))

    for tc in state["pending_tool_calls"]:
        tool_name = tc["name"]
        tool_args = tc.get("args", {})

        tool_fn = tool_map.get(tool_name)
        result = tool_fn.invoke(tool_args) if tool_fn else {"error": f"Unknown tool: {tool_name}"}

        try:
            print(f"\n===== [ARM B'] TOOL EXECUTED: {tool_name} =====")
            print(f"Result: {result}")
        except UnicodeEncodeError:
            print(f"\n===== [ARM B'] TOOL EXECUTED: {tool_name} (result printed with unicode replacement) =====")

        observations.append({"tool": tool_name, "result": result})
        tools_called.append(tool_name)
        tool_step_count += 1

        # Check for scheduled perturbation injection AFTER tool execution (Req 5 & 14)
        for event in state["evidence_schedule"]:
            t = event["t"]
            if tool_step_count >= t and event not in available_perturbations:
                perturbation_obs = {
                    "tool": "SYSTEM_PERTURBATION",
                    "result": {
                        "type": event["type"],
                        "content": event["content"].strip(),
                    },
                }
                observations.append(perturbation_obs)
                available_perturbations.append(event)
                print(f"\n===== [ARM B'] PERTURBATION INJECTED (t={t}) =====")
                print(event["content"].strip())

        # If agent calls submit_diagnosis, evaluate with verifier
        if tool_name == "submit_diagnosis" and isinstance(result, dict):
            submission = result
            v_res = verify_diagnosis(submission, state["instance"], len(available_perturbations))
            verifier_result = v_res
            accepted = v_res["passed"]
            print(f"\n===== [ARM B'] VERIFIER EVALUATION =====")
            print(f"Passed: {accepted} | Violations: {v_res.get('violations')}")

    return {
        "observations": observations,
        "tools_called": tools_called,
        "pending_tool_calls": [],
        "tool_step_count": tool_step_count,
        "available_perturbations": available_perturbations,
        "accepted": accepted,
        "submission": submission,
        "verifier_result": verifier_result,
    }


def chamber_node(state: ArmBState) -> dict:
    prior_state = {
        "understanding": state.get("understanding", ""),
        "assumptions": state.get("assumptions", []),
        "hypotheses": state.get("hypotheses", []),
        "diagnostic_notes": state.get("diagnostic_notes", []),
        "uncertainties": state.get("uncertainties", []),
    }
    chamber_out = update_chamber_state(state["task"], state["observations"], prior_state)
    history = list(state.get("chamber_history", []))
    history.append({
        "step": state["step_count"],
        "tool_step": state["tool_step_count"],
        "output": chamber_out,
    })

    return {
        "understanding": chamber_out["understanding"],
        "assumptions": chamber_out["assumptions"],
        "hypotheses": chamber_out["hypotheses"],
        "what_changed": chamber_out["what_changed"],
        "diagnostic_notes": chamber_out["diagnostic_notes"],
        "uncertainties": chamber_out["uncertainties"],
        "chamber_history": history,
    }


def should_continue(state: ArmBState) -> str:
    if state["accepted"]:
        return "end"
    if state["step_count"] >= MAX_STEPS:
        print(f"\n[ARM B'] Step cap ({MAX_STEPS}) reached — terminating.")
        return "end"
    if state["pending_tool_calls"]:
        return "tool"
    return "end"


def build_arm_b_graph():
    builder = StateGraph(ArmBState)
    builder.add_node("agent", agent_node)
    builder.add_node("tool", tool_node)
    builder.add_node("chamber", chamber_node)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue, {"tool": "tool", "end": END})
    builder.add_edge("tool", "chamber")
    builder.add_edge("chamber", "agent")

    return builder.compile()


arm_b_graph = build_arm_b_graph()


def run_arm_b(instance_id: str, instance: dict, env: SystemEnvironment) -> dict:
    set_active_environment(env)

    initial_state: ArmBState = {
        "instance_id": instance_id,
        "instance": instance,
        "task": instance["initial_spec"]["goal"],
        "observations": [],
        "tools_called": [],
        "pending_tool_calls": [],
        "final_answer": "",
        "tool_step_count": 0,
        "evidence_schedule": instance.get("evidence_schedule", []),
        "available_perturbations": [],
        "accepted": False,
        "step_count": 0,
        "submission": {},
        "verifier_result": {},
        "understanding": "",
        "assumptions": [],
        "hypotheses": [],
        "what_changed": "",
        "diagnostic_notes": [],
        "uncertainties": [],
        "chamber_history": [],
    }
    return arm_b_graph.invoke(initial_state)
