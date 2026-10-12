"""
Fara-7B Agent Implementations for Biomedical Variant Classification.
Supports:
- Arm A: Fara Autoregressive Agent (Replanning from scratch).
- Arm B': Fara Hermeneutic Agent (Minimal repair with interpretive state sigma).
Runs locally on NVIDIA RTX 4070 GPU via llama-cli.exe with -ngl 99.
"""

import os
import sys
import json
import re
import subprocess
from typing import Dict, Any, List

# Locate project paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
LLAMA_BIN = os.path.join(PROJECT_ROOT, "llama_bin", "cuda", "llama-cli.exe")
FARA_MODEL = os.path.join(PROJECT_ROOT, "Autoregressive LLM", "microsoft_Fara-7B-Q4_K_M.gguf")

sys.path.insert(0, CURRENT_DIR)
from verifier.acmg_verifier import verify_interpretation

def parse_json_from_llm(raw_text: str) -> Dict[str, Any]:
    """Robustly extract JSON object from LLM response text using balanced brace parsing."""
    clean_text = raw_text
    if "<tool_call>" in clean_text:
        clean_text = clean_text.split("<tool_call>")[0]
    if "[ Prompt:" in clean_text:
        clean_text = clean_text.split("[ Prompt:")[0]

    # First attempt: standard markdown block
    if "```json" in clean_text:
        try:
            block = clean_text.split("```json")[1].split("```")[0].strip()
            data = json.loads(block)
            if "classification" in data or "active_criteria" in data:
                return data
        except Exception:
            pass

    # Second attempt: balanced braces search
    start = -1
    depth = 0
    for i, char in enumerate(clean_text):
        if char == "{":
            if depth == 0:
                start = i
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start != -1:
                candidate = clean_text[start:i+1]
                try:
                    data = json.loads(candidate)
                    if "classification" in data or "active_criteria" in data:
                        return data
                except Exception:
                    pass
    return {}

def call_fara_cli(prompt_content: str, seed: int = 42, max_tokens: int = 256) -> str:
    """Execute Fara-7B on GPU via llama-cli.exe with ChatML wrapping."""
    chat_prompt = (
        f"<|im_start|>system\n"
        f"You are an expert clinical geneticist specializing in ACMG/AMP 2015 variant classification. "
        f"You must strictly output valid JSON format conforming to the requested schema.\n"
        f"<|im_end|>\n"
        f"<|im_start|>user\n"
        f"{prompt_content}\n"
        f"<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

    cmd = [
        LLAMA_BIN,
        "-m", FARA_MODEL,
        "-p", chat_prompt,
        "-ngl", "99",
        "-c", "2048",
        "-ub", "512",
        "-b", "512",
        "-n", str(max_tokens),
        "--temp", "0.0",
        "--seed", str(seed),
        "--no-warmup",
        "-st",
        "--simple-io"
    ]

    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = res.stdout
    # Cut off everything before assistant prompt echo if present
    if "<|im_start|>assistant" in output:
        output = output.split("<|im_start|>assistant")[-1]
    return output


class FaraAutoregressiveAgent:
    """Arm A: Autoregressive agent with Fara-7B on GPU."""
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.llm_call_count = 0
        self.total_tokens_est = 0
        self.verifier_call_count = 0

    def run_step(self, task_spec: Dict[str, Any], cumulative_evidence: List[Dict[str, Any]], gene_rules: Dict[str, Any], max_verifier_budget: int = 3) -> Dict[str, Any]:
        evidence_text = "\n".join([f"- [Time {e.get('t', 0)}] {e.get('content', '')}" for e in cumulative_evidence])
        
        prompt = f"""You are an expert clinical geneticist classifying a sequence variant under ACMG/AMP 2015 criteria.
Variant: {task_spec.get('target_gene')} - {task_spec.get('task')}

Cumulative Evidence observed so far:
{evidence_text}

Gene rules:
Loss of function mechanism: {gene_rules.get('loss_of_function_mechanism')}
Disallowed criteria: {gene_rules.get('disallowed_criteria', [])}

TASK:
1. Re-analyze all cumulative evidence from scratch.
2. Select the valid ACMG criteria codes:
   Pathogenic: PVS1, PS1, PS2, PS3, PS4, PM1, PM2, PM3, PM4, PM5, PM6, PP1, PP2, PP3, PP4, PP5
   Benign: BA1, BS1, BS2, BS3, BS4, BP1, BP2, BP3, BP4, BP5, BP6, BP7
3. Ensure no mutual exclusion violations (PM2 cannot coexist with BA1/BS1; PS3 cannot coexist with BS3; PVS1 cannot coexist with BP7 or PM4).
4. Assign final classification that accurately reflects the criteria combination: 'Pathogenic', 'Likely pathogenic', 'VUS', 'Likely benign', 'Benign'.
5. Assign probability distribution across all 5 classes summing to 1.0.

Respond strictly in valid JSON format:
{{
  "classification": "<one of the 5 classes>",
  "active_criteria": ["<CRITERION_1>", "<CRITERION_2>"],
  "assumptions": ["<key assumption 1>", "<key assumption 2>"],
  "belief": {{
    "Pathogenic": 0.0,
    "Likely pathogenic": 0.0,
    "VUS": 0.0,
    "Likely benign": 0.0,
    "Benign": 0.0
  }},
  "plan": ["completed"]
}}
"""
        step_verifier_calls = 0
        current_state = {}
        v_report = {"valid": False, "violations": ["Initial"]}

        while step_verifier_calls < max_verifier_budget and not v_report["valid"]:
            self.llm_call_count += 1
            self.total_tokens_est += len(prompt) // 4 + 200
            
            raw_content = call_fara_cli(prompt, seed=self.seed)
            state_data = parse_json_from_llm(raw_content)
            
            if state_data:
                current_state = {
                    "classification": state_data.get("classification", "VUS"),
                    "active_criteria": state_data.get("active_criteria", []),
                    "assumptions": state_data.get("assumptions", []),
                    "constraints": gene_rules.get("disallowed_criteria", []),
                    "hypotheses": [state_data.get("classification", "VUS")],
                    "belief": state_data.get("belief", {c: 0.2 for c in ["Pathogenic", "Likely pathogenic", "VUS", "Likely benign", "Benign"]}),
                    "plan": state_data.get("plan", ["completed"])
                }
            else:
                current_state = {
                    "classification": "VUS",
                    "active_criteria": [],
                    "assumptions": ["Parsing fallback"],
                    "constraints": [],
                    "hypotheses": ["VUS"],
                    "belief": {"Pathogenic": 0.0, "Likely pathogenic": 0.0, "VUS": 1.0, "Likely benign": 0.0, "Benign": 0.0},
                    "plan": ["error"]
                }

            self.verifier_call_count += 1
            step_verifier_calls += 1
            v_report = verify_interpretation(current_state, gene_rules)

            if not v_report["valid"] and step_verifier_calls < max_verifier_budget:
                prompt += f"\n\n[VERIFIER ERROR REPORT]: The plan failed constraint verification with violations: {v_report['violations']}. Repair the plan from scratch to eliminate these violations."

        return {
            "state": current_state,
            "verifier_report": v_report,
            "step_verifier_calls": step_verifier_calls,
            "accepted": v_report["valid"]
        }


class FaraHermeneuticAgent:
    """Arm B': Hermeneutic agent with Fara-7B on GPU."""
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.llm_call_count = 0
        self.total_tokens_est = 0
        self.verifier_call_count = 0
        self.chamber_updates_count = 0

    def run_step(self, current_sigma: Dict[str, Any], new_evidence: Dict[str, Any], gene_rules: Dict[str, Any], max_verifier_budget: int = 3) -> Dict[str, Any]:
        self.chamber_updates_count += 1
        
        prompt = f"""You are the Hermeneutic Interpretation Chamber for an ACMG Variant Classification Agent.
You maintain an explicit interpretive state sigma:
- Active Criteria: {current_sigma.get('active_criteria', [])}
- Current Classification: {current_sigma.get('classification', 'VUS')}
- Prior Assumptions: {current_sigma.get('assumptions', [])}
- Constraints: {current_sigma.get('constraints', [])}
- Prior Belief: {current_sigma.get('belief', {})}

NEW EVIDENCE ARRIVING AT THIS STEP (epsilon_t+1):
Perturbation Type: {new_evidence.get('type')}
Content: {new_evidence.get('content')}

Gene rules:
Loss of function mechanism: {gene_rules.get('loss_of_function_mechanism')}
Disallowed criteria: {gene_rules.get('disallowed_criteria', [])}

HERMENEUTIC CIRCLE TASK:
1. INTERPRET THE PART: What does this new evidence specifically assert?
2. RE-INTERPRET THE WHOLE (MINIMAL REPAIR):
   - Invalidate/withdraw any prior assumptions contradicted by this evidence.
   - Adjust active criteria to incorporate the new finding.
   - PRESERVE prior valid criteria that are unaffected by this perturbation. Do NOT discard sound work.
   - Ensure no mutual exclusions (PM2 vs BA1/BS1; PS3 vs BS3; PVS1 vs BP7/PM4).
3. Assign final classification that accurately reflects the criteria combination: 'Pathogenic', 'Likely pathogenic', 'VUS', 'Likely benign', 'Benign'.
4. Update the belief probability distribution over all 5 classes summing to 1.0.

Respond strictly in valid JSON format:
{{
  "interpretation_summary": "<brief summary of what changed and why>",
  "withdrawn_assumptions": ["<withdrawn assumption 1>"],
  "maintained_assumptions": ["<sound assumption 1>"],
  "active_criteria": ["<CRITERION_1>", "<CRITERION_2>"],
  "classification": "<one of the 5 classes>",
  "belief": {{
    "Pathogenic": 0.0,
    "Likely pathogenic": 0.0,
    "VUS": 0.0,
    "Likely benign": 0.0,
    "Benign": 0.0
  }},
  "hypotheses": ["<leading hypothesis>", "<competing hypothesis>"],
  "plan": ["completed"]
}}
"""
        step_verifier_calls = 0
        new_sigma = {}
        v_report = {"valid": False, "violations": ["Initial"]}

        while step_verifier_calls < max_verifier_budget and not v_report["valid"]:
            self.llm_call_count += 1
            self.total_tokens_est += len(prompt) // 4 + 250
            
            raw_content = call_fara_cli(prompt, seed=self.seed)
            chamber_data = parse_json_from_llm(raw_content)
            
            if chamber_data:
                new_sigma = {
                    "classification": chamber_data.get("classification", current_sigma.get("classification", "VUS")),
                    "active_criteria": chamber_data.get("active_criteria", current_sigma.get("active_criteria", [])),
                    "assumptions": chamber_data.get("maintained_assumptions", []),
                    "constraints": current_sigma.get("constraints", []),
                    "hypotheses": chamber_data.get("hypotheses", [chamber_data.get("classification", "VUS")]),
                    "belief": chamber_data.get("belief", current_sigma.get("belief", {})),
                    "plan": chamber_data.get("plan", ["completed"])
                }
            else:
                new_sigma = current_sigma.copy()

            self.verifier_call_count += 1
            step_verifier_calls += 1
            v_report = verify_interpretation(new_sigma, gene_rules)

            if not v_report["valid"] and step_verifier_calls < max_verifier_budget:
                prompt += f"\n\n[VERIFIER CONSTRAINED FEEDBACK]: Verifier reported specific constraint violations: {v_report['violations']}. Repair ONLY the violating criteria or class mismatch while retaining valid criteria."

        return {
            "state": new_sigma,
            "verifier_report": v_report,
            "step_verifier_calls": step_verifier_calls,
            "accepted": v_report["valid"]
        }
