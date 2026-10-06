"""
run_verifier.py — Deterministic verifier for the NLP/Code case study.
Runs the pytest suite for a given instance and returns structured JSON output.

Usage (CLI):
    python run_verifier.py nlpcode-001

Usage (Python API):
    from verifier.run_verifier import run_verifier
    result = run_verifier("nlpcode-001")
    # → {"passed": bool, "failed_tests": [...], "passed_count": int,
    #     "failed_count": int, "total": int, "output": str}
"""

import subprocess
import sys
import os
import re
import json


# ── Paths ──────────────────────────────────────────────────────────────────
CASE_STUDY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.join(CASE_STUDY_DIR, "tests")
WORKSPACE_DIR = os.path.join(CASE_STUDY_DIR, "agent_workspace")


def run_verifier(instance_id: str) -> dict:
    """
    Run the pytest test suite for instance_id.

    Returns:
        {
          "passed": bool,
          "failed_tests": [str, ...],   # FAILED test node IDs
          "passed_count": int,
          "failed_count": int,
          "total": int,
          "output": str                 # truncated stdout for agent context
        }
    """
    # Map instance_id to test file (nlpcode-001 → test_001.py)
    number = instance_id.split("-")[1]
    test_file = os.path.join(TESTS_DIR, f"test_{number}.py")

    if not os.path.isfile(test_file):
        return {
            "passed": False,
            "failed_tests": [f"ERROR: test file not found: {test_file}"],
            "passed_count": 0,
            "failed_count": 0,
            "total": 0,
            "output": f"Test file missing: {test_file}",
        }

    env = {**os.environ, "PYTHONPATH": WORKSPACE_DIR}

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short", "--no-header"],
        capture_output=True,
        text=True,
        env=env,
        cwd=CASE_STUDY_DIR,
    )

    stdout = proc.stdout
    stderr = proc.stderr
    combined = stdout + ("\n" + stderr if stderr.strip() else "")

    # ── Parse failed test node IDs ─────────────────────────────────────────
    failed_tests = []
    for line in stdout.splitlines():
        stripped = line.strip()
        # Match lines like "tests/test_001.py::test_name FAILED"
        if "::" in stripped and "FAILED" in stripped:
            node_id = stripped.split()[0]
            if node_id not in failed_tests and "::" in node_id:
                failed_tests.append(node_id)

    # ── Parse counts ───────────────────────────────────────────────────────
    passed_count = 0
    failed_count = 0

    m_pass = re.search(r"(\d+) passed", stdout)
    if m_pass:
        passed_count = int(m_pass.group(1))

    m_fail = re.search(r"(\d+) failed", stdout)
    if m_fail:
        failed_count = int(m_fail.group(1))

    # If pytest errored before collecting (e.g. import error)
    m_error = re.search(r"(\d+) error", stdout)
    if m_error and failed_count == 0:
        failed_count = int(m_error.group(1))
        if not failed_tests:
            failed_tests.append("COLLECTION_ERROR")

    total = passed_count + failed_count

    return {
        "passed": proc.returncode == 0,
        "failed_tests": failed_tests,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "total": total,
        "output": combined[:3000],  # truncate for LLM context window
    }


# ── CLI entry point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_verifier.py <instance_id>")
        sys.exit(1)
    result = run_verifier(sys.argv[1])
    print(json.dumps(result, indent=2))
