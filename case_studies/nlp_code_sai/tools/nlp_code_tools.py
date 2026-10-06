"""
nlp_code_tools.py — LangChain tools for the NLP/Code case study agents.

Tools available to both Arm A and Arm B':
  • read_spec        — returns the initial spec for an instance
  • read_workspace   — returns the current code in the agent workspace
  • write_code       — writes/overwrites the agent's implementation
  • run_tests        — runs the verifier and returns pass/fail data

The evidence schedule (perturbations) is NOT exposed as a tool.
Instead, the experiment runner injects perturbations into the observations
list automatically after each run_tests call, and the agents see them there.
"""

import os
import sys
import yaml
from langchain_core.tools import tool


# ── Paths ──────────────────────────────────────────────────────────────────
_BASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "case_studies", "nlp_code_sai",
)
_INSTANCES_DIR = os.path.join(_BASE, "instances")
_WORKSPACE_DIR = os.path.join(_BASE, "agent_workspace")
_VERIFIER_DIR  = os.path.join(_BASE, "verifier")

# FIX #1: Import run_verifier at module load time (not inside the tool function)
# to avoid sys.path pollution and stale-module issues on repeated calls.
if _VERIFIER_DIR not in sys.path:
    sys.path.insert(0, _VERIFIER_DIR)
from run_verifier import run_verifier as _run_verifier  # type: ignore


def _instance_path(instance_id: str) -> str:
    return os.path.join(_INSTANCES_DIR, f"{instance_id}.yaml")


def _workspace_path(instance_id: str) -> str:
    number = instance_id.split("-")[1]
    return os.path.join(_WORKSPACE_DIR, f"workspace_{number}.py")


def _load_instance(instance_id: str) -> dict:
    with open(_instance_path(instance_id)) as f:
        return yaml.safe_load(f)


# ── Tool definitions ───────────────────────────────────────────────────────

@tool
def read_spec(instance_id: str) -> dict:
    """
    Read the initial natural-language specification for the given instance.

    Returns the task goal, constraints, and any prior evidence.
    Call this first to understand what function to implement.
    """
    try:
        instance = _load_instance(instance_id)
        spec = instance["initial_spec"]
        return {
            "instance_id": instance_id,
            "goal": spec["goal"].strip(),
            "constraints": spec.get("constraints", []),
            "prior_evidence": spec.get("prior_evidence", []),
        }
    except FileNotFoundError:
        return {"error": f"Instance '{instance_id}' not found."}


@tool
def read_workspace(instance_id: str) -> dict:
    """
    Read the current content of the agent workspace for the given instance.

    Returns the current Python code (your implementation so far).
    Use this to review what you have written before making changes.
    """
    path = _workspace_path(instance_id)
    if not os.path.isfile(path):
        return {"code": "", "message": "Workspace is empty."}
    with open(path) as f:
        code = f.read()
    return {"instance_id": instance_id, "code": code}


@tool
def write_code(instance_id: str, code: str) -> dict:
    """
    Write (or overwrite) your Python implementation to the agent workspace.

    The 'code' parameter must be the COMPLETE Python module content —
    include all imports and the full function body.
    This overwrites the previous implementation entirely.
    """
    path = _workspace_path(instance_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(code)
    return {
        "status": "success",
        "message": f"Code written to workspace for {instance_id}.",
        "lines_written": len(code.splitlines()),
    }


@tool
def run_tests(instance_id: str) -> dict:
    """
    Run the full test suite for the given instance.

    Returns:
      - passed       : True if ALL tests pass
      - failed_tests : list of failed test names
      - passed_count : number of tests that passed
      - failed_count : number of tests that failed
      - total        : total number of tests
      - output       : full test output (truncated to 3000 chars)

    Analyse failed_tests carefully to understand which requirements are
    not yet satisfied. Each test name encodes what it checks.
    """
    return _run_verifier(instance_id)


# ── Convenience list for bind_tools ───────────────────────────────────────
ALL_TOOLS = [read_spec, read_workspace, write_code, run_tests]
