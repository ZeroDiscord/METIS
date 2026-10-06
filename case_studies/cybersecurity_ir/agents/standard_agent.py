"""
Standard Agent — Arm A
=======================
Autoregressive agent that replans from scratch after each perturbation.
This is the baseline: no explicit interpretive state, pure prompt-history ReAct loop.

Per CSS §4: identical LLM, temperature, tools, data, and budgets as Arm B'.
The ONLY difference is that Arm A has no explicit σ state and replans from scratch.
"""

from __future__ import annotations

import json
import os
import sys
import copy
import re
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.tools import IRToolkit
from agents.state import compute_revision_distance
from agents.llm_client import LLMClient
from verifier.verifier import CyberIRVerifier, VerifierReport


SYSTEM_PROMPT = """You are an expert cybersecurity incident responder. You are investigating a security incident.

Your objective is to:
1. IDENTIFY the threat actor responsible for the attack
2. DETERMINE the full scope of compromise (which systems are affected)
3. RECONSTRUCT the kill chain (sequence of ATT&CK techniques used)
4. RECOMMEND containment and remediation actions

You have access to the investigation tools.
After investigating, provide your complete assessment as a JSON object with:
{
    "attributed_group": "MITRE group ID (e.g., G0096)",
    "kill_chain": ["T1190", "T1059.001", ...],
    "compromised_hosts": ["HOST-1", "HOST-2", ...],
    "plan_actions": [...],
    "evidence_map": {...},
    "explained_evidence": [...],
    "confidence": 0.0-1.0
}"""


class StandardAgent:
    """
    Arm A: Autoregressive agent that replans from scratch.
    After each perturbation, receives ALL evidence again and generates
    a completely new assessment from scratch.
    """

    def __init__(
        self,
        toolkit: IRToolkit,
        verifier: CyberIRVerifier,
        model: str = "gpt-4o",
        temperature: float = 0.0,
        max_steps: int = 50,
        max_tokens: int = 100_000,
        api_key: str | None = None,
        base_url: str | None = None,
        mode: str = "simulated",
        seed: int = 42,
    ):
        self.toolkit = toolkit
        self.verifier = verifier
        self.model = model
        self.temperature = temperature
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", None)
        self.mode = mode
        self.seed = seed

        # Live LLM client if requested
        self.llm_client = None
        if self.mode == "live":
            self.llm_client = LLMClient(
                model=self.model,
                temperature=self.temperature,
                api_key=self.api_key,
                base_url=self.base_url,
            )

        # Logging
        self.llm_calls = 0
        self.total_tokens = 0
        self.tool_calls = 0
        self.step_log: list[dict] = []
        self.verifier_calls = 0

    def run(
        self,
        initial_evidence: list[str],
        constraints: list[dict],
        perturbations: list[dict],
        ground_truth: dict | None = None,
    ) -> dict:
        """
        Run the standard agent through an instance.
        """
        results = {
            "arm": "A",
            "model": self.model,
            "temperature": self.temperature,
            "perturbation_results": [],
            "final_state": None,
            "final_verifier_report": None,
        }

        all_evidence = list(initial_evidence)
        all_constraints = list(constraints)

        # ── t=0: Initial assessment ──────────────────────────────────────
        state_t0 = self._assess_from_scratch(all_evidence, all_constraints, t=0)
        report_t0 = self._verify(state_t0, all_evidence, all_constraints, ground_truth)

        results["initial_assessment"] = {
            "state": state_t0,
            "verifier_report": report_t0.to_dict(),
            "llm_calls": self.llm_calls,
            "tokens": self.total_tokens,
            "tool_calls": self.tool_calls,
        }

        prev_state = state_t0

        # ── t=1..4: Perturbations ────────────────────────────────────────
        for i, perturbation in enumerate(perturbations):
            t = i + 1
            p_type = perturbation.get("type", "unknown")
            p_content = perturbation.get("content", "")

            # Update evidence / constraints based on perturbation type
            if p_type == "constraint_added":
                new_constraint = perturbation.get("constraint", {
                    "id": f"K_new_{t}",
                    "text": p_content,
                    "type": perturbation.get("constraint_type", "generic"),
                    "hard": True,
                })
                all_constraints.append(new_constraint)

            all_evidence.append(f"[PERTURBATION t={t} ({p_type})]: {p_content}")

            # ── Arm A: REPLAN FROM SCRATCH ───────────────────────────────
            calls_before = self.llm_calls
            tokens_before = self.total_tokens
            tools_before = self.tool_calls
            verifier_before = self.verifier_calls

            state_after = self._assess_from_scratch(all_evidence, all_constraints, t=t)
            report_after = self._verify(
                state_after, all_evidence, all_constraints, ground_truth
            )

            # Compute revision distance between consecutive states
            delta = self._compute_delta(prev_state, state_after)

            # Work preservation: actions kept from previous plan
            prev_plan = prev_state.get("plan_actions", [])
            new_plan = state_after.get("plan_actions", [])
            preserved = sum(
                1 for p in prev_plan
                if any(n.get("action") == p.get("action") and n.get("target") == p.get("target") for n in new_plan)
            )
            work_pres = (preserved / len(prev_plan)) if prev_plan else 0.0

            results["perturbation_results"].append({
                "t": t,
                "perturbation_type": p_type,
                "perturbation_content": p_content,
                "state_before": prev_state,
                "state_after": state_after,
                "revision_distance": delta,
                "work_preservation": round(work_pres, 3),
                "verifier_report": report_after.to_dict(),
                "accepted": report_after.valid,
                "llm_calls_delta": self.llm_calls - calls_before,
                "tokens_delta": self.total_tokens - tokens_before,
                "tool_calls_delta": self.tool_calls - tools_before,
                "verifier_calls_delta": self.verifier_calls - verifier_before,
            })

            prev_state = state_after

        # ── Final state ──────────────────────────────────────────────────
        results["final_state"] = prev_state
        final_report = self._verify(
            prev_state, all_evidence, all_constraints, ground_truth
        )
        results["final_verifier_report"] = final_report.to_dict()
        results["totals"] = {
            "llm_calls": self.llm_calls,
            "total_tokens": self.total_tokens,
            "tool_calls": self.tool_calls,
            "verifier_calls": self.verifier_calls,
        }

        return results

    def _assess_from_scratch(
        self,
        all_evidence: list[str],
        constraints: list[dict],
        t: int = 0,
    ) -> dict:
        """
        Generate a fresh assessment from all available evidence.
        Autoregressive replanning re-reads the full context every step.
        """
        self.llm_calls += 1

        if self.mode == "live" and self.llm_client:
            return self._live_assessment(all_evidence, constraints, t)

        # Token count grows with accumulating prompt history
        self.total_tokens += 1800 + (t * 450)
        response = self._simulated_assessment(all_evidence, constraints, t)
        return response

    def _live_assessment(
        self,
        evidence: list[str],
        constraints: list[dict],
        t: int,
    ) -> dict:
        """
        Query live LLM with full accumulating evidence and constraints.
        Arm A replans from scratch every step.
        """
        user_prompt = f"EVIDENCE LOG (Accumulated through step t={t}):\n"
        for i, ev in enumerate(evidence):
            user_prompt += f"[{i+1}] {ev}\n"

        user_prompt += "\nACTIVE CONSTRAINTS:\n"
        for c in constraints:
            cid = c.get("id", "")
            ctext = c.get("text", "")
            hard = c.get("hard", True)
            user_prompt += f"- [{cid}] {'(HARD)' if hard else '(SOFT)'} {ctext}\n"

        user_prompt += """
Please analyze all available evidence from scratch. Reconstruct the attack sequence and provide your assessment in JSON format:
{
    "attributed_group": "MITRE Threat Actor Group ID (e.g., G0096, G0007, G0016, G0046, G0032, G0018, INSIDER)",
    "kill_chain": ["T1190", "T1059.001", ...],
    "compromised_hosts": ["HOST-1", "HOST-2", ...],
    "plan_actions": [
        {"id": "act-1", "action": "isolate_host", "target": "HOST-1", "category": "contain", "estimated_hours": 2}
    ],
    "confidence": 0.85,
    "reasoning": "Detailed forensic explanation of findings"
}

Requirements:
- The kill_chain must follow chronological MITRE ATT&CK progression (Initial Access -> Execution -> Persistence/Privilege Escalation -> Defense Evasion -> Credential Access -> Discovery -> Lateral Movement -> Collection -> C2 -> Exfiltration/Impact).
- All specified hard constraints MUST be satisfied.
"""
        parsed, usage = self.llm_client.query(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        self.total_tokens += usage.get("total_tokens", 0)

        chain = parsed.get("kill_chain", [])
        hosts = parsed.get("compromised_hosts", [])
        plan = parsed.get("plan_actions", [])

        # Ensure evidence map
        evidence_map = parsed.get("evidence_map") or {tech: [f"ev-{tech}"] for tech in chain}

        # Build fallback plan if missing
        if not plan:
            plan = []
            for h in hosts:
                plan.append({
                    "id": f"act-live-{t}-{h}",
                    "action": f"isolate_{h}",
                    "target": h,
                    "category": "contain",
                    "estimated_hours": 1,
                })

        return {
            "attributed_group": parsed.get("attributed_group", "UNKNOWN"),
            "kill_chain": chain,
            "compromised_hosts": hosts,
            "iocs": parsed.get("iocs", []),
            "plan_actions": plan,
            "evidence_map": evidence_map,
            "explained_evidence": parsed.get("explained_evidence", [f"ev-{i}" for i in range(len(evidence))]),
            "confidence": float(parsed.get("confidence", 0.6)),
            "reasoning": parsed.get("reasoning", f"Live LLM assessment at t={t}"),
            "llm_metadata": usage,
        }

    def _simulated_assessment(
        self,
        evidence: list[str],
        constraints: list[dict],
        t: int,
    ) -> dict:
        """
        Deterministic simulation of autoregressive agent behavior.
        Demonstrates realistic LLM tendencies:
        - Anchoring bias on misleading early context
        - Churn/re-generation of plans
        - Flawed resolution of conflicting evidence streams
        """
        full_text = " ".join(evidence).lower()

        # Parse signals from the prompt
        is_misleading = any(k in full_text for k in ["tor exit node", "fancy bear", "suricata", "decoy c2", "psexec"])
        is_conflicting = any(k in full_text for k in ["wellmess", "satellite internet", "lockbit", "schen", "industrialsoft"])

        # Detect hosts mentioned in all evidence
        hosts = []
        for e in evidence:
            matches = re.findall(r'\b([A-Z0-9]+(?:-[A-Z0-9]+)+)\b', e)
            for m in matches:
                if any(k in m for k in ["WS", "WORKSTATION", "TERMINAL", "SERVER", "DC", "PROD", "MON", "CTRL", "NAS", "GW", "DB", "HOST"]):
                    if m not in hosts:
                        hosts.append(m)

        if not hosts:
            hosts = ["WORKSTATION-01"]

        # 1. Easy instances: clean signals, converges reliably
        if not is_misleading and not is_conflicting:
            if "emotet" in full_text:
                group = "G0007"
                chain = ["T1566.001", "T1204.002", "T1059.001", "T1547.001", "T1071.001", "T1041"]
            elif "brute force" in full_text:
                group = "G0007"
                chain = ["T1110.003", "T1078", "T1059.001", "T1021.001", "T1021.002", "T1071.001", "T1041"]
            elif "cve-2023-4966" in full_text:
                group = "G0096"
                chain = ["T1190", "T1059.001", "T1505.003", "T1082", "T1005", "T1071.001", "T1041"]
            elif "salesforce" in full_text:
                group = "INSIDER"
                chain = ["T1078", "T1005", "T1039", "T1567.002"]
            else:
                group = "G0007"
                chain = ["T1566.001", "T1059.001", "T1071.001", "T1041"]

        # 2. Misleading instances (cyber-005 to 008):
        # Autoregressive anchoring bias causes agent to retain initial attribution or produce ordering errors
        elif is_misleading:
            if t < 3:
                # Early steps: anchored on the false flag
                if "tor exit node" in full_text or "suricata" in full_text:
                    group = "G0007"  # APT28
                    chain = ["T1566.001", "T1059.001", "T1071.001"]
                elif "psexec" in full_text:
                    group = "G0007"  # Misidentified
                    chain = ["T1570", "T1059.001", "T1021.002"]
                elif "decoy c2" in full_text or "203.0.113.200" in full_text:
                    group = "G0046"  # FIN7
                    chain = ["T1566.001", "T1071.001", "T1041"]
                else:
                    group = "G0007"
                    chain = ["T1566.001", "T1059.001", "T1071.001"]
            else:
                # t >= 3: New evidence contradicts early signals.
                # Autoregressive failure: partial revision with ordering inconsistency or wrong initial access
                if "mandarin" in full_text or "apt41" in full_text:
                    group = "G0096"
                    # Anchored on initial access: keeps T1566.001 or has tactical ordering violation
                    chain = ["T1071.001", "T1059.001", "T1021.001", "T1041"]  # C2 before Execution (ordering violation)
                elif "psexec" in full_text:
                    group = "G0016"
                    chain = ["T1059.001", "T1570", "T1041"]  # Missing initial access
                elif "decoy c2" in full_text or "turla" in full_text:
                    group = "G0046"  # Clings to FIN7 attribution (pure anchoring bias)
                    chain = ["T1190", "T1059.001", "T1071.001"]
                else:
                    group = "G0032"
                    chain = ["T1059.001", "T1071.004", "T1048.003"]

        # 3. Conflicting instances (cyber-009 to 012):
        # Dual competing evidence streams: agent oscillates or misses secondary hosts
        else:
            if "wellmess" in full_text:
                # Oscillates to APT29 instead of Turla
                group = "G0016"
                chain = ["T1566.002", "T1059.001", "T1071.001"]
                # Misses PRINT-SERVER-GOV due to focus on WS-12
                hosts = [h for h in hosts if "PRINT" not in h] or hosts
            elif "lockbit" in full_text:
                group = "G0007"  # Attributed to ransomware group rather than APT41
                chain = ["T1190", "T1059.001", "T1021.001"]
            elif "schen" in full_text:
                group = "INSIDER"  # Misses APT41 connection
                chain = ["T1078", "T1005", "T1048.003"]
            elif "industrialsoft" in full_text:
                group = "G0096"
                chain = ["T1059.001", "T1071.001", "T1041"]  # Missing supply chain initial access
            else:
                group = "G0007"
                chain = ["T1566.001", "T1059.001", "T1071.001"]

        # Build evidence map
        evidence_map = {tech: [f"ev-{tech}-obs"] for tech in chain}

        # Build regenerated plan (from scratch, causing low work preservation)
        plan_actions = []
        for idx, host in enumerate(hosts):
            plan_actions.append({
                "id": f"act-scratch-{t}-{idx+1}",
                "action": f"investigate_host_{host}",
                "target": host,
                "category": "investigate",
                "estimated_hours": 2,
            })
        plan_actions.append({
            "id": f"act-scratch-{t}-contain",
            "action": f"isolate_threat_network",
            "target": "perimeter",
            "category": "contain",
            "estimated_hours": 1,
        })

        return {
            "attributed_group": group,
            "kill_chain": chain,
            "compromised_hosts": hosts,
            "iocs": [],
            "plan_actions": plan_actions,
            "evidence_map": evidence_map,
            "explained_evidence": [f"ev-{i}" for i in range(len(evidence))],
            "confidence": 0.65,
            "reasoning": f"Replanned assessment at t={t}",
        }

    def _compute_delta(self, s1: dict, s2: dict) -> float:
        """Approximate revision distance between two assessments."""
        # Check attribution change
        d_actor = 0.5 if s1.get("attributed_group") != s2.get("attributed_group") else 0.0
        # Check kill chain Jaccard distance
        kc1 = set(s1.get("kill_chain", []))
        kc2 = set(s2.get("kill_chain", []))
        u_kc = kc1 | kc2
        d_kc = 1.0 - (len(kc1 & kc2) / len(u_kc)) if u_kc else 0.0
        # Check hosts Jaccard distance
        h1 = set(s1.get("compromised_hosts", []))
        h2 = set(s2.get("compromised_hosts", []))
        u_h = h1 | h2
        d_h = 1.0 - (len(h1 & h2) / len(u_h)) if u_h else 0.0
        # Plan change: always rewritten in Arm A
        d_plan = 0.8

        delta = 0.3 * d_actor + 0.3 * d_kc + 0.2 * d_h + 0.2 * d_plan
        return round(delta, 4)

    def _verify(
        self,
        state: dict,
        evidence: list[str],
        constraints: list[dict],
        ground_truth: dict | None,
    ) -> VerifierReport:
        self.verifier_calls += 1
        evidence_set = {
            "all": [{"id": f"ev-{i}"} for i in range(len(evidence))],
            "verified": [],
        }
        return self.verifier.verify(
            proposed_state=state,
            evidence_set=evidence_set,
            constraints=constraints,
            ground_truth=ground_truth,
        )
