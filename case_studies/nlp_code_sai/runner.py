"""
nlp_code_experiment.py — Orchestrates the full NLP/Code case study experiment.

Runs all 10 instances × 2 arms (A, B') × 3 seeds = 60 total runs.
Logs each run to JSONL and aggregates metrics into results.csv.

Usage:
    python nlp_code_experiment.py                    # full 60-run experiment
    python nlp_code_experiment.py --instance nlpcode-001 --arm A --seed 42  # single run
    python nlp_code_experiment.py --pilot            # 10 runs (1 seed per instance per arm)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import time
from datetime import datetime

import yaml

from agents.arm_a import run_arm_a
from agents.arm_b import run_arm_b

# ── Config ─────────────────────────────────────────────────────────────────
BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "case_studies", "nlp_code_sai",
)
INSTANCES_DIR  = os.path.join(BASE_DIR, "instances")
WORKSPACE_DIR  = os.path.join(BASE_DIR, "agent_workspace")
SOLUTIONS_DIR  = os.path.join(BASE_DIR, "solutions")
RUNS_DIR       = os.path.join(BASE_DIR, "runs")
RESULTS_CSV    = os.path.join(BASE_DIR, "results.csv")

INSTANCE_IDS = [f"nlpcode-{str(i).zfill(3)}" for i in range(1, 11)]
ARMS         = ["A", "B"]
SEEDS        = [42, 43, 44]

MAX_TOOL_CALLS = 20   # step cap per instance per arm (CSS §4 control)


# ── Helpers ────────────────────────────────────────────────────────────────
def load_instance(instance_id: str) -> dict:
    path = os.path.join(INSTANCES_DIR, f"{instance_id}.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


def reset_workspace(instance_id: str) -> None:
    """Reset the workspace file to its placeholder state before each run."""
    number = instance_id.split("-")[1]
    workspace_path = os.path.join(WORKSPACE_DIR, f"workspace_{number}.py")
    fn_names = {
        "001": "filter_records",   "002": "compute_score",
        "003": "format_output",    "004": "sort_records",
        "005": "merge_streams",    "006": "find_largest",
        "007": "classify_tokens",  "008": "resolve_conflicts",
        "009": "batch_process",    "010": "aggregate_results",
    }
    fn = fn_names.get(number, "solution")
    with open(workspace_path, "w") as f:
        f.write(f"def {fn}(*args, **kwargs):\n    pass\n")

    # FIX #7: delete __pycache__ so Python doesn't serve stale bytecode
    # from a previous run's compiled workspace module.
    pycache = os.path.join(WORKSPACE_DIR, "__pycache__")
    if os.path.isdir(pycache):
        shutil.rmtree(pycache)


# ── Metrics ────────────────────────────────────────────────────────────────
def compute_metrics(state: dict, arm: str, instance_id: str,
                    instance: dict, seed: int, elapsed: float) -> dict:
    """
    Compute CSS §5 Tier 1 + Tier 2 metrics from the final agent state.

    Tier 1 (simplified for PoC):
      R1 — proxy: fraction of perturbations after which interpretation
           visibly changed (Arm B' only; Arm A = N/A)
      R4 — repeated-error rate: heuristic from tool call sequence
      R5 — verifier calls to acceptance (run_tests calls until accepted)
      R6 — recovery rate: accepted == True → 1, else 0
      R7 — recovery latency: total LLM calls

    Tier 2:
      Q1 — final task success (accepted)
      C1 — LLM calls (≈ number of agent_node invocations = len(tools_called)+1)
      C2 — tokens: not directly available; logged as -1
      C3 — tool calls total
      C4 — wall-clock seconds
      C5 — Chamber updates (Arm B' only)
    """
    tools_called = state.get("tools_called", [])
    test_run_count = state.get("test_run_count", 0)
    accepted = state.get("accepted", False)

    # R5: verifier calls to acceptance
    r5 = test_run_count  # total run_tests calls (cap = MAX_TOOL_CALLS)

    # R6: recovery rate (binary for PoC)
    r6 = 1.0 if accepted else 0.0

    # R7: recovery latency ≈ total tool calls
    r7 = len(tools_called)

    # Q1: final success
    q1 = 1 if accepted else 0

    # Q2: failed tests count (from last run_tests observation)
    q2 = 0
    observations = state.get("observations", [])
    for obs in reversed(observations):
        if obs.get("tool") == "run_tests" and isinstance(obs.get("result"), dict):
            q2 = obs["result"].get("failed_count", 0)
            break

    # C1: approximate LLM calls = number of agent decisions
    c1 = len(tools_called) + 1  # each tool call was preceded by an agent decision

    # C3: tool calls
    c3 = len(tools_called)

    # C4: wall-clock
    c4 = round(elapsed, 2)

    # C5: Chamber activations = all tool calls in Arm B'
    # (Chamber fires once after every tool call, so C5 == C3 for arm B)
    c5 = c3 if arm == "B" else 0

    # R1 proxy (Arm B' only): non-empty WHAT_CHANGED after each perturbation
    r1_proxy = "N/A"
    if arm == "B":
        n_perturbations = len(instance.get("evidence_schedule", []))
        r1_proxy = f"qualitative/{n_perturbations}_perturbations"

    # R4: repeated-error rate (heuristic: fraction of test-runs that failed
    # after a prior run had also failed — proxy for failing to learn)
    fail_sequence = []
    for obs in observations:
        if obs.get("tool") == "run_tests" and isinstance(obs.get("result"), dict):
            fail_sequence.append(obs["result"].get("failed_count", 0) > 0)
    r4 = 0.0
    if len(fail_sequence) > 1:
        repeated = sum(
            1 for i in range(1, len(fail_sequence)) if fail_sequence[i] and fail_sequence[i - 1]
        )
        r4 = round(repeated / (len(fail_sequence) - 1), 4)

    return {
        "domain":       "nlp_code",
        "instance_id":  instance_id,
        "difficulty":   instance.get("difficulty", "unknown"),
        "arm":          arm,
        "seed":         seed,
        # Tier 1
        "R1":  r1_proxy,
        "R2":  "N/A",       # requires reference state — logged qualitatively
        "R3":  "N/A",       # requires sub-decision tracking
        "R4":  r4,
        "R5":  r5,
        "R6":  r6,
        "R7":  r7,
        # Tier 2
        "Q1":  q1,
        "Q2":  q2,
        "Q3":  "N/A",
        "Q4":  "N/A",
        "C1":  c1,
        "C2":  -1,          # tokens not directly tracked by LangChain here
        "C3":  c3,
        "C4":  c4,
        "C5":  c5,
    }


# ── Single run ─────────────────────────────────────────────────────────────
def run_single(instance_id: str, arm: str, seed: int, verbose: bool = True) -> dict:
    """Run one (instance, arm, seed) triple. Returns metrics dict."""
    instance = load_instance(instance_id)
    task     = instance["initial_spec"]["goal"].strip()
    schedule = instance.get("evidence_schedule", [])

    # Reset workspace to placeholder before each run
    reset_workspace(instance_id)

    if verbose:
        print(f"\n{'='*70}")
        print(f"  EXPERIMENT: instance={instance_id}  arm={arm}  seed={seed}")
        print(f"{'='*70}")

    t0 = time.time()
    try:
        if arm == "A":
            final_state = run_arm_a(instance_id, task, schedule)
        else:
            final_state = run_arm_b(instance_id, task, schedule)
    except Exception as exc:
        print(f"  [ERROR] Run failed: {exc}")
        final_state = {
            "tools_called": [], "test_run_count": 0,
            "accepted": False, "observations": [],
        }
    elapsed = time.time() - t0

    metrics = compute_metrics(final_state, arm, instance_id, instance, seed, elapsed)

    # ── Write JSONL log ────────────────────────────────────────────────────
    os.makedirs(RUNS_DIR, exist_ok=True)
    log_path = os.path.join(
        RUNS_DIR,
        f"{instance_id}_arm{arm}_seed{seed}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl",
    )
    with open(log_path, "w") as f:
        log_entry = {
            "instance_id":  instance_id,
            "arm":          arm,
            "seed":         seed,
            "metrics":      metrics,
            "tools_called": final_state.get("tools_called", []),
            "test_run_count": final_state.get("test_run_count", 0),
            "accepted":     final_state.get("accepted", False),
            "final_answer": final_state.get("final_answer", ""),
            "observations": [
                {"tool": o["tool"], "result": str(o["result"])[:500]}
                for o in final_state.get("observations", [])
            ],
        }
        # Arm B' extra
        if arm == "B":
            log_entry["understanding"]        = final_state.get("understanding", "")
            log_entry["assumptions"]          = final_state.get("assumptions", [])
            log_entry["implementation_notes"] = final_state.get("implementation_notes", [])
        f.write(json.dumps(log_entry) + "\n")

    if verbose:
        print(f"\n  ✓ Done | accepted={metrics['Q1']} | test_runs={metrics['R5']} | "
              f"tool_calls={metrics['C3']} | time={metrics['C4']}s")

    return metrics


# ── CSV writer ──────────────────────────────────────────────────────────────
CSV_FIELDS = [
    "domain", "instance_id", "difficulty", "arm", "seed",
    "R1", "R2", "R3", "R4", "R5", "R6", "R7",
    "Q1", "Q2", "Q3", "Q4", "C1", "C2", "C3", "C4", "C5",
]


def append_results_csv(rows: list[dict]) -> None:
    file_exists = os.path.isfile(RESULTS_CSV)
    with open(RESULTS_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="NLP/Code METIS case study experiment")
    parser.add_argument("--instance", default=None, help="Run a single instance (e.g. nlpcode-001)")
    parser.add_argument("--arm",      default=None, choices=["A", "B"], help="Single arm")
    parser.add_argument("--seed",     default=None, type=int, help="Single seed")
    parser.add_argument("--pilot",    action="store_true", help="Pilot: 1 seed per instance per arm")
    args = parser.parse_args()

    # ── Determine run matrix ───────────────────────────────────────────────
    if args.instance and args.arm and args.seed is not None:
        run_matrix = [(args.instance, args.arm, args.seed)]
    elif args.pilot:
        run_matrix = [(iid, arm, 42) for iid in INSTANCE_IDS for arm in ARMS]
    else:
        run_matrix = [
            (iid, arm, seed)
            for iid  in INSTANCE_IDS
            for arm  in ARMS
            for seed in SEEDS
        ]

    print(f"\n🧪 NLP/Code METIS Experiment")
    print(f"   Runs planned: {len(run_matrix)}")
    print(f"   Results CSV:  {RESULTS_CSV}\n")

    all_metrics = []
    for instance_id, arm, seed in run_matrix:
        metrics = run_single(instance_id, arm, seed)
        all_metrics.append(metrics)
        append_results_csv([metrics])

    # ── Summary table ──────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("  EXPERIMENT SUMMARY")
    print(f"{'='*70}")
    print(f"{'Instance':<18} {'Arm':<5} {'Seed':<6} {'Q1':>4} {'R5':>5} {'C3':>6}")
    print("-" * 50)
    for m in all_metrics:
        print(f"{m['instance_id']:<18} {m['arm']:<5} {m['seed']:<6} "
              f"{m['Q1']:>4} {m['R5']:>5} {m['C3']:>6}")

    # ── Aggregate A vs B' comparison ───────────────────────────────────────
    a_success = [m["Q1"] for m in all_metrics if m["arm"] == "A"]
    b_success = [m["Q1"] for m in all_metrics if m["arm"] == "B"]
    a_r5 = [m["R5"] for m in all_metrics if m["arm"] == "A"]
    b_r5 = [m["R5"] for m in all_metrics if m["arm"] == "B"]

    def mean(lst): return sum(lst) / len(lst) if lst else 0.0

    print(f"\n  Arm A — Q1 success rate: {mean(a_success):.2f}  |  mean R5: {mean(a_r5):.1f}")
    print(f"  Arm B'— Q1 success rate: {mean(b_success):.2f}  |  mean R5: {mean(b_r5):.1f}")
    print(f"\n  Results written to: {RESULTS_CSV}")
    print(f"  Run logs in:        {RUNS_DIR}/")


if __name__ == "__main__":
    main()
