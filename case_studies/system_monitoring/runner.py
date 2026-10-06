"""
runner.py — Orchestrates the System Performance Diagnosis case study experiment.

Runs Arm A and Arm B' on any instance (or full pilot matrix), logs JSONL trajectories
to runs/, and writes summary metrics to results.csv.

Usage:
    python runner.py --instance sysmon-001 --arm A --seed 42
    python runner.py --instance sysmon-001 --arm B --seed 42
    python runner.py --pilot         (runs sysmon-001 on both arms)
    python runner.py --full-pilot    (runs all 10 instances on both arms = 20 runs)
"""

from __future__ import annotations
import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
import yaml

# Ensure agents and root case study dir are on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from environment import SystemEnvironment
from agents.arm_a import run_arm_a
from agents.arm_b import run_arm_b

INSTANCES_DIR = os.path.join(BASE_DIR, "instances")
RUNS_DIR = os.path.join(BASE_DIR, "runs")
RESULTS_CSV = os.path.join(BASE_DIR, "results.csv")

CSV_FIELDS = [
    "domain", "instance_id", "difficulty", "arm", "seed",
    "R1", "R2", "R3", "R4", "R5", "R6", "R7",
    "Q1", "Q2", "Q3", "Q4", "C1", "C2", "C3", "C4", "C5",
]


def load_instance(instance_id: str) -> dict:
    path = os.path.join(INSTANCES_DIR, f"{instance_id}.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def compute_metrics(
    final_state: dict,
    arm: str,
    instance_id: str,
    instance: dict,
    seed: int,
    elapsed: float,
) -> dict:
    tools_called = final_state.get("tools_called", [])
    accepted = final_state.get("accepted", False)
    v_res = final_state.get("verifier_result", {})

    q1 = 1 if accepted else 0
    q2 = len(v_res.get("violations", []))
    r5 = len([t for t in tools_called if t == "submit_diagnosis"])
    r6 = 1.0 if accepted else 0.0
    r7 = len(tools_called)
    c1 = final_state.get("step_count", len(tools_called))
    c3 = len(tools_called)
    c4 = round(elapsed, 2)
    c5 = len(final_state.get("chamber_history", [])) if arm == "B" else 0

    return {
        "domain": "system_monitoring",
        "instance_id": instance_id,
        "difficulty": instance.get("difficulty", "unknown"),
        "arm": arm,
        "seed": seed,
        "R1": f"qualitative/{c5}_updates" if arm == "B" else "N/A",
        "R2": "N/A",
        "R3": "N/A",
        "R4": 0.0,
        "R5": r5,
        "R6": r6,
        "R7": r7,
        "Q1": q1,
        "Q2": q2,
        "Q3": "N/A",
        "Q4": "N/A",
        "C1": c1,
        "C2": -1,
        "C3": c3,
        "C4": c4,
        "C5": c5,
    }


def run_single(instance_id: str, arm: str, seed: int, verbose: bool = True) -> dict:
    instance = load_instance(instance_id)
    env = SystemEnvironment(instance)

    if verbose:
        print(f"\n{'='*70}")
        print(f"  SYSTEM MONITORING EXPERIMENT: instance={instance_id}  arm={arm}  seed={seed}")
        print(f"{'='*70}")

    t0 = time.time()
    try:
        if arm == "A":
            final_state = run_arm_a(instance_id, instance, env)
        else:
            final_state = run_arm_b(instance_id, instance, env)
    except Exception as exc:
        print(f"  [ERROR] Run failed: {exc}")
        import traceback
        traceback.print_exc()
        final_state = {
            "tools_called": [],
            "accepted": False,
            "observations": [],
            "step_count": 0,
            "submission": {},
            "verifier_result": {"passed": False, "violations": [str(exc)]},
        }
    elapsed = time.time() - t0

    metrics = compute_metrics(final_state, arm, instance_id, instance, seed, elapsed)

    os.makedirs(RUNS_DIR, exist_ok=True)
    log_path = os.path.join(
        RUNS_DIR,
        f"{instance_id}_arm{arm}_seed{seed}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl",
    )
    with open(log_path, "w", encoding="utf-8") as f:
        log_entry = {
            "instance_id": instance_id,
            "arm": arm,
            "seed": seed,
            "metrics": metrics,
            "tools_called": final_state.get("tools_called", []),
            "accepted": final_state.get("accepted", False),
            "submission": final_state.get("submission", {}),
            "verifier_result": final_state.get("verifier_result", {}),
            "observations": [
                {"tool": o["tool"], "result": str(o["result"])[:500]}
                for o in final_state.get("observations", [])
            ],
        }
        if arm == "B":
            log_entry["understanding"] = final_state.get("understanding", "")
            log_entry["assumptions"] = final_state.get("assumptions", [])
            log_entry["hypotheses"] = final_state.get("hypotheses", [])
            log_entry["what_changed"] = final_state.get("what_changed", "")
            log_entry["chamber_history"] = final_state.get("chamber_history", [])

        f.write(json.dumps(log_entry, indent=2) + "\n")

    if verbose:
        print(f"\n  [DONE] accepted={metrics['Q1']} | tool_calls={metrics['C3']} | time={metrics['C4']}s")
        print(f"  Log saved: {log_path}")

    return metrics


def append_results_csv(rows: list[dict]) -> None:
    file_exists = os.path.isfile(RESULTS_CSV)
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})


ALL_INSTANCES = [
    "sysmon-001", "sysmon-002", "sysmon-003", "sysmon-004", "sysmon-005",
    "sysmon-006", "sysmon-007", "sysmon-008", "sysmon-009", "sysmon-010",
]


def main():
    parser = argparse.ArgumentParser(description="System Performance Diagnosis Experiment Runner")
    parser.add_argument("--instance", default="sysmon-001", help="Instance ID (e.g. sysmon-001)")
    parser.add_argument("--arm", default=None, choices=["A", "B"], help="Arm choice (A or B)")
    parser.add_argument("--seed", default=42, type=int, help="Random seed")
    parser.add_argument("--pilot", action="store_true", help="Run sysmon-001 on both arms")
    parser.add_argument("--full-pilot", action="store_true", help="Run all 10 instances on both arms (20 runs)")
    args = parser.parse_args()

    if getattr(args, 'full_pilot', False):
        run_matrix = [(iid, arm, 42) for iid in ALL_INSTANCES for arm in ["A", "B"]]
    elif args.pilot:
        run_matrix = [("sysmon-001", "A", 42), ("sysmon-001", "B", 42)]
    elif args.arm:
        run_matrix = [(args.instance, args.arm, args.seed)]
    else:
        run_matrix = [(args.instance, "A", args.seed), (args.instance, "B", args.seed)]

    print("\n[EXPERIMENT] System Performance Diagnosis Experiment")
    print("   Runs planned: %d" % len(run_matrix))
    print("   Results CSV:  %s\n" % RESULTS_CSV)

    all_metrics = []
    for iid, arm, seed in run_matrix:
        metrics = run_single(iid, arm, seed)
        all_metrics.append(metrics)
        append_results_csv([metrics])

    print("\n" + "="*70)
    print("  EXPERIMENT SUMMARY")
    print("="*70)
    for m in all_metrics:
        try:
            print("Instance: %s | Arm: %s | Success (Q1): %s | Tool Calls: %s | Time: %ss" % (
                m['instance_id'], m['arm'], m['Q1'], m['C3'], m['C4']
            ))
        except UnicodeEncodeError:
            print(("Instance: %s | Arm: %s | Success (Q1): %s | Tool Calls: %s | Time: %ss" % (
                m['instance_id'], m['arm'], m['Q1'], m['C3'], m['C4']
            )).encode('ascii', errors='replace').decode())


if __name__ == "__main__":
    main()
