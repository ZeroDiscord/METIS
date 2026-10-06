"""
agents/arm_a.py — Standard (Arm A) Agentic Workflow for System Performance Diagnosis.

Architecture (CSS §4, Arm A):
    START → agent_node → [tool_node → agent_node]* → END

Arm A receives raw task + observations (tool outputs + injected perturbations).
Has NO access to explicit Hermeneutic Chamber state.
"""

from __future__ import annotations
import os
import sys
import time
from typing import TypedDict, List, Dict, Any

# Allow imports from the case-study root (environment, tools, verifier)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph

from environment import SystemEnvironment
from tools import ALL_TOOLS, set_active_environment
from verifier import verify_diagnosis

load_dotenv()

MAX_STEPS = 20


class ArmAState(TypedDict):
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


def get_llm():
    llm = ChatGroq(
        model="openai/gpt-oss-20b",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
        max_retries=20,
    )
    return llm.bind_tools(ALL_TOOLS)



def agent_node(state: ArmAState) -> dict:
    time.sleep(1)
    if state["accepted"]:
        return {"pending_tool_calls": [], "final_answer": state["final_answer"]}

    obs_text = "\n".join(
        f"[{o['tool']}] {o['result']}" for o in state["observations"]
    )

    prompt = f"""You are a System Diagnostics Agent investigating a gaming system performance degradation problem.

INSTANCE: {state["instance_id"]}

TASK:
{state["task"]}

OBSERVATIONS & SYSTEM ALERTS SO FAR:
{obs_text if obs_text else "(none yet)"}

INSTRUCTIONS:
- Choose EXACTLY ONE diagnostic tool per turn.
- Investigate using available diagnostic tools (performance_monitor, cpu_monitor, gpu_monitor, memory_monitor, system_events, game_diagnostics, settings_monitor).
- Pay close attention to ANY lines starting with "NEW TELEMETRY ALERT" or "NEW SYSTEM EVENT" — these represent dynamic system changes and new evidence that may OVERRIDE previous conclusions.
- When you are confident in your diagnosis, call `submit_diagnosis` with:
    • primary_cause
    • contributing_factors
    • supporting_evidence
    • confidence
    • rejected_alternatives
"""

    llm_with_tools = get_llm()
    for attempt in range(10):
        try:
            response = llm_with_tools.invoke(prompt)
            break
        except Exception as exc:
            if "429" in str(exc) or "rate_limit" in str(exc).lower():
                print(f"  [RATE LIMIT 429] Groq daily token limit reached. Retrying in 65s (attempt {attempt+1}/10)...")
                time.sleep(65)
            else:
                raise exc


    try:
        print("\n" + "="*70)
        print("  [ARM A] AGENT RESPONSE")
        print(f"  Content: {response.content}")
        print(f"  Tool calls: {response.tool_calls}")
        print("="*70)
    except UnicodeEncodeError:
        print("  [ARM A] AGENT RESPONSE (unicode suppressed)")

    return {
        "pending_tool_calls": response.tool_calls,
        "final_answer": str(response.content),
        "step_count": state["step_count"] + 1,
    }


def tool_node(state: ArmAState) -> dict:
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
            print(f"\n===== [ARM A] TOOL EXECUTED: {tool_name} =====")
            print(f"Result: {result}")
        except UnicodeEncodeError:
            print(f"\n===== [ARM A] TOOL EXECUTED: {tool_name} (result printed with unicode replacement) =====")

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
                print(f"\n===== [ARM A] PERTURBATION INJECTED (t={t}) =====")
                print(event["content"].strip())

        # If agent calls submit_diagnosis, evaluate with verifier
        if tool_name == "submit_diagnosis" and isinstance(result, dict):
            submission = result
            v_res = verify_diagnosis(submission, state["instance"], len(available_perturbations))
            verifier_result = v_res
            accepted = v_res["passed"]
            print(f"\n===== [ARM A] VERIFIER EVALUATION =====")
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


def should_continue(state: ArmAState) -> str:
    if state["accepted"]:
        return "end"
    if state["step_count"] >= MAX_STEPS:
        print(f"\n[ARM A] Step cap ({MAX_STEPS}) reached — terminating.")
        return "end"
    if state["pending_tool_calls"]:
        return "tool"
    return "end"


def build_arm_a_graph():
    builder = StateGraph(ArmAState)
    builder.add_node("agent", agent_node)
    builder.add_node("tool", tool_node)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue, {"tool": "tool", "end": END})
    builder.add_edge("tool", "agent")

    return builder.compile()


arm_a_graph = build_arm_a_graph()


def run_arm_a(instance_id: str, instance: dict, env: SystemEnvironment) -> dict:
    set_active_environment(env)

    initial_state: ArmAState = {
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
    }
    return arm_a_graph.invoke(initial_state)
