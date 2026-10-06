"""
METIS Case Study Runner — Biomedical Variant Classification (ACMG/AMP Standards)
================================================================================
Executes the experimental protocol across:
- 12 evaluation instances (4 easy, 4 misleading, 4 conflicting)
- 2 experimental arms:
    - Arm A: Standard autoregressive baseline (replanning from scratch)
    - Arm B': Hermeneutic Chamber agent with explicit interpretive state sigma
- 3 random seeds: 42, 123, 999
Total executions: 12 x 2 x 3 = 72 runs.

Generates:
- runs/run_{arm}_{instance_id}_{seed}.json: Per-run execution traces
- results.csv: Standard CSS v1.0 schema containing R1-R7, Q1-Q4, C1-C5 metrics
"""

from __future__ import annotations
import os
import sys
import json
import csv
import time
import numpy as np
from typing import Dict, Any, List

# Setup paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

poc_venvs = [
    os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "..", "poc", "hermeneutic-poc", ".venv", "Lib", "site-packages")),
    r"C:\Users\navee\Documents\Major Project\poc\hermeneutic-poc\.venv\Lib\site-packages"
]
for v in poc_venvs:
    if os.path.exists(v) and v not in sys.path:
        sys.path.insert(0, v)

poc_envs = [
    os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "..", "poc", "hermeneutic-poc", ".env")),
    r"C:\Users\navee\Documents\Major Project\poc\hermeneutic-poc\.env"
]
for e in poc_envs:
    if os.path.exists(e):
        try:
            import dotenv
            dotenv.load_dotenv(e)
            break
        except Exception:
            pass

from agents.agent_arm_a import AutoregressiveAgent
from agents.agent_arm_b import HermeneuticAgent
from analysis.metrics import (
    compute_revision_distance,
    compute_minimal_repair_target,
    compute_preserved_valid_work,
    compute_brier_score
)
from verifier.acmg_verifier import verify_interpretation

SEEDS = [42, 123, 999]
INSTANCES_DIR = os.path.join(CURRENT_DIR, "instances")
RUNS_DIR = os.path.join(CURRENT_DIR, "runs")
RESULTS_CSV = os.path.join(CURRENT_DIR, "results.csv")

CSV_HEADER = [
    "domain", "instance_id", "difficulty", "arm", "seed",
    "R1", "R2", "R3", "R4", "R5", "R6", "R7",
    "Q1", "Q2", "Q3", "Q4",
    "C1", "C2", "C3", "C4", "C5"
]

def load_instances() -> List[Dict[str, Any]]:
    instances = []
    files = sorted([f for f in os.listdir(INSTANCES_DIR) if f.endswith(".json")])
    for f in files:
        with open(os.path.join(INSTANCES_DIR, f), "r", encoding="utf-8") as fp:
            instances.append(json.load(fp))
    return instances

def run_arm_a_instance(instance: Dict[str, Any], seed: int) -> Dict[str, Any]:
    agent = AutoregressiveAgent(seed=seed)
    task_spec = instance["initial_spec"]
    gene_rules = instance["gene_rules"]
    ground_truth = instance["ground_truth"]
    ref_criteria = set(ground_truth.get("expected_criteria", []))
    
    cumulative_evidence = []
    prev_state = {
        "classification": "VUS",
        "active_criteria": ["PM2"] if instance["difficulty"] != "easy" else ["PVS1"],
        "assumptions": ["Initial assumption"],
        "constraints": [],
        "hypotheses": ["VUS"],
        "belief": {c: 0.2 for c in ["Pathogenic", "Likely pathogenic", "VUS", "Likely benign", "Benign"]},
        "plan": ["init"]
    }
    
    deltas = []
    r2_ratios = []
    r3_preservations = []
    repeated_error_count = 0
    withdrawn_criteria_history = set()
    total_verifier_calls = 0
    recovered_count = 0
    total_perturbations = len(instance["evidence_schedule"])
    log_records = []

    for perturbation in instance["evidence_schedule"]:
        cumulative_evidence.append(perturbation)
        
        step_res = agent.run_step(task_spec, cumulative_evidence, gene_rules)
        curr_state = step_res["state"]
        v_rep = step_res["verifier_report"]
        
        delta = compute_revision_distance(prev_state, curr_state)
        deltas.append(delta)
        
        delta_star = compute_minimal_repair_target(prev_state, ground_truth)
        r2 = delta / delta_star if delta_star > 1e-4 else 1.0
        r2_ratios.append(r2)
        
        prev_crit = set(prev_state.get("active_criteria", []))
        curr_crit = set(curr_state.get("active_criteria", []))
        r3 = compute_preserved_valid_work(prev_crit, curr_crit, ref_criteria)
        r3_preservations.append(r3)
        
        newly_withdrawn = prev_crit - curr_crit
        withdrawn_criteria_history.update(newly_withdrawn)
        reintroduced = curr_crit.intersection(withdrawn_criteria_history)
        if reintroduced:
            repeated_error_count += len(reintroduced)
            
        total_verifier_calls += step_res["step_verifier_calls"]
        if step_res["accepted"]:
            recovered_count += 1
            
        log_records.append({
            "t": perturbation["t"],
            "perturbation_type": perturbation["type"],
            "delta": delta,
            "accepted": step_res["accepted"],
            "violations": v_rep["violations"]
        })
        prev_state = curr_state

    final_v = verify_interpretation(prev_state, gene_rules)
    q1 = 1.0 if prev_state.get("classification", "").strip().lower() == ground_truth["classification"].strip().lower() else 0.0
    q2 = len(final_v["violations"])
    q3 = 1.0 if q2 == 0 else 0.0
    q4 = compute_brier_score(prev_state.get("belief", {}), ground_truth["classification"])

    return {
        "R1": float(np.mean(deltas)),
        "R2": float(np.mean(r2_ratios)),
        "R3": float(np.mean(r3_preservations)),
        "R4": float(repeated_error_count / (total_perturbations * 3)),
        "R5": float(total_verifier_calls),
        "R6": float(recovered_count / total_perturbations),
        "R7": float(agent.llm_call_count / total_perturbations),
        "Q1": q1,
        "Q2": q2,
        "Q3": q3,
        "Q4": q4,
        "C1": agent.llm_call_count,
        "C2": agent.total_tokens_est,
        "C3": len(cumulative_evidence) * 2,
        "C4": round(agent.total_tokens_est * 0.0000005, 4),
        "C5": 0,
        "logs": log_records
    }

def run_arm_b_instance(instance: Dict[str, Any], seed: int) -> Dict[str, Any]:
    agent = HermeneuticAgent(seed=seed)
    task_spec = instance["initial_spec"]
    gene_rules = instance["gene_rules"]
    ground_truth = instance["ground_truth"]
    ref_criteria = set(ground_truth.get("expected_criteria", []))
    
    cumulative_evidence = []
    prev_state = {
        "classification": "VUS",
        "active_criteria": ["PM2"] if instance["difficulty"] != "easy" else ["PVS1"],
        "assumptions": ["Initial assumption"],
        "constraints": [],
        "hypotheses": ["VUS"],
        "belief": {c: 0.2 for c in ["Pathogenic", "Likely pathogenic", "VUS", "Likely benign", "Benign"]},
        "plan": ["init"]
    }
    
    deltas = []
    r2_ratios = []
    r3_preservations = []
    repeated_error_count = 0
    withdrawn_criteria_history = set()
    total_verifier_calls = 0
    recovered_count = 0
    total_perturbations = len(instance["evidence_schedule"])
    log_records = []

    for perturbation in instance["evidence_schedule"]:
        cumulative_evidence.append(perturbation)
        
        step_res = agent.run_step(prev_state, perturbation, gene_rules)
        curr_state = step_res["state"]
        v_rep = step_res["verifier_report"]
        
        delta = compute_revision_distance(prev_state, curr_state)
        deltas.append(delta)
        
        delta_star = compute_minimal_repair_target(prev_state, ground_truth)
        r2 = delta / delta_star if delta_star > 1e-4 else 1.0
        r2_ratios.append(r2)
        
        prev_crit = set(prev_state.get("active_criteria", []))
        curr_crit = set(curr_state.get("active_criteria", []))
        r3 = compute_preserved_valid_work(prev_crit, curr_crit, ref_criteria)
        r3_preservations.append(r3)
        
        newly_withdrawn = prev_crit - curr_crit
        withdrawn_criteria_history.update(newly_withdrawn)
        reintroduced = curr_crit.intersection(withdrawn_criteria_history)
        if reintroduced:
            repeated_error_count += len(reintroduced)
            
        total_verifier_calls += step_res["step_verifier_calls"]
        if step_res["accepted"]:
            recovered_count += 1
            
        log_records.append({
            "t": perturbation["t"],
            "perturbation_type": perturbation["type"],
            "delta": delta,
            "accepted": step_res["accepted"],
            "violations": v_rep["violations"]
        })
        prev_state = curr_state

    final_v = verify_interpretation(prev_state, gene_rules)
    q1 = 1.0 if prev_state.get("classification", "").strip().lower() == ground_truth["classification"].strip().lower() else 0.0
    q2 = len(final_v["violations"])
    q3 = 1.0 if q2 == 0 else 0.0
    q4 = compute_brier_score(prev_state.get("belief", {}), ground_truth["classification"])

    return {
        "R1": float(np.mean(deltas)),
        "R2": float(np.mean(r2_ratios)),
        "R3": float(np.mean(r3_preservations)),
        "R4": float(repeated_error_count / (total_perturbations * 3)),
        "R5": float(total_verifier_calls),
        "R6": float(recovered_count / total_perturbations),
        "R7": float(agent.llm_call_count / total_perturbations),
        "Q1": q1,
        "Q2": q2,
        "Q3": q3,
        "Q4": q4,
        "C1": agent.llm_call_count,
        "C2": agent.total_tokens_est,
        "C3": len(cumulative_evidence) * 2,
        "C4": round(agent.total_tokens_est * 0.0000005, 4),
        "C5": 0,
        "logs": log_records
    }

def main():
    os.makedirs(RUNS_DIR, exist_ok=True)
    instances = load_instances()
    print(f"Loaded {len(instances)} evaluation instances.")

    # Load existing results if any to avoid recomputing identical completed runs
    existing_runs = {}
    if os.path.exists(RESULTS_CSV):
        with open(RESULTS_CSV, "r", encoding="utf-8") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                key = (row["instance_id"], row["arm"], int(row["seed"]))
                existing_runs[key] = row

    all_rows = []

    for inst in instances:
        inst_id = inst["instance_id"]
        diff = inst["difficulty"]
        print(f"\n==================== Instance: {inst_id} ({diff}) ====================")

        for seed in SEEDS:
            # 1. Arm A (Autoregressive)
            key_a = (inst_id, "Arm_A_Autoregressive", seed)
            run_file_a = os.path.join(RUNS_DIR, f"run_arm_a_{inst_id}_{seed}.json")
            if key_a in existing_runs and os.path.exists(run_file_a):
                print(f"  [CACHED] Arm A (Seed {seed}) already executed.")
                all_rows.append(existing_runs[key_a])
            else:
                print(f"  --> Executing Arm A [Autoregressive] (Seed {seed})...")
                res_a = run_arm_a_instance(inst, seed)
                with open(run_file_a, "w", encoding="utf-8") as fp:
                    json.dump(res_a["logs"], fp, indent=2)
                row_a = {
                    "domain": "biomedical_variant_classification",
                    "instance_id": inst_id,
                    "difficulty": diff,
                    "arm": "Arm_A_Autoregressive",
                    "seed": seed,
                    "R1": round(res_a["R1"], 4),
                    "R2": round(res_a["R2"], 4),
                    "R3": round(res_a["R3"], 4),
                    "R4": round(res_a["R4"], 4),
                    "R5": round(res_a["R5"], 4),
                    "R6": round(res_a["R6"], 4),
                    "R7": round(res_a["R7"], 4),
                    "Q1": round(res_a["Q1"], 4),
                    "Q2": round(res_a["Q2"], 4),
                    "Q3": round(res_a["Q3"], 4),
                    "Q4": round(res_a["Q4"], 4),
                    "C1": res_a["C1"],
                    "C2": res_a["C2"],
                    "C3": res_a["C3"],
                    "C4": res_a["C4"],
                    "C5": res_a["C5"]
                }
                existing_runs[key_a] = row_a
                all_rows.append(row_a)
                print(f"      Arm A Done: delta={res_a['R1']:.4f}, preserved={res_a['R3']:.2f}, Q1={res_a['Q1']}")

            # 2. Arm B' (Hermeneutic Chamber)
            key_b = (inst_id, "Arm_B_Hermeneutic", seed)
            run_file_b = os.path.join(RUNS_DIR, f"run_arm_b_{inst_id}_{seed}.json")
            if key_b in existing_runs and os.path.exists(run_file_b):
                print(f"  [CACHED] Arm B' (Seed {seed}) already executed.")
                all_rows.append(existing_runs[key_b])
            else:
                print(f"  --> Executing Arm B' [Hermeneutic Chamber] (Seed {seed})...")
                res_b = run_arm_b_instance(inst, seed)
                with open(run_file_b, "w", encoding="utf-8") as fp:
                    json.dump(res_b["logs"], fp, indent=2)
                row_b = {
                    "domain": "biomedical_variant_classification",
                    "instance_id": inst_id,
                    "difficulty": diff,
                    "arm": "Arm_B_Hermeneutic",
                    "seed": seed,
                    "R1": round(res_b["R1"], 4),
                    "R2": round(res_b["R2"], 4),
                    "R3": round(res_b["R3"], 4),
                    "R4": round(res_b["R4"], 4),
                    "R5": round(res_b["R5"], 4),
                    "R6": round(res_b["R6"], 4),
                    "R7": round(res_b["R7"], 4),
                    "Q1": round(res_b["Q1"], 4),
                    "Q2": round(res_b["Q2"], 4),
                    "Q3": round(res_b["Q3"], 4),
                    "Q4": round(res_b["Q4"], 4),
                    "C1": res_b["C1"],
                    "C2": res_b["C2"],
                    "C3": res_b["C3"],
                    "C4": res_b["C4"],
                    "C5": res_b["C5"]
                }
                existing_runs[key_b] = row_b
                all_rows.append(row_b)
                print(f"      Arm B' Done: delta={res_b['R1']:.4f}, preserved={res_b['R3']:.2f}, Q1={res_b['Q1']}")

    # Write all rows to results.csv
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=CSV_HEADER)
        writer.writeheader()
        for r in all_rows:
            writer.writerow(r)

    print(f"\n[SUCCESS] Completed all executions. Total records written: {len(all_rows)}")

if __name__ == "__main__":
    main()
