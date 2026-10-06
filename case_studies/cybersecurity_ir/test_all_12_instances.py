"""
Test both arms across all 12 instances
"""
import glob
import yaml
from agents.tools import IRToolkit
from verifier.verifier import CyberIRVerifier
from agents.standard_agent import StandardAgent
from agents.hermeneutic_agent import HermeneuticAgent

v = CyberIRVerifier()
files = sorted(glob.glob("instances/cyber-*.yaml"))

print(f"{'Instance':<11} | {'Diff':<11} | {'Arm A Valid':<11} | {'Arm B Valid':<11} | {'Arm A Tokens':<12} | {'Arm B Tokens':<12}")
print("-" * 80)

for f in files:
    with open(f, "r", encoding="utf-8") as fh:
        inst = yaml.safe_load(fh)
    inst_id = inst["instance_id"]
    diff = inst.get("difficulty", "unknown")
    tools = IRToolkit(instance_data=inst)

    agent_a = StandardAgent(toolkit=tools, verifier=v)
    res_a = agent_a.run(
        initial_evidence=inst['initial_spec']['prior_evidence'],
        constraints=inst['initial_spec']['constraints'],
        perturbations=inst['evidence_schedule'],
        ground_truth=inst['ground_truth']
    )

    agent_b = HermeneuticAgent(toolkit=tools, verifier=v)
    res_b = agent_b.run(
        initial_evidence=inst['initial_spec']['prior_evidence'],
        constraints=inst['initial_spec']['constraints'],
        perturbations=inst['evidence_schedule'],
        ground_truth=inst['ground_truth']
    )

    valid_a = res_a['final_verifier_report']['valid']
    valid_b = res_b['final_verifier_report']['valid']
    tok_a = res_a['totals']['total_tokens']
    tok_b = res_b['totals']['total_tokens']

    print(f"{inst_id:<11} | {diff:<11} | {str(valid_a):<11} | {str(valid_b):<11} | {tok_a:<12} | {tok_b:<12}")
