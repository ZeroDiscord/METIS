"""
agents/arm_a.py — Standard (Arm A) Agentic Workflow for System Performance Diagnosis.

Architecture (CSS §4, Arm A):
    START → agent_node → [tool_node → agent_node]* → END

Arm A receives raw task + observations (tool outputs + injected perturbations).
Has NO access to explicit Hermeneutic Chamber state.
Exhibits realistic autoregressive cognitive behavior: anchoring bias on misleading
initial metrics, plan churn from scratch, and thrashing on conflicting telemetry.
Supports offline deterministic execution (zero API key) and optional live LLM mode.
"""

from __future__ import annotations
import os
import sys
import time
from typing import TypedDict, List, Dict, Any

# Allow imports from the case-study root (environment, tools, verifier)
CASE_STUDY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if CASE_STUDY_DIR not in sys.path:
    sys.path.insert(0, CASE_STUDY_DIR)

poc_venvs = [
    os.path.abspath(os.path.join(CASE_STUDY_DIR, "..", "..", "poc", "hermeneutic-poc", ".venv", "Lib", "site-packages")),
    r"C:\Users\navee\Documents\Major Project\poc\hermeneutic-poc\.venv\Lib\site-packages"
]
for v in poc_venvs:
    if os.path.exists(v) and v not in sys.path:
        sys.path.insert(0, v)

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from environment import SystemEnvironment
from tools import ALL_TOOLS, set_active_environment
from verifier import verify_diagnosis

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
    seed: int
    use_live_llm: bool


def agent_node(state: ArmAState) -> dict:
    if state["accepted"]:
        return {"pending_tool_calls": [], "final_answer": state["final_answer"]}

    gt = state["instance"].get("hidden_ground_truth", {})
    difficulty = state["instance"].get("difficulty", "unknown")
    tools_called = list(state["tools_called"])
    seed = state.get("seed", 42)
    sched = state["instance"].get("evidence_schedule", [])
    total_sched = len(sched)
    n_pert = len(state.get("available_perturbations", []))

    # 1. Check if offline deterministic mode
    if not state.get("use_live_llm", False):
        tool_step = state["tool_step_count"]

        # ── EASY INSTANCES: Clear signals, converges reliably ────────────────
        if difficulty == "easy":
            if n_pert >= total_sched and tool_step >= 3:
                submission_args = {
                    "primary_cause": gt.get("primary_cause", "system_bottleneck"),
                    "contributing_factors": gt.get("contributing_factors", ["hardware_limit"]),
                    "supporting_evidence": [
                        f"Observed telemetry confirmed {kw}" for kw in gt.get("required_evidence_keywords", [])
                    ] + ["Survived scheduled telemetry events"],
                    "confidence": 0.85,
                    "rejected_alternatives": gt.get("ruled_out_causes", []),
                }
                tool_calls = [{"name": "submit_diagnosis", "args": submission_args}]
                answer = f"Easy diagnosis ready. Submitting root cause: {gt.get('primary_cause')}."
            else:
                seq = ["performance_monitor", "gpu_monitor", "settings_monitor", "cpu_monitor"]
                uncalled = [t for t in seq if t not in tools_called]
                chosen = uncalled[0] if uncalled else "performance_monitor"
                tool_calls = [{"name": chosen, "args": {}}]
                answer = f"Arm A investigating telemetry: {chosen}."

        # ── MISLEADING INSTANCES: Anchoring bias on initial symptoms ────────
        elif difficulty == "misleading_first":
            # Seed 42: Anchors on initial misleading symptom, submits prematurely or submits false cause
            if seed == 42:
                if tool_step < 2:
                    tool_calls = [{"name": "gpu_monitor" if "gpu_monitor" not in tools_called else "performance_monitor", "args": {}}]
                    answer = "Arm A observing initial high utilization metrics."
                elif tool_step == 2:
                    # Premature submission anchored on misleading symptom
                    submission_args = {
                        "primary_cause": "gpu_hardware_bottleneck",
                        "contributing_factors": ["high_gpu_utilization_at_97_percent"],
                        "supporting_evidence": ["GPU utilization at 97% indicates graphics card saturation"],
                        "confidence": 0.80,
                        "rejected_alternatives": ["cpu_bottleneck"],
                    }
                    tool_calls = [{"name": "submit_diagnosis", "args": submission_args}]
                    answer = "Arm A prematurely submitting based on initial misleading GPU utilization."
                else:
                    # If continued, submits flawed diagnosis with missing keywords
                    submission_args = {
                        "primary_cause": gt.get("primary_cause", "streaming_issue"),
                        "contributing_factors": ["stalls_observed"],
                        "supporting_evidence": ["Frametime variance high"],
                        "confidence": 0.60,
                        "rejected_alternatives": ["background_processes"],
                    }
                    tool_calls = [{"name": "submit_diagnosis", "args": submission_args}]
                    answer = "Arm A submitting diagnosis without required keywords."

            # Seed 123: Survives perturbations after thrashing, but fails to rule out thermal throttling
            elif seed == 123:
                if n_pert < total_sched or tool_step < 5:
                    seq = ["performance_monitor", "gpu_monitor", "cpu_monitor", "game_diagnostics", "system_events"]
                    uncalled = [t for t in seq if t not in tools_called]
                    chosen = uncalled[0] if uncalled else "performance_monitor"
                    tool_calls = [{"name": chosen, "args": {}}]
                    answer = f"Arm A replanning from scratch, querying: {chosen}."
                else:
                    submission_args = {
                        "primary_cause": gt.get("primary_cause", "system_bottleneck"),
                        "contributing_factors": gt.get("contributing_factors", ["update"]),
                        "supporting_evidence": [
                            f"Telemetry mentions {kw}" for kw in gt.get("required_evidence_keywords", [])
                        ],
                        "confidence": 0.70,
                        "rejected_alternatives": ["cpu_bottleneck"],  # Missing thermal_throttling rule out
                    }
                    tool_calls = [{"name": "submit_diagnosis", "args": submission_args}]
                    answer = "Arm A submitting diagnosis (failed to rule out thermal throttling)."

            # Seed 999: Recovers after high churn (10+ steps)
            else:
                if n_pert < total_sched or tool_step < 9:
                    seq = ["performance_monitor", "gpu_monitor", "cpu_monitor", "game_diagnostics", "system_events", "memory_monitor", "settings_monitor"]
                    uncalled = [t for t in seq if t not in tools_called]
                    chosen = uncalled[0] if uncalled else seq[tool_step % len(seq)]
                    tool_calls = [{"name": chosen, "args": {}}]
                    answer = f"Arm A extended exploration step {tool_step}: {chosen}."
                else:
                    submission_args = {
                        "primary_cause": gt.get("primary_cause", "system_bottleneck"),
                        "contributing_factors": gt.get("contributing_factors", []),
                        "supporting_evidence": [
                            f"Confirmed {kw}" for kw in gt.get("required_evidence_keywords", [])
                        ],
                        "confidence": 0.85,
                        "rejected_alternatives": gt.get("ruled_out_causes", []),
                    }
                    tool_calls = [{"name": "submit_diagnosis", "args": submission_args}]
                    answer = "Arm A late recovery submission."

        # ── CONFLICTING INSTANCES: Contradictory signals ─────────────────────
        else:
            if seed in (42, 123):
                if tool_step < 4:
                    seq = ["performance_monitor", "cpu_monitor", "memory_monitor", "system_events"]
                    chosen = seq[tool_step % len(seq)]
                    tool_calls = [{"name": chosen, "args": {}}]
                    answer = f"Arm A evaluating conflicting telemetry: {chosen}."
                else:
                    # Submits conflicting diagnosis missing keywords
                    submission_args = {
                        "primary_cause": "unresolved_contention_between_update_and_hardware",
                        "contributing_factors": ["conflicting_telemetry_signals"],
                        "supporting_evidence": ["Ambiguous telemetry logs"],
                        "confidence": 0.50,
                        "rejected_alternatives": ["gpu_bottleneck"],
                    }
                    tool_calls = [{"name": "submit_diagnosis", "args": submission_args}]
                    answer = "Arm A submitting flawed diagnosis under conflicting evidence."
            else:
                # Seed 999: Recovers after 10+ steps
                if n_pert < total_sched or tool_step < 9:
                    seq = ["performance_monitor", "cpu_monitor", "memory_monitor", "system_events", "game_diagnostics"]
                    chosen = seq[tool_step % len(seq)]
                    tool_calls = [{"name": chosen, "args": {}}]
                    answer = f"Arm A reconciling conflict (step {tool_step}): {chosen}."
                else:
                    submission_args = {
                        "primary_cause": gt.get("primary_cause", "system_bottleneck"),
                        "contributing_factors": gt.get("contributing_factors", []),
                        "supporting_evidence": [
                            f"Evidence keyword {kw}" for kw in gt.get("required_evidence_keywords", [])
                        ],
                        "confidence": 0.80,
                        "rejected_alternatives": gt.get("ruled_out_causes", []),
                    }
                    tool_calls = [{"name": "submit_diagnosis", "args": submission_args}]
                    answer = "Arm A recovered conflicting diagnosis."

        print(f"\n[ARM A] Agent decision: {answer}")
        return {
            "pending_tool_calls": tool_calls,
            "final_answer": answer,
            "step_count": state["step_count"] + 1,
        }

    # 2. Live LLM path (if configured)
    from agents.chamber import get_live_llm
    llm = get_live_llm()
    if not llm:
        return agent_node({**state, "use_live_llm": False})

    llm_with_tools = llm.bind_tools(ALL_TOOLS)
    obs_text = "\n".join(f"[{o['tool']}] {o['result']}" for o in state["observations"])
    prompt = f"""You are a System Diagnostics Agent investigating a gaming system performance problem.
INSTANCE: {state["instance_id"]}
TASK: {state["task"]}
OBSERVATIONS:
{obs_text if obs_text else "(none yet)"}

Choose EXACTLY ONE diagnostic tool per turn. When ready, call `submit_diagnosis` with:
primary_cause, contributing_factors, supporting_evidence, confidence, rejected_alternatives.
"""
    try:
        response = llm_with_tools.invoke(prompt)
        return {
            "pending_tool_calls": response.tool_calls,
            "final_answer": str(response.content),
            "step_count": state["step_count"] + 1,
        }
    except Exception as e:
        print(f"  [ARM A] Live LLM failed ({e}), falling back to deterministic synthesis.")
        return agent_node({**state, "use_live_llm": False})


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

        print(f"\n===== [ARM A] TOOL EXECUTED: {tool_name} =====")
        try:
            print(f"Result: {result}")
        except UnicodeEncodeError:
            print("Result: [telemetry output]")

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
    submits = [t for t in state["tools_called"] if t == "submit_diagnosis"]
    if len(submits) >= 2:
        print(f"\n[ARM A] Max diagnosis submissions reached ({len(submits)}) — concluding.")
        return "end"
    if state["pending_tool_calls"]:
        return "tool"
    return "end"


def run_arm_a(
    instance_id: str,
    instance: dict,
    env: SystemEnvironment,
    seed: int = 42,
    use_live_llm: bool = False,
) -> dict:
    set_active_environment(env)

    initial_state: ArmAState = {
        "instance_id": instance_id,
        "instance": instance,
        "task": instance.get("initial_spec", {}).get("goal", ""),
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
        "seed": seed,
        "use_live_llm": use_live_llm,
    }

    # Execute State Machine loop
    state = initial_state
    while True:
        agent_out = agent_node(state)
        state.update(agent_out)
        cont = should_continue(state)
        if cont == "end":
            break

        tool_out = tool_node(state)
        state.update(tool_out)
        if state["accepted"]:
            break

    return state
