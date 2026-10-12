"""
Experiment Runner for Biomedical Variant Classification Case Study using Fara-7B on GPU.
Executes Arm A (Autoregressive Replanning) and Arm B' (Hermeneutic Chamber)
across 10 evaluation instances (biomed-001 to biomed-010) and 3 seeds per instance.
Outputs:
- runs/*.json
- results.csv (standard schema per CSS v1.0 §6.3)
- results_fara.csv
"""

import os
import sys
import json
import csv
import time
import numpy as np
from typing import Dict, Any, List

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CURRENT_DIR)

from agent_fara import FaraAutoregressiveAgent, FaraHermeneuticAgent
from metrics import (
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
RESULTS_FARA_CSV = os.path.join(CURRENT_DIR, "results_fara.csv")

os.makedirs(RUNS_DIR, exist_ok=True)

CSV_HEADER = [
    "domain", "instance_id", "difficulty", "arm", "seed",
    "R1", "R2", "R3", "R4", "R5", "R6", "R7",
    "Q1", "Q2", "Q3", "Q4",
    "C1", "C2", "C3", "C4", "C5"
]

def load_target_instances() -> List[Dict[str, Any]]:
    """Load target evaluation instances biomed-001 to biomed-010."""
    instances = []
    # Standard 10 instances for comparative study
    for i in range(1, 11):
        filename = f"biomed-{i:03d}.json"
        filepath = os.path.join(INSTANCES_DIR, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as fp:
                instances.append(json.load(fp))
    return instances

def run_arm_a_instance(instance: Dict[str, Any], seed: int) -> Dict[str, Any]:
    agent = FaraAutoregressiveAgent(seed=seed)
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
    agent = FaraHermeneuticAgent(seed=seed)
    task_spec = instance["initial_spec"]
    gene_rules = instance["gene_rules"]
    ground_truth = instance["ground_truth"]
    ref_criteria = set(ground_truth.get("expected_criteria", []))
    
    current_sigma = {
        "classification": "VUS",
        "active_criteria": ["PM2"] if instance["difficulty"] != "easy" else ["PVS1"],
        "assumptions": instance["initial_spec"].get("initial_assumptions", []),
        "constraints": instance["initial_spec"].get("constraints", []),
        "hypotheses": ["VUS", "Pathogenic"],
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
        prev_sigma = current_sigma.copy()
        
        step_res = agent.run_step(current_sigma, perturbation, gene_rules)
        current_sigma = step_res["state"]
        v_rep = step_res["verifier_report"]
        
        delta = compute_revision_distance(prev_sigma, current_sigma)
        deltas.append(delta)
        
        delta_star = compute_minimal_repair_target(prev_sigma, ground_truth)
        r2 = delta / delta_star if delta_star > 1e-4 else 1.0
        r2_ratios.append(r2)
        
        prev_crit = set(prev_sigma.get("active_criteria", []))
        curr_crit = set(current_sigma.get("active_criteria", []))
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

    final_v = verify_interpretation(current_sigma, gene_rules)
    q1 = 1.0 if current_sigma.get("classification", "").strip().lower() == ground_truth["classification"].strip().lower() else 0.0
    q2 = len(final_v["violations"])
    q3 = 1.0 if q2 == 0 else 0.0
    q4 = compute_brier_score(current_sigma.get("belief", {}), ground_truth["classification"])

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
        "C3": total_perturbations * 2,
        "C4": round(agent.total_tokens_est * 0.0000005, 4),
        "C5": agent.chamber_updates_count,
        "logs": log_records
    }

def main():
    instances = load_target_instances()
    print(f"Loaded {len(instances)} target evaluation instances for Fara-7B GPU benchmark.", flush=True)
    
    rows = []
    
    # Open CSV files for writing
    for out_path in [RESULTS_CSV, RESULTS_FARA_CSV]:
        with open(out_path, "w", newline="", encoding="utf-8") as csv_fp:
            writer = csv.DictWriter(csv_fp, fieldnames=CSV_HEADER)
            writer.writeheader()
    
    start_time = time.time()
    total_runs = len(instances) * len(SEEDS) * 2
    run_idx = 0

    for inst in instances:
        inst_id = inst["instance_id"]
        diff = inst["difficulty"]
        print(f"\n=======================================================", flush=True)
        print(f"Executing Instance: {inst_id} ({diff}) on RTX 4070 GPU", flush=True)
        print(f"=======================================================", flush=True)
        
        for seed in SEEDS:
            # 1. Run Arm A
            run_idx += 1
            t0 = time.time()
            print(f"[{run_idx}/{total_runs}] Arm A [Autoregressive] ({inst_id}, Seed {seed})...", end="", flush=True)
            res_a = run_arm_a_instance(inst, seed)
            dur_a = time.time() - t0
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
                "R5": int(res_a["R5"]),
                "R6": round(res_a["R6"], 4),
                "R7": round(res_a["R7"], 2),
                "Q1": round(res_a["Q1"], 2),
                "Q2": int(res_a["Q2"]),
                "Q3": round(res_a["Q3"], 2),
                "Q4": round(res_a["Q4"], 4),
                "C1": int(res_a["C1"]),
                "C2": int(res_a["C2"]),
                "C3": int(res_a["C3"]),
                "C4": round(res_a["C4"], 4),
                "C5": int(res_a["C5"])
            }
            rows.append(row_a)
            for out_path in [RESULTS_CSV, RESULTS_FARA_CSV]:
                with open(out_path, "a", newline="", encoding="utf-8") as csv_fp:
                    writer = csv.DictWriter(csv_fp, fieldnames=CSV_HEADER)
                    writer.writerow(row_a)
            print(f" Done ({dur_a:.1f}s): R1={row_a['R1']}, R2={row_a['R2']}, R3={row_a['R3']}, Q1={row_a['Q1']}", flush=True)

            with open(os.path.join(RUNS_DIR, f"run_fara_arm_a_{inst_id}_{seed}.json"), "w", encoding="utf-8") as lfp:
                json.dump(res_a["logs"], lfp, indent=2)

            # 2. Run Arm B'
            run_idx += 1
            t0 = time.time()
            print(f"[{run_idx}/{total_runs}] Arm B' [Hermeneutic] ({inst_id}, Seed {seed})...", end="", flush=True)
            res_b = run_arm_b_instance(inst, seed)
            dur_b = time.time() - t0
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
                "R5": int(res_b["R5"]),
                "R6": round(res_b["R6"], 4),
                "R7": round(res_b["R7"], 2),
                "Q1": round(res_b["Q1"], 2),
                "Q2": int(res_b["Q2"]),
                "Q3": round(res_b["Q3"], 2),
                "Q4": round(res_b["Q4"], 4),
                "C1": int(res_b["C1"]),
                "C2": int(res_b["C2"]),
                "C3": int(res_b["C3"]),
                "C4": round(res_b["C4"], 4),
                "C5": int(res_b["C5"])
            }
            rows.append(row_b)
            for out_path in [RESULTS_CSV, RESULTS_FARA_CSV]:
                with open(out_path, "a", newline="", encoding="utf-8") as csv_fp:
                    writer = csv.DictWriter(csv_fp, fieldnames=CSV_HEADER)
                    writer.writerow(row_b)
            print(f" Done ({dur_b:.1f}s): R1={row_b['R1']}, R2={row_b['R2']}, R3={row_b['R3']}, Q1={row_b['Q1']}", flush=True)

            with open(os.path.join(RUNS_DIR, f"run_fara_arm_b_{inst_id}_{seed}.json"), "w", encoding="utf-8") as lfp:
                json.dump(res_b["logs"], lfp, indent=2)

    total_dur = time.time() - start_time
    print(f"\n[SUCCESS] Completed all {run_idx} runs in {total_dur:.1f}s ({total_dur/60:.2f} mins).", flush=True)
    print(f"Results saved to: {RESULTS_CSV} and {RESULTS_FARA_CSV}", flush=True)

if __name__ == "__main__":
    main()
