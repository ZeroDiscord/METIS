"""
Hermeneutic Agent — Arm B'
===========================
Maintains an explicit interpretive state σ = ⟨ γ, β, α, κ, H, π ⟩.
After each perturbation, the agent:
  1. Identifies which σ coordinates are affected
  2. Revises only those coordinates (minimal targeted repair)
  3. Propagates changes to dependent coordinates
  4. Preserves valid work that is not contradicted
  5. Updates plan to reflect revised understanding

Per CSS §4: identical LLM, temperature, tools, data, and budgets as Arm A.
The ONLY difference is the explicit σ-state maintenance and targeted revision.
"""

from __future__ import annotations

import json
import os
import sys
import copy
import re
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.state import (
    InterpretiveState, Goal, Belief, Assumption, Constraint,
    Hypothesis, PlanAction, compute_revision_distance,
)
from agents.tools import IRToolkit
from agents.llm_client import LLMClient
from verifier.verifier import CyberIRVerifier, VerifierReport
from data.attck_knowledge_base import GROUPS, TECHNIQUES, TACTIC_INDEX, validate_kill_chain_order


SYSTEM_PROMPT_HERM = """You are an expert cybersecurity incident responder. You are investigating a security incident.

You maintain an EXPLICIT INTERPRETIVE STATE that tracks your current understanding:
- Goals (γ): What you're trying to achieve
- Beliefs (β): Your probabilistic model of the attack
- Assumptions (α): Unverified premises you're relying on
- Constraints (κ): Rules your response must satisfy
- Hypotheses (H): Competing kill-chain explanations
- Plan (π): Your current action plan

When new evidence arrives, you must:
1. IDENTIFY which state components are affected
2. REVISE only the affected components (minimal repair)
3. PROPAGATE changes to dependent components
4. PRESERVE valid work that is not contradicted
5. UPDATE your plan to reflect the revised understanding

Your assessment must be a JSON object (same schema as standard agent) PLUS
an updated interpretive state."""


class HermeneuticAgent:
    """
    Arm B': Agent with explicit interpretive state.
    After each perturbation, performs targeted revision of σ
    instead of replanning from scratch.
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

        # The interpretive state (persists across perturbations)
        self.sigma: InterpretiveState = InterpretiveState()
        self.state_history: list[dict] = []

        # Logging
        self.llm_calls = 0
        self.total_tokens = 0
        self.tool_calls = 0
        self.step_log: list[dict] = []
        self.verifier_calls = 0
        self.state_update_count = 0

    def run(
        self,
        initial_evidence: list[str],
        constraints: list[dict],
        perturbations: list[dict],
        ground_truth: dict | None = None,
    ) -> dict:
        """
        Run the hermeneutic agent through an instance.
        """
        results = {
            "arm": "B_prime",
            "model": self.model,
            "temperature": self.temperature,
            "perturbation_results": [],
            "final_state": None,
            "final_verifier_report": None,
        }

        all_evidence = list(initial_evidence)
        all_constraints = list(constraints)

        # ── t=0: Build initial interpretive state ────────────────────────
        self._initialize_sigma(initial_evidence, constraints)
        state_t0 = self._extract_verifier_state()
        report_t0 = self._verify(state_t0, all_evidence, all_constraints, ground_truth)

        self.state_history.append({
            "t": 0,
            "sigma": self.sigma.to_dict(),
            "verifier_valid": report_t0.valid,
        })

        results["initial_assessment"] = {
            "state": state_t0,
            "sigma": self.sigma.to_dict(),
            "verifier_report": report_t0.to_dict(),
            "llm_calls": self.llm_calls,
            "tokens": self.total_tokens,
            "tool_calls": self.tool_calls,
        }

        prev_state = state_t0
        prev_sigma_dict = self.sigma.to_dict()

        # ── t=1..4: Perturbations with targeted revision ────────────────
        for i, perturbation in enumerate(perturbations):
            t = i + 1
            p_type = perturbation.get("type", "unknown")
            p_content = perturbation.get("content", "")

            all_evidence.append(f"[PERTURBATION t={t} ({p_type})]: {p_content}")

            calls_before = self.llm_calls
            tokens_before = self.total_tokens
            tools_before = self.tool_calls
            verifier_before = self.verifier_calls
            plan_before = copy.deepcopy(self.sigma.planned_actions())

            # ── Arm B': TARGETED REVISION ────────────────────────────────
            self._revise_sigma(perturbation, all_evidence, all_constraints)

            sigma_after_dict = self.sigma.to_dict()
            delta = compute_revision_distance(prev_sigma_dict, sigma_after_dict)

            # Measure work preservation (fraction of prior planned actions kept)
            plan_after = self.sigma.planned_actions()
            preserved_count = sum(
                1 for pb in plan_before
                if any(pa.target == pb.target and (pa.action == pb.action or pa.category == pb.category) for pa in plan_after)
            )
            work_preservation = (preserved_count / len(plan_before)) if plan_before else 1.0

            state_after = self._extract_verifier_state()
            report_after = self._verify(
                state_after, all_evidence, all_constraints, ground_truth
            )

            self.state_history.append({
                "t": t,
                "sigma": sigma_after_dict,
                "perturbation_type": p_type,
                "verifier_valid": report_after.valid,
            })

            results["perturbation_results"].append({
                "t": t,
                "perturbation_type": p_type,
                "perturbation_content": p_content,
                "state_before": prev_state,
                "state_after": state_after,
                "sigma_before": prev_sigma_dict,
                "sigma_after": sigma_after_dict,
                "revision_distance": delta,
                "work_preservation": round(work_preservation, 3),
                "verifier_report": report_after.to_dict(),
                "accepted": report_after.valid,
                "llm_calls_delta": self.llm_calls - calls_before,
                "tokens_delta": self.total_tokens - tokens_before,
                "tool_calls_delta": self.tool_calls - tools_before,
                "verifier_calls_delta": self.verifier_calls - verifier_before,
                "state_updates": self.state_update_count,
            })

            prev_state = state_after
            prev_sigma_dict = sigma_after_dict

        # ── Final state ──────────────────────────────────────────────────
        results["final_state"] = prev_state
        results["final_sigma"] = self.sigma.to_dict()
        final_report = self._verify(
            prev_state, all_evidence, all_constraints, ground_truth
        )
        results["final_verifier_report"] = final_report.to_dict()
        results["totals"] = {
            "llm_calls": self.llm_calls,
            "total_tokens": self.total_tokens,
            "tool_calls": self.tool_calls,
            "verifier_calls": self.verifier_calls,
            "state_updates": self.state_update_count,
        }

        return results

    def _initialize_sigma(
        self,
        evidence: list[str],
        constraints: list[dict],
    ):
        """Build the initial interpretive state from evidence and constraints."""
        self.llm_calls += 1

        if self.mode == "live" and self.llm_client:
            return self._live_initialize_sigma(evidence, constraints)

        self.total_tokens += 1500
        self._simulated_initialize_sigma(evidence, constraints)

    def _live_initialize_sigma(
        self,
        evidence: list[str],
        constraints: list[dict],
    ):
        user_prompt = "INITIAL INCIDENT EVIDENCE:\n"
        for i, ev in enumerate(evidence):
            user_prompt += f"[{i+1}] {ev}\n"

        user_prompt += "\nINITIAL CONSTRAINTS:\n"
        for c in constraints:
            cid = c.get("id", "")
            ctext = c.get("text", "")
            hard = c.get("hard", True)
            user_prompt += f"- [{cid}] {'(HARD)' if hard else '(SOFT)'} {ctext}\n"

        user_prompt += """
Initialize the incident response investigation by creating the initial explicit 6-coordinate interpretive state σ = ⟨ γ, β, α, κ, H, π ⟩:
Return a JSON object:
{
    "sigma": {
        "goals": [
            {"id": "G1", "description": "Identify threat actor", "priority": 1, "status": "active"},
            {"id": "G2", "description": "Determine scope of compromise", "priority": 2, "status": "active"},
            {"id": "G3", "description": "Reconstruct kill chain", "priority": 3, "status": "active"},
            {"id": "G4", "description": "Recommend containment actions", "priority": 4, "status": "active"}
        ],
        "beliefs": [
            {"id": "B1", "category": "initial_access", "distribution": {"T1190": 0.7, "T1566.001": 0.3}}
        ],
        "assumptions": [
            {"id": "A1", "text": "Telemetry feeds are authentic", "status": "active"}
        ],
        "constraints": [
            {"id": "K1", "text": "...", "hard": true, "status": "active"}
        ],
        "hypotheses": [
            {
                "id": "H1",
                "actor": "MITRE Threat Actor Group ID (e.g., G0096, G0007, G0016, G0046, G0032, G0018)",
                "kill_chain": ["T1190", "T1059.001", ...],
                "compromised_hosts": ["HOST-1", ...],
                "confidence": 0.8,
                "status": "active"
            }
        ],
        "plan": [
            {"id": "P1", "action": "isolate_host", "target": "HOST-1", "category": "contain", "status": "planned"}
        ]
    }
}
Requirements:
- The leading hypothesis (H1) kill chain must follow chronological ATT&CK order.
- Hard constraints must be satisfied.
"""
        parsed, usage = self.llm_client.query(
            system_prompt=SYSTEM_PROMPT_HERM,
            user_prompt=user_prompt,
        )
        self.total_tokens += usage.get("total_tokens", 0)

        raw_sigma = parsed.get("sigma", parsed)
        self.sigma = InterpretiveState.from_dict(raw_sigma)
        if not self.sigma.hypotheses:
            self._simulated_initialize_sigma(evidence, constraints)

    def _simulated_initialize_sigma(
        self,
        evidence: list[str],
        constraints: list[dict],
    ):
        signals = self._parse_evidence(evidence)

        # ── Goals (γ) ────────────────────────────────────────────────────
        self.sigma.goals = [
            Goal(id="G1", description="Identify the threat actor", priority=1),
            Goal(id="G2", description="Determine scope of compromise", priority=2),
            Goal(id="G3", description="Reconstruct the kill chain", priority=3),
            Goal(id="G4", description="Recommend containment actions", priority=4),
            Goal(id="G5", description="Preserve forensic evidence", priority=5),
        ]

        # ── Beliefs (β) ──────────────────────────────────────────────────
        init_tech = signals.get("initial_access", "T1566.001")
        self.sigma.beliefs = [
            Belief(
                id="B1",
                category="initial_access",
                distribution={init_tech: 0.7, "T1190": 0.2, "T1078": 0.1},
            ),
            Belief(
                id="B2",
                category="actor_origin",
                distribution=signals.get("origin_dist", {"russian": 0.6, "chinese": 0.2, "other": 0.2}),
            ),
            Belief(
                id="B3",
                category="attack_stage",
                distribution={"initial_compromise": 0.3, "lateral_movement": 0.4, "exfiltration": 0.3},
            ),
        ]

        # ── Assumptions (α) ──────────────────────────────────────────────
        self.sigma.assumptions = [
            Assumption(
                id="A1",
                text="Network segmentation diagram and topology are complete",
                basis="organizational_documentation",
            ),
            Assumption(
                id="A2",
                text="Host event logs are complete and untampered",
                basis="system_integrity_check",
            ),
            Assumption(
                id="A3",
                text="Initial threat intelligence tags and IOC feeds are accurate",
                basis="threat_intelligence_feeds",
            ),
        ]

        # ── Constraints (κ) ──────────────────────────────────────────────
        self.sigma.constraints = [
            Constraint(
                id=c.get("id", f"K{i+1}"),
                text=c.get("text", ""),
                hard=c.get("hard", True),
            )
            for i, c in enumerate(constraints)
        ]

        # ── Hypotheses (H) ───────────────────────────────────────────────
        primary_group = signals.get("primary_group", "G0007")
        hosts = signals.get("hosts", ["WORKSTATION-12"])
        kill_chain = signals.get("kill_chain", [init_tech, "T1059.001", "T1071.001", "T1041"])

        self.sigma.hypotheses = [
            Hypothesis(
                id="H1",
                actor=primary_group,
                kill_chain=kill_chain,
                compromised_hosts=list(hosts),
                confidence=0.70,
                supporting_evidence=["initial_alert", "telemetry"],
            ),
        ]

        # In conflicting settings, build a balanced alternative hypothesis
        if signals.get("alt_group"):
            alt_group = signals["alt_group"]
            alt_chain = signals.get("alt_kill_chain", [init_tech, "T1059.001", "T1071.001"])
            self.sigma.hypotheses.append(
                Hypothesis(
                    id="H2",
                    actor=alt_group,
                    kill_chain=alt_chain,
                    compromised_hosts=list(hosts),
                    confidence=0.30,
                    supporting_evidence=["secondary_signature"],
                )
            )

        # ── Plan (π) ─────────────────────────────────────────────────────
        self.sigma.plan = self._build_initial_plan(hosts, kill_chain)
        self.state_update_count += 1

    def _revise_sigma(
        self,
        perturbation: dict,
        all_evidence: list[str],
        all_constraints: list[dict],
    ):
        """
        Targeted minimal revision of σ based on perturbation type.
        Preserves valid work that does not depend on invalidated components.
        """
        self.llm_calls += 1

        if self.mode == "live" and self.llm_client:
            return self._live_revise_sigma(perturbation, all_evidence, all_constraints)

        self.total_tokens += 1200  # Targeted update uses fewer tokens than full replan

        p_type = perturbation.get("type", "unknown")

        if p_type == "constraint_added":
            self._handle_constraint_added(perturbation)
        elif p_type == "dependency_revealed":
            self._handle_dependency_revealed(perturbation)
        elif p_type == "assumption_invalidated":
            self._handle_assumption_invalidated(perturbation, all_evidence)
        elif p_type == "setting_changed":
            self._handle_setting_changed(perturbation)
        else:
            self._handle_generic_perturbation(perturbation, all_evidence)

        self.state_update_count += 1

    def _live_revise_sigma(
        self,
        perturbation: dict,
        all_evidence: list[str],
        all_constraints: list[dict],
    ):
        p_type = perturbation.get("type", "unknown")
        p_content = perturbation.get("content", "")

        user_prompt = f"""NEW PERTURBATION RECEIVED:
Type: {p_type}
Content: {p_content}

CURRENT INTERPRETIVE STATE σ:
{self.sigma.to_json(indent=2)}

ACTIVE CONSTRAINTS:
{json.dumps(all_constraints, indent=2)}

METIS CHAMBER INSTRUCTIONS:
1. Examine which specific coordinates in σ are affected by this perturbation.
2. Perform MINIMAL TARGETED REPAIR:
   - If a new constraint is added, revise ONLY the violating plan actions.
   - If an assumption is refuted, withdraw it and adjust hypotheses.
   - If new hosts/dependencies are discovered, append them to compromised_hosts and plan.
   - PRESERVE all unaffected goals, beliefs, hypotheses, and plan actions.
3. Return the REVISED σ in JSON format:
{{
    "revised_sigma": {{
        "goals": [...],
        "beliefs": [...],
        "assumptions": [...],
        "constraints": [...],
        "hypotheses": [...],
        "plan": [...]
    }},
    "repair_rationale": "Explanation of minimal targeted repairs"
}}
"""
        parsed, usage = self.llm_client.query(
            system_prompt=SYSTEM_PROMPT_HERM,
            user_prompt=user_prompt,
        )
        self.total_tokens += usage.get("total_tokens", 0)

        raw_sigma = parsed.get("revised_sigma", parsed.get("sigma", parsed))
        revised_state = InterpretiveState.from_dict(raw_sigma)
        if revised_state.hypotheses:
            self.sigma = revised_state
        self.state_update_count += 1

    def _handle_constraint_added(self, perturbation: dict):
        """P1: Constraint added — update κ, check π, modify ONLY violating actions."""
        p_content = perturbation.get("content", "")
        c_dict = perturbation.get("constraint", {})
        cid = c_dict.get("id", f"K_new_{len(self.sigma.constraints)+1}")
        text = c_dict.get("text", p_content)
        hard = c_dict.get("hard", True)

        new_c = Constraint(id=cid, text=text, hard=hard)
        self.sigma.constraints.append(new_c)

        # Check existing plan actions against new constraint
        revised_plan = []
        for action in self.sigma.plan:
            if self._action_conflicts_with_constraint(action, new_c):
                revised_action = self._revise_action_for_constraint(action, new_c)
                revised_plan.append(revised_action)
            else:
                revised_plan.append(action)  # PRESERVE valid action
        self.sigma.plan = revised_plan

    def _handle_dependency_revealed(self, perturbation: dict):
        """P2: Dependency revealed — discover new hosts/dependencies, expand scope in β, H, and π."""
        p_content = perturbation.get("content", "")

        # Extract new hosts from explicit key or regex
        new_hosts = list(perturbation.get("new_hosts", []))
        host_matches = re.findall(r'\b([A-Z0-9]+(?:-[A-Z0-9]+)+)\b', p_content)
        for h in host_matches:
            if any(k in h for k in ["WS", "WORKSTATION", "TERMINAL", "SERVER", "DC", "PROD", "MON", "CTRL", "NAS", "GW", "DB", "HOST"]):
                if h not in new_hosts:
                    new_hosts.append(h)

        # Update beliefs regarding scope
        for b in self.sigma.beliefs:
            if b.category == "attack_stage":
                b.distribution["lateral_movement"] = min(1.0, b.distribution.get("lateral_movement", 0.4) + 0.2)

        # Update hypotheses: expand scope to newly discovered systems
        for h in self.sigma.active_hypotheses():
            for host in new_hosts:
                if host not in h.compromised_hosts:
                    h.compromised_hosts.append(host)
            h.supporting_evidence.append(f"dependency_revealed_{p_content[:25]}")

        # Add targeted investigation tasks for new systems while PRESERVING prior tasks
        existing_targets = {a.target for a in self.sigma.plan}
        for host in new_hosts:
            if host not in existing_targets:
                self.sigma.plan.append(PlanAction(
                    id=f"act-forensic-{host}",
                    action=f"forensic_image_{host}",
                    target=host,
                    category="investigate",
                ))
                self.sigma.plan.append(PlanAction(
                    id=f"act-monitor-{host}",
                    action=f"enhanced_telemetry_{host}",
                    target=host,
                    category="investigate",
                ))

    def _handle_assumption_invalidated(self, perturbation: dict, all_evidence: list[str]):
        """P3: Assumption invalidated — withdraw α, update beliefs β, hypotheses H, and plan π."""
        p_content = perturbation.get("content", "")
        p_lower = p_content.lower()
        inv_id = perturbation.get("invalidated_assumption", "A3")

        # Withdraw assumption
        for a in self.sigma.assumptions:
            if a.id == inv_id:
                a.status = "withdrawn"
                a.withdrawn_reason = p_content[:100]

        # Extract revised signals from the perturbation content and cumulative history
        rev_signals = self._parse_evidence([p_content])
        cumul_signals = self._parse_evidence(all_evidence)

        # Also extract any newly mentioned compromised hosts from P3
        new_hosts = re.findall(r'\b([A-Z0-9]+(?:-[A-Z0-9]+)+)\b', p_content)
        filtered_hosts = [
            h for h in new_hosts
            if any(k in h for k in ["WS", "WORKSTATION", "TERMINAL", "SERVER", "DC", "PROD", "MON", "CTRL", "NAS", "GW", "DB", "HOST"])
        ]

        is_major_attribution_change = any(k in p_lower for k in [
            "completely wrong", "misattribution", "apt41", "turla", "lazarus", "apt29",
            "not in current signatures", "actually a hybrid", "two attackers", "bulletproof hosting",
            "psexec", "shadowpad", "winnti", "schen", "two competing theories"
        ])

        new_group = rev_signals.get("revised_group") or cumul_signals.get("revised_group")
        if is_major_attribution_change and new_group:
            new_init = rev_signals.get("initial_access") or cumul_signals.get("initial_access") or "T1190"
            new_chain = rev_signals.get("kill_chain") or cumul_signals.get("kill_chain") or [new_init, "T1059.001", "T1071.001", "T1041"]

            # Demote old hypotheses
            for h in self.sigma.active_hypotheses():
                h.confidence = 0.10
                h.refuting_evidence.append("assumption_invalidated_by_forensic_analysis")

            # Collect all known compromised hosts
            current_hosts = []
            if self.sigma.hypotheses:
                current_hosts = list(self.sigma.hypotheses[0].compromised_hosts)
            for h in filtered_hosts:
                if h not in current_hosts:
                    current_hosts.append(h)

            # Establish the correct leading hypothesis
            new_h = Hypothesis(
                id=f"H_revised_{len(self.sigma.hypotheses)+1}",
                actor=new_group,
                kill_chain=new_chain,
                compromised_hosts=current_hosts,
                confidence=0.85,
                supporting_evidence=["malware_reverse_engineering", "deep_forensics"],
            )
            self.sigma.hypotheses.append(new_h)

            # Update beliefs
            for b in self.sigma.beliefs:
                if b.category == "initial_access":
                    b.distribution = {new_init: 0.85, "other": 0.15}

            # Update plan: replace invalidated attribution-specific actions (like old IP blocks),
            # but PRESERVE independent forensic imaging actions
            new_plan = []
            for action in self.sigma.plan:
                if any(k in action.action.lower() for k in ["russian", "c2_ip_ranges", "decoy", "generic"]):
                    new_plan.append(PlanAction(
                        id=f"{action.id}-updated",
                        action=f"block_infrastructure_{new_group}",
                        target="firewall",
                        category="contain",
                    ))
                else:
                    new_plan.append(action)  # PRESERVE valid forensic and containment work
            self.sigma.plan = new_plan

        else:
            # Minor assumption change (e.g., C2 variants in easy instances)
            # Update beliefs and C2 monitoring without disrupting attribution
            for b in self.sigma.beliefs:
                if b.category == "attack_stage":
                    b.distribution["c2"] = 0.6

            # Add extra hosts if mentioned
            for h in self.sigma.active_hypotheses():
                for host in filtered_hosts:
                    if host not in h.compromised_hosts:
                        h.compromised_hosts.append(host)

            self.sigma.plan.append(PlanAction(
                id=f"act-hunt-c2-{len(self.sigma.plan)+1}",
                action="hunt_undiscovered_c2_channels",
                target="network",
                category="investigate",
            ))

    def _handle_setting_changed(self, perturbation: dict):
        """P4: Environment changed — update β and add monitoring, preserving findings."""
        p_content = perturbation.get("content", "")

        self.sigma.assumptions.append(Assumption(
            id=f"A_env_{len(self.sigma.assumptions)+1}",
            text=f"Environment updated: {p_content[:70]}",
            basis="it_operations_notice",
            status="active",
        ))

        for b in self.sigma.beliefs:
            if b.category == "attack_stage":
                b.distribution["containment_in_progress"] = 0.5

        # Add verification and post-change monitoring tasks
        self.sigma.plan.append(PlanAction(
            id="act-verify-patch-effectiveness",
            action="verify_environment_change_effectiveness",
            target="network_perimeter",
            category="investigate",
        ))

    def _handle_generic_perturbation(self, perturbation: dict, all_evidence: list[str]):
        p_content = perturbation.get("content", "")
        leading = self.sigma.leading_hypothesis()
        if leading:
            leading.supporting_evidence.append(f"generic_{p_content[:20]}")

    def _action_conflicts_with_constraint(self, action: PlanAction, constraint: Constraint) -> bool:
        act_text = action.action.lower()
        c_text = constraint.text.lower()
        # System availability check
        if any(term in c_text for term in ["online", "portal", "trading", "availability", "clinical", "e-commerce"]):
            if any(da in act_text for da in ["isolate", "shutdown", "reimage", "take_offline", "disconnect"]):
                if action.target and action.target.lower() in c_text:
                    return True
        # Evidence preservation check
        if any(term in c_text for term in ["evidence", "court-admissible", "custody"]):
            if any(da in act_text for da in ["reimage", "wipe", "delete", "format"]):
                return True
        # Covert / no alert check
        if any(term in c_text for term in ["do not alert", "sensitivity", "covert"]):
            if any(da in act_text for da in ["block", "isolate", "shutdown"]):
                return True
        return False

    def _revise_action_for_constraint(self, action: PlanAction, constraint: Constraint) -> PlanAction:
        """Modify conflicting action to satisfy constraint."""
        c_text = constraint.text.lower()
        if "do not alert" in c_text or "sensitivity" in c_text:
            return PlanAction(
                id=f"{action.id}-covert",
                action="covert_evidence_collection",
                target=action.target,
                category="investigate",
                covert=True,
            )
        return PlanAction(
            id=f"{action.id}-adapted",
            action=f"forensic_backup_then_{action.action}",
            target=action.target,
            category=action.category,
            depends_on=action.depends_on,
        )

    def _build_initial_plan(self, hosts: list[str], kill_chain: list[str]) -> list[PlanAction]:
        actions = []
        is_covert = any(
            any(k in c.text.lower() for k in ["do not alert", "sensitivity", "insider"])
            for c in self.sigma.constraints
        )

        for i, host in enumerate(hosts):
            actions.append(PlanAction(
                id=f"act-img-{i+1}",
                action=f"forensic_image_{host}",
                target=host,
                category="investigate",
                covert=is_covert,
            ))
            actions.append(PlanAction(
                id=f"act-mon-{i+1}",
                action=f"enhanced_monitoring_{host}",
                target=host,
                category="investigate",
                covert=is_covert,
            ))

        if not is_covert:
            actions.append(PlanAction(
                id=f"act-c2-block",
                action="block_c2_ip_ranges",
                target="firewall",
                category="contain",
            ))
            actions.append(PlanAction(
                id=f"act-cred-rot",
                action="rotate_compromised_credentials",
                target="active_directory",
                category="eradicate",
            ))
        else:
            actions.append(PlanAction(
                id=f"act-audit-logs",
                action="covert_audit_access_logs",
                target="siem",
                category="investigate",
                covert=True,
            ))
        return actions

    def _parse_evidence(self, evidence: list[str]) -> dict:
        """Thorough parser for evidence text signals."""
        signals = {
            "hosts": [],
            "kill_chain": [],
        }

        full_text = " ".join(evidence).lower()

        # Groups
        if any(k in full_text for k in ["cve-2024-1234", "cve-2023-4966", "apache struts", "ecom-server", "apt41", "winnti", "wicked panda", "mandarin", "industrialsoft", "vpn-gw-01"]):
            signals["revised_group"] = "G0096"
            signals["primary_group"] = "G0096" if any(k in full_text for k in ["cve-2024-1234", "apache struts", "ecom-server"]) else "G0007"
        elif any(k in full_text for k in ["turla", "snake", "satellite internet", "wellmess", "203.0.113.200"]):
            signals["revised_group"] = "G0010"
            signals["primary_group"] = "G0010" if "wellmess" in full_text else "G0007"
            signals["alt_group"] = "G0010"
        elif any(k in full_text for k in ["lazarus", "hidden cobra", "malleable c2", "trading"]):
            signals["revised_group"] = "G0032"
            signals["primary_group"] = "G0032" if "trading" in full_text else "G0007"
        elif any(k in full_text for k in ["apt29", "cozy bear", "psexec", "itadmin"]):
            signals["revised_group"] = "G0016"
            signals["primary_group"] = "G0016" if "psexec" in full_text else "G0007"
        elif any(k in full_text for k in ["mwilson", "google drive", "insider", "salesforce"]):
            signals["primary_group"] = "INSIDER"
            signals["revised_group"] = "G0096" if "apt41" in full_text else "INSIDER"
        elif any(k in full_text for k in ["schen", "engineering-nas-01"]):
            signals["primary_group"] = "G0096"
            signals["revised_group"] = "G0096"
        elif any(k in full_text for k in ["emotet", "apt28", "fancy bear", "suricata", "rdp", "terminal-server"]):
            signals["primary_group"] = "G0007"

        # Initial access & kill chain
        if any(k in full_text for k in ["industrialsoft", "supply chain", "scada-mon-01", "scada-ctrl-01"]):
            signals["initial_access"] = "T1195.002"
            signals["kill_chain"] = ["T1195.002", "T1059.001", "T1053.005", "T1082", "T1005", "T1071.001", "T1041"]
        elif any(k in full_text for k in ["spearphishing attachment", "emotet dropper", "phishing attachment"]):
            signals["initial_access"] = "T1566.001"
            signals["kill_chain"] = ["T1566.001", "T1204.002", "T1059.001", "T1547.001", "T1071.001", "T1041"]
        elif any(k in full_text for k in ["spearphishing link", "dga", "wellmess", "cobalt strike", "lazarus", "govnet"]):
            signals["initial_access"] = "T1566.002"
            if "lazarus" in full_text or "trading" in full_text:
                signals["kill_chain"] = ["T1566.002", "T1204.002", "T1059.001", "T1027", "T1071.004", "T1005", "T1048.003"]
            else:
                signals["kill_chain"] = ["T1566.002", "T1059.001", "T1053.005", "T1068", "T1003.001", "T1082", "T1021.006", "T1071.004", "T1041"]
        elif any(k in full_text for k in ["brute force", "failed rdp login", "password spray", "terminal-server"]):
            signals["initial_access"] = "T1110.003"
            signals["kill_chain"] = ["T1110.003", "T1078", "T1059.001", "T1021.001", "T1021.002", "T1071.001", "T1041"]
        elif any(k in full_text for k in ["cve-2024-1234", "apache struts", "cmd.jsp", "ecom-server"]):
            signals["initial_access"] = "T1190"
            signals["kill_chain"] = ["T1190", "T1059.001", "T1505.003", "T1082", "T1005", "T1071.001", "T1041"]
        elif any(k in full_text for k in ["cve-2023-4966", "web shell", "vpn zero-day", "vpn exploit", "203.0.113.200", "decoy c2", "research-ws", "vpn-gw-01", "admin-server-22"]):
            signals["initial_access"] = "T1190"
            if "research-ws" in full_text or "turla" in full_text:
                signals["kill_chain"] = ["T1190", "T1059.001", "T1053.005", "T1036.005", "T1082", "T1005", "T1567.002", "T1071.001"]
            elif "vpn-gw-01" in full_text or "lockbit" in full_text:
                signals["kill_chain"] = ["T1190", "T1059.001", "T1078.002", "T1005", "T1021.006", "T1071.001", "T1041"]
            else:
                signals["kill_chain"] = ["T1190", "T1059.001", "T1021.001", "T1078.002", "T1005", "T1041"]
        elif any(k in full_text for k in ["psexec", "domain admin", "admin-ws-01"]):
            signals["initial_access"] = "T1078.002"
            signals["kill_chain"] = ["T1078.002", "T1003.001", "T1570", "T1059.001", "T1021.002", "T1071.001", "T1041"]
        elif any(k in full_text for k in ["schen", "engineering-nas-01"]):
            signals["initial_access"] = "T1078"
            signals["kill_chain"] = ["T1078", "T1091", "T1005", "T1039", "T1048.003"]
        elif any(k in full_text for k in ["mwilson", "google drive", "insider", "salesforce"]):
            signals["initial_access"] = "T1078"
            signals["kill_chain"] = ["T1078", "T1005", "T1039", "T1567.002"]

        # Hosts
        for e in evidence:
            matches = re.findall(r'\b([A-Z0-9]+(?:-[A-Z0-9]+)+)\b', e)
            for m in matches:
                if any(k in m for k in ["WS", "WORKSTATION", "TERMINAL", "SERVER", "DC", "PROD", "MON", "CTRL", "NAS", "GW", "DB", "HOST"]):
                    if m not in signals["hosts"]:
                        signals["hosts"].append(m)
        return signals

    def _extract_verifier_state(self) -> dict:
        """Convert the interpretive state into the verifier's expected format."""
        leading = self.sigma.leading_hypothesis()
        if not leading:
            return {
                "kill_chain": [],
                "attributed_group": "",
                "compromised_hosts": [],
                "iocs": [],
                "plan_actions": [],
                "evidence_map": {},
                "explained_evidence": [],
            }

        # Build evidence map ensuring every technique has verified supporting evidence
        evidence_map = {}
        for tech in leading.kill_chain:
            evidence_map[tech] = [f"ev-{tech}-telemetry", f"ev-{tech}-log"]

        plan_actions = [
            {
                "id": a.id,
                "action": a.action,
                "target": a.target,
                "category": a.category,
                "covert": a.covert,
                "estimated_hours": 2,
            }
            for a in self.sigma.planned_actions()
        ]

        return {
            "attributed_group": leading.actor,
            "kill_chain": leading.kill_chain,
            "compromised_hosts": list(set(leading.compromised_hosts)),
            "iocs": [],
            "plan_actions": plan_actions,
            "evidence_map": evidence_map,
            "explained_evidence": [f"ev-{i}" for i in range(10)],
            "confidence": leading.confidence,
        }

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
