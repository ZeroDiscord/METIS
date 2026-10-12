"""
Diffusion LLM Experiment Runner for Biomedical Variant Classification Case Study.
Evaluates Arm A (Autoregressive Replan on Diffusion LLM) and Arm B (Hermeneutic Chamber on Diffusion LLM)
on the two additional evaluation instances: biomed-011 and biomed-012 across seeds [42, 123, 999].

Outputs:
- runs/run_Arm_A_Diffusion_{instance_id}_seed{seed}.json
- runs/run_Arm_B_Diffusion_{instance_id}_seed{seed}.json
- Appends rows to results.csv
"""

import os
import sys
import json
import csv
import time
import re
import subprocess
import numpy as np
from typing import Dict, Any, List, Set

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCES_DIR = os.path.join(BASE_DIR, "instances")
RUNS_DIR = os.path.join(BASE_DIR, "runs")
RESULTS_CSV = os.path.join(BASE_DIR, "results.csv")

sys.path.insert(0, BASE_DIR)
from metrics import (
    compute_revision_distance,
    compute_minimal_repair_target,
    compute_preserved_valid_work,
    compute_brier_score
)
from verifier.acmg_verifier import verify_interpretation

BIN_PATH = r"c:\Users\navee\Documents\Major Project\llama_src\build_cuda\bin\llama-diffusion-cli.exe"
MODEL_PATH = r"c:\Users\navee\Documents\Major Project\LLaDA-MoE-7B-A1B-Instruct-i1-GGUF\LLaDA-MoE-7B-A1B-Instruct.i1-Q4_K_M.gguf"
ENV = os.environ.copy()
CUDA_BIN = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin"
LOCAL_BIN = r"c:\Users\navee\Documents\Major Project\llama_src\build_cuda\bin"
ENV["PATH"] = f"{LOCAL_BIN};{CUDA_BIN};" + ENV.get("PATH", "")

SEEDS = [42, 123, 999]
TARGET_INSTANCES = ["biomed-011", "biomed-012"]
CLASSES = ["Pathogenic", "Likely pathogenic", "VUS", "Likely benign", "Benign"]

def invoke_diffusion(prompt: str, seed: int = 42, steps: int = 64, block_length: int = 32) -> str:
    cmd = [
        BIN_PATH,
        "-m", MODEL_PATH,
        "-p", prompt,
        "-ngl", "99",
        "-c", "1024",
        "-ub", "512",
        "-b", "512",
        "--diffusion-block-length", str(block_length),
        "--diffusion-steps", str(steps),
        "--temp", "0.0",
        "--seed", str(seed),
        "-t", "8"
    ]
    p = subprocess.run(cmd, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    out = p.stdout
    if "total time:" in out:
        out = out.split("total time:")[1]
    out = re.sub(r'^\s*\d+\.\d+\.\d+\.\d+\s+[IWE]\s*', '', out, flags=re.MULTILINE)
    return out.strip()

def extract_json(raw: str, default_class: str = "VUS") -> Dict[str, Any]:
    # Extract json block or substring
    cleaned = raw.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json")[1].split("```")[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```")[1].split("```")[0].strip()
    
    # Try direct parse
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            cls_val = obj.get("classification", default_class)
            crit_val = obj.get("active_criteria", [])
            belief = {c: (0.85 if c.lower() == str(cls_val).lower() else 0.0375) for c in CLASSES}
            return {
                "classification": cls_val,
                "active_criteria": crit_val,
                "assumptions": obj.get("assumptions", ["Diffusion extracted state"]),
                "belief": belief,
                "plan": ["completed"]
            }
    except Exception:
        pass
        
    m = re.search(r'(\{[\s\S]*\})', cleaned)
    if m:
        try:
            obj = json.loads(m.group(1))
            if isinstance(obj, dict):
                cls_val = obj.get("classification", default_class)
                crit_val = obj.get("active_criteria", [])
                belief = {c: (0.85 if c.lower() == str(cls_val).lower() else 0.0375) for c in CLASSES}
                return {
                    "classification": cls_val,
                    "active_criteria": crit_val,
                    "assumptions": obj.get("assumptions", ["Diffusion extracted state"]),
                    "belief": belief,
                    "plan": ["completed"]
                }
        except Exception:
            pass
            
    # Regex fallback
    classification = default_class
    m_cls = re.search(r'"classification"\s*:\s*"([^"]+)"', raw, re.IGNORECASE)
    if m_cls:
        val = m_cls.group(1).strip()
        for c in CLASSES:
            if c.lower() in val.lower():
                classification = c
                break
                
    criteria = []
    m_crit = re.search(r'"active_criteria"\s*:\s*\[([\s\S]*?)\]', raw)
    if m_crit:
        criteria = re.findall(r'"([A-Z0-9_]+)"', m_crit.group(1))
        
    belief = {c: (0.85 if c == classification else 0.0375) for c in CLASSES}
    return {
        "classification": classification,
        "active_criteria": criteria,
        "assumptions": ["Diffusion extracted state"],
        "belief": belief,
        "plan": ["completed"]
    }

class ArmADiffusionAgent:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.llm_call_count = 0
        self.total_tokens_est = 0
        self.verifier_call_count = 0

    def run_step(self, task_spec: Dict[str, Any], cumulative_evidence: List[Dict[str, Any]], gene_rules: Dict[str, Any], max_verifier_budget: int = 3) -> Dict[str, Any]:
        evidence_text = "\n".join([f"- [Time {e.get('t', 0)}] {e.get('content', '')}" for e in cumulative_evidence])
        
        prompt = f"""<|im_start|>system
You are an expert clinical geneticist classifying sequence variants under ACMG/AMP 2015 criteria. Always respond strictly in valid JSON format only.<|im_end|>
<|im_start|>user
Variant: {task_spec.get('target_gene')} - {task_spec.get('task')}

Cumulative Evidence observed:
{evidence_text}

Gene rules: LoF={gene_rules.get('loss_of_function_mechanism')}, Disallowed={gene_rules.get('disallowed_criteria', [])}

TASK:
1. Re-analyze all cumulative evidence from scratch.
2. Select all valid active ACMG criteria codes from:
   Pathogenic: PS1, PS2, PS3, PS4, PM1, PM2, PM3, PM4, PM5, PM6, PP1, PP2, PP3, PP4, PP5
   Benign: BA1, BS1, BS2, BS3, BS4, BP1, BP2, BP3, BP4, BP5, BP6, BP7
3. Assign final classification: 'Pathogenic', 'Likely pathogenic', 'VUS', 'Likely benign', 'Benign'.

Output JSON format strictly:
{{"classification": "Pathogenic", "active_criteria": ["PS3", "PS4", "PM1", "PM2"]}}
<|im_end|>
<|im_start|>assistant
"""
        step_verifier_calls = 0
        current_state = {}
        v_report = {"valid": False, "violations": ["Initial"]}

        while step_verifier_calls < max_verifier_budget and not v_report["valid"]:
            self.llm_call_count += 1
            self.total_tokens_est += len(prompt) // 4 + 64
            
            raw = invoke_diffusion(prompt, seed=self.seed + step_verifier_calls, steps=64, block_length=32)
            parsed = extract_json(raw, default_class="VUS")
            
            cls_val = parsed.get("classification", "VUS")
            current_state = {
                "classification": cls_val,
                "active_criteria": parsed.get("active_criteria", []),
                "assumptions": parsed.get("assumptions", ["Autoregressive replan assumption"]),
                "constraints": gene_rules.get("disallowed_criteria", []),
                "hypotheses": [cls_val],
                "belief": parsed.get("belief", {c: (0.8 if c == cls_val else 0.05) for c in CLASSES}),
                "plan": parsed.get("plan", ["completed"])
            }
            
            step_verifier_calls += 1
            self.verifier_call_count += 1
            v_report = verify_interpretation(current_state, gene_rules)
            
            if not v_report["valid"]:
                prompt += f"\nNote: verifier flagged {v_report['violations']}. Adjust criteria.\n<|im_end|>\n<|im_start|>assistant\n"

        return {
            "state": current_state,
            "verifier_report": v_report,
            "verifier_calls": step_verifier_calls
        }

class ArmBDiffusionAgent:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.llm_call_count = 0
        self.total_tokens_est = 0
        self.verifier_call_count = 0
        self.chamber_updates_count = 0

    def run_step(self, current_sigma: Dict[str, Any], new_evidence: Dict[str, Any], gene_rules: Dict[str, Any], max_verifier_budget: int = 3) -> Dict[str, Any]:
        self.chamber_updates_count += 1
        
        prompt = f"""<|im_start|>system
You are the Hermeneutic Interpretation Chamber for an ACMG Variant Classification Agent. Always respond strictly in valid JSON format only.<|im_end|>
<|im_start|>user
Current State:
- Active Criteria: {current_sigma.get('active_criteria', [])}
- Current Classification: {current_sigma.get('classification', 'VUS')}

New Evidence ({new_evidence.get('type')}):
{new_evidence.get('content')}

HERMENEUTIC MINIMAL REPAIR:
1. Retain valid unaffected criteria.
2. Invalidate contradicted criteria and incorporate new evidence criteria.
3. Assign final classification: 'Pathogenic', 'Likely pathogenic', 'VUS', 'Likely benign', 'Benign'.

Output JSON format strictly:
{{"classification": "Pathogenic", "active_criteria": ["PS3", "PS4", "PM1", "PM2"]}}
<|im_end|>
<|im_start|>assistant
"""
        step_verifier_calls = 0
        new_sigma = {}
        v_report = {"valid": False, "violations": ["Initial"]}

        while step_verifier_calls < max_verifier_budget and not v_report["valid"]:
            self.llm_call_count += 1
            self.total_tokens_est += len(prompt) // 4 + 64
            
            raw = invoke_diffusion(prompt, seed=self.seed + step_verifier_calls, steps=64, block_length=32)
            parsed = extract_json(raw, default_class=current_sigma.get("classification", "VUS"))
            
            cls_val = parsed.get("classification", current_sigma.get("classification", "VUS"))
            new_sigma = {
                "classification": cls_val,
                "active_criteria": parsed.get("active_criteria", current_sigma.get("active_criteria", [])),
                "assumptions": parsed.get("assumptions", current_sigma.get("assumptions", [])),
                "constraints": gene_rules.get("disallowed_criteria", []),
                "hypotheses": [cls_val],
                "belief": parsed.get("belief", current_sigma.get("belief", {c: 0.2 for c in CLASSES})),
                "plan": ["completed"],
                "withdrawn_assumptions": parsed.get("withdrawn_assumptions", [])
            }
            
            step_verifier_calls += 1
            self.verifier_call_count += 1
            v_report = verify_interpretation(new_sigma, gene_rules)
            
            if not v_report["valid"]:
                prompt += f"\nNote: verifier flagged {v_report['violations']}. Adjust criteria.\n<|im_end|>\n<|im_start|>assistant\n"

        return {
            "state": new_sigma,
            "verifier_report": v_report,
            "verifier_calls": step_verifier_calls
        }

        return {
            "state": new_sigma,
            "verifier_report": v_report,
            "verifier_calls": step_verifier_calls
        }

def execute_arm_a(instance: Dict[str, Any], seed: int) -> Dict[str, Any]:
    agent = ArmADiffusionAgent(seed=seed)
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
        "belief": {c: 0.2 for c in CLASSES},
        "plan": ["init"]
    }
    
    deltas = []
    r2_ratios = []
    r3_preservations = []
    withdrawn_criteria_history = set()
    repeated_error_count = 0
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
            
        total_verifier_calls += step_res["verifier_calls"]
        if v_rep["valid"]:
            recovered_count += 1
            
        log_records.append({
            "t": perturbation["t"],
            "perturbation": perturbation,
            "state_before": prev_state,
            "state_after": curr_state,
            "verifier_report": v_rep,
            "delta": delta,
            "r2": r2,
            "r3": r3
        })
        prev_state = curr_state

    final_state = prev_state
    q1 = 1.0 if final_state.get("classification", "").lower() == ground_truth.get("classification", "").lower() else 0.0
    final_v = verify_interpretation(final_state, gene_rules)
    q2 = len(final_v.get("violations", []))
    q3 = 1.0 if (q2 == 0 and final_state.get("classification") == final_v.get("classification")) else 0.0
    q4 = compute_brier_score(final_state.get("belief", {}), ground_truth.get("classification", ""))

    r1 = float(np.mean(deltas)) if deltas else 0.0
    r2_mean = float(np.mean(r2_ratios)) if r2_ratios else 0.0
    r3_mean = float(np.mean(r3_preservations)) if r3_preservations else 0.0
    r4 = float(repeated_error_count / (total_perturbations * 2))
    r5 = total_verifier_calls
    r6 = float(recovered_count / total_perturbations)
    r7 = float(total_verifier_calls / total_perturbations)

    return {
        "domain": "biomedical_variant_classification",
        "instance_id": instance["instance_id"],
        "difficulty": instance["difficulty"],
        "arm": "Arm_A_Diffusion",
        "seed": seed,
        "R1": round(r1, 4),
        "R2": round(r2_mean, 4),
        "R3": round(r3_mean, 4),
        "R4": round(r4, 4),
        "R5": r5,
        "R6": round(r6, 4),
        "R7": round(r7, 4),
        "Q1": q1,
        "Q2": q2,
        "Q3": q3,
        "Q4": round(q4, 4),
        "C1": total_verifier_calls,
        "C2": agent.total_tokens_est,
        "C3": 8,
        "C4": round(agent.total_tokens_est * 0.0000005, 4),
        "C5": 0,
        "log_records": log_records
    }

def execute_arm_b(instance: Dict[str, Any], seed: int) -> Dict[str, Any]:
    agent = ArmBDiffusionAgent(seed=seed)
    gene_rules = instance["gene_rules"]
    ground_truth = instance["ground_truth"]
    ref_criteria = set(ground_truth.get("expected_criteria", []))
    
    current_sigma = {
        "classification": "VUS",
        "active_criteria": ["PM2"] if instance["difficulty"] != "easy" else ["PVS1"],
        "assumptions": ["Initial provisional assumption"],
        "constraints": gene_rules.get("disallowed_criteria", []),
        "hypotheses": ["VUS"],
        "belief": {c: 0.2 for c in CLASSES},
        "plan": ["init"]
    }
    
    deltas = []
    r2_ratios = []
    r3_preservations = []
    withdrawn_criteria_history = set()
    repeated_error_count = 0
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
            
        total_verifier_calls += step_res["verifier_calls"]
        if v_rep["valid"]:
            recovered_count += 1
            
        log_records.append({
            "t": perturbation["t"],
            "perturbation": perturbation,
            "sigma_before": prev_sigma,
            "sigma_after": current_sigma,
            "verifier_report": v_rep,
            "delta": delta,
            "r2": r2,
            "r3": r3
        })

    final_state = current_sigma
    q1 = 1.0 if final_state.get("classification", "").lower() == ground_truth.get("classification", "").lower() else 0.0
    final_v = verify_interpretation(final_state, gene_rules)
    q2 = len(final_v.get("violations", []))
    q3 = 1.0 if (q2 == 0 and final_state.get("classification") == final_v.get("classification")) else 0.0
    q4 = compute_brier_score(final_state.get("belief", {}), ground_truth.get("classification", ""))

    r1 = float(np.mean(deltas)) if deltas else 0.0
    r2_mean = float(np.mean(r2_ratios)) if r2_ratios else 0.0
    r3_mean = float(np.mean(r3_preservations)) if r3_preservations else 0.0
    r4 = float(repeated_error_count / (total_perturbations * 2))
    r5 = total_verifier_calls
    r6 = float(recovered_count / total_perturbations)
    r7 = float(total_verifier_calls / total_perturbations)

    return {
        "domain": "biomedical_variant_classification",
        "instance_id": instance["instance_id"],
        "difficulty": instance["difficulty"],
        "arm": "Arm_B_Diffusion",
        "seed": seed,
        "R1": round(r1, 4),
        "R2": round(r2_mean, 4),
        "R3": round(r3_mean, 4),
        "R4": round(r4, 4),
        "R5": r5,
        "R6": round(r6, 4),
        "R7": round(r7, 4),
        "Q1": q1,
        "Q2": q2,
        "Q3": q3,
        "Q4": round(q4, 4),
        "C1": total_verifier_calls,
        "C2": agent.total_tokens_est,
        "C3": 8,
        "C4": round(agent.total_tokens_est * 0.0000005, 4),
        "C5": agent.chamber_updates_count,
        "log_records": log_records
    }

def main():
    print("=" * 70)
    print("STARTING DIFFUSION LLM CASE STUDY EXPERIMENT (LLaDA-MoE-7B-A1B-Instruct)")
    print(f"Target Cases: {TARGET_INSTANCES}")
    print(f"Seeds: {SEEDS}")
    print("=" * 70)
    sys.stdout.flush()

    instances = {}
    for inst_id in TARGET_INSTANCES:
        path = os.path.join(INSTANCES_DIR, f"{inst_id}.json")
        with open(path, "r", encoding="utf-8") as f:
            instances[inst_id] = json.load(f)

    results_to_append = []
    total_runs = len(TARGET_INSTANCES) * len(SEEDS) * 2
    completed_runs = 0

    start_all = time.time()

    for inst_id in TARGET_INSTANCES:
        inst_data = instances[inst_id]
        
        # 1. Run Arm A on Diffusion LLM
        for s in SEEDS:
            t0 = time.time()
            print(f"[{time.strftime('%H:%M:%S')}] RUNNING Arm_A_Diffusion | Instance: {inst_id} | Seed: {s} ...")
            sys.stdout.flush()
            
            res_a = execute_arm_a(inst_data, s)
            elapsed = time.time() - t0
            completed_runs += 1
            
            # Save run JSON
            run_file = os.path.join(RUNS_DIR, f"run_Arm_A_Diffusion_{inst_id}_seed{s}.json")
            with open(run_file, "w", encoding="utf-8") as fp:
                json.dump(res_a, fp, indent=2)
                
            row_data = {k: v for k, v in res_a.items() if k != "log_records"}
            results_to_append.append(row_data)
            
            print(f"[{time.strftime('%H:%M:%S')}] COMPLETED Arm_A_Diffusion | {inst_id} (Seed {s}) in {elapsed:.1f}s | R1={res_a['R1']} | Q1={res_a['Q1']} | Progress: {completed_runs}/{total_runs}")
            sys.stdout.flush()

        # 2. Run Arm B on Diffusion LLM
        for s in SEEDS:
            t0 = time.time()
            print(f"[{time.strftime('%H:%M:%S')}] RUNNING Arm_B_Diffusion | Instance: {inst_id} | Seed: {s} ...")
            sys.stdout.flush()
            
            res_b = execute_arm_b(inst_data, s)
            elapsed = time.time() - t0
            completed_runs += 1
            
            # Save run JSON
            run_file = os.path.join(RUNS_DIR, f"run_Arm_B_Diffusion_{inst_id}_seed{s}.json")
            with open(run_file, "w", encoding="utf-8") as fp:
                json.dump(res_b, fp, indent=2)
                
            row_data = {k: v for k, v in res_b.items() if k != "log_records"}
            results_to_append.append(row_data)
            
            print(f"[{time.strftime('%H:%M:%S')}] COMPLETED Arm_B_Diffusion | {inst_id} (Seed {s}) in {elapsed:.1f}s | R1={res_b['R1']} | Q1={res_b['Q1']} | Progress: {completed_runs}/{total_runs}")
            sys.stdout.flush()

    # Append to results.csv
    print(f"\nAppending {len(results_to_append)} rows to {RESULTS_CSV}...")
    csv_header = [
        "domain", "instance_id", "difficulty", "arm", "seed",
        "R1", "R2", "R3", "R4", "R5", "R6", "R7",
        "Q1", "Q2", "Q3", "Q4",
        "C1", "C2", "C3", "C4", "C5"
    ]
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=csv_header)
        for r in results_to_append:
            writer.writerow(r)

    total_time_min = (time.time() - start_all) / 60
    print(f"ALL 12 DIFFUSION RUNS COMPLETED in {total_time_min:.1f} minutes!")
    sys.stdout.flush()

if __name__ == "__main__":
    main()
