"""
Arm A: Autoregressive Agent (Replanning from scratch).
At each perturbation, restarts the reasoning trace from scratch given cumulative evidence.
"""

import os
import sys
import json
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
poc_venv = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "poc", "hermeneutic-poc", ".venv", "Lib", "site-packages"))
if os.path.exists(poc_venv) and poc_venv not in sys.path:
    sys.path.insert(0, poc_venv)

poc_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "poc", "hermeneutic-poc", ".env"))
if os.path.exists(poc_env):
    try:
        import dotenv
        dotenv.load_dotenv(poc_env)
    except Exception:
        pass

from langchain_google_genai import ChatGoogleGenerativeAI
from verifier.acmg_verifier import verify_interpretation

class AutoregressiveAgent:
    def __init__(self, model_name: str = "gemini-3.5-flash-lite", temperature: float = 0.0, seed: int = 42):
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature
        )
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
            self.total_tokens_est += len(prompt) // 4 + 250
            
            try:
                response = self.llm.invoke(prompt)
                raw_content = response.content
                if isinstance(raw_content, list):
                    raw_content = "".join([part.get("text", "") if isinstance(part, dict) else str(part) for part in raw_content])
                
                if "```json" in raw_content:
                    raw_content = raw_content.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_content:
                    raw_content = raw_content.split("```")[1].split("```")[0].strip()
                
                state_data = json.loads(raw_content)
                current_state = {
                    "classification": state_data.get("classification", "VUS"),
                    "active_criteria": state_data.get("active_criteria", []),
                    "assumptions": state_data.get("assumptions", []),
                    "constraints": gene_rules.get("disallowed_criteria", []),
                    "hypotheses": [state_data.get("classification", "VUS")],
                    "belief": state_data.get("belief", {c: 0.2 for c in ["Pathogenic", "Likely pathogenic", "VUS", "Likely benign", "Benign"]}),
                    "plan": state_data.get("plan", ["completed"])
                }
            except Exception as e:
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
