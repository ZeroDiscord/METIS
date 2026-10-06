"""
Arm B': Hermeneutic Agent with Explicit Interpretive State.
Maintains sigma_t = <gamma, beta, alpha, kappa, H, pi>.
At each perturbation, the Hermeneutic Chamber interprets the new evidence,
updates assumptions, revises hypotheses, and performs minimal repair on the state.
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

class HermeneuticAgent:
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
            self.total_tokens_est += len(prompt) // 4 + 300
            
            try:
                response = self.llm.invoke(prompt)
                raw_content = response.content
                if isinstance(raw_content, list):
                    raw_content = "".join([part.get("text", "") if isinstance(part, dict) else str(part) for part in raw_content])

                if "```json" in raw_content:
                    raw_content = raw_content.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_content:
                    raw_content = raw_content.split("```")[1].split("```")[0].strip()
                
                chamber_data = json.loads(raw_content)
                new_sigma = {
                    "classification": chamber_data.get("classification", current_sigma.get("classification", "VUS")),
                    "active_criteria": chamber_data.get("active_criteria", current_sigma.get("active_criteria", [])),
                    "assumptions": chamber_data.get("maintained_assumptions", []),
                    "constraints": current_sigma.get("constraints", []),
                    "hypotheses": chamber_data.get("hypotheses", [chamber_data.get("classification", "VUS")]),
                    "belief": chamber_data.get("belief", current_sigma.get("belief", {})),
                    "plan": chamber_data.get("plan", ["completed"])
                }
            except Exception as e:
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
