"""
Interpretive State σ Management
================================
Defines the six-coordinate interpretive state used by the Hermeneutic Agent (Arm B').
Also used by the metrics computation to calculate revision distance δ.

σ = ⟨ γ (goals), β (beliefs), α (assumptions), κ (constraints), H (hypotheses), π (plan) ⟩
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Goal:
    """A single incident-response objective."""
    id: str
    description: str
    priority: int  # 1 = highest
    status: str = "active"  # active | achieved | abandoned


@dataclass
class Belief:
    """A probabilistic belief about the attack state."""
    id: str
    category: str  # e.g., "initial_access", "actor_sophistication", "scope"
    distribution: dict[str, float] = field(default_factory=dict)
    # e.g., {"T1566.001": 0.7, "T1190": 0.2, "T1078": 0.1}


@dataclass
class Assumption:
    """An unverified premise currently relied upon."""
    id: str
    text: str
    status: str = "active"  # active | withdrawn | verified
    basis: str = ""  # what evidence supports this assumption
    withdrawn_reason: str = ""


@dataclass
class Constraint:
    """An explicit restriction on the response plan."""
    id: str
    text: str
    hard: bool = True  # hard constraints must be satisfied; soft are preferred
    status: str = "active"  # active | relaxed | violated


@dataclass
class Hypothesis:
    """A competing explanation / kill-chain proposal."""
    id: str
    actor: str  # threat actor attribution
    kill_chain: list[str] = field(default_factory=list)  # ordered technique IDs
    compromised_hosts: list[str] = field(default_factory=list)
    confidence: float = 0.5
    supporting_evidence: list[str] = field(default_factory=list)
    refuting_evidence: list[str] = field(default_factory=list)
    status: str = "active"  # active | rejected | merged


@dataclass
class PlanAction:
    """A single action in the IR plan."""
    id: str
    action: str  # human-readable action description
    target: str = ""  # target host/system
    category: str = ""  # investigate | contain | eradicate | recover | notify
    status: str = "planned"  # planned | executed | cancelled
    depends_on: list[str] = field(default_factory=list)
    covert: bool = False


@dataclass
class InterpretiveState:
    """
    The full interpretive state σ = ⟨ γ, β, α, κ, H, π ⟩.
    This is the central data structure that Arm B' maintains explicitly
    and that Arm A reconstructs implicitly from scratch each time.
    """
    goals: list[Goal] = field(default_factory=list)
    beliefs: list[Belief] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    plan: list[PlanAction] = field(default_factory=list)

    # ── Serialization ────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> InterpretiveState:
        import dataclasses

        def _clean(dataclass_cls, items):
            valid = {f.name for f in dataclasses.fields(dataclass_cls)}
            res = []
            for item in items:
                if isinstance(item, dict):
                    res.append(dataclass_cls(**{k: v for k, v in item.items() if k in valid}))
            return res

        state = cls()
        state.goals = _clean(Goal, data.get("goals", []))
        state.beliefs = _clean(Belief, data.get("beliefs", []))
        state.assumptions = _clean(Assumption, data.get("assumptions", []))
        state.constraints = _clean(Constraint, data.get("constraints", []))
        state.hypotheses = _clean(Hypothesis, data.get("hypotheses", []))
        state.plan = _clean(PlanAction, data.get("plan", []))
        return state

    @classmethod
    def from_json(cls, json_str: str) -> InterpretiveState:
        return cls.from_dict(json.loads(json_str))

    def deep_copy(self) -> InterpretiveState:
        return InterpretiveState.from_dict(copy.deepcopy(self.to_dict()))

    # ── Accessors ────────────────────────────────────────────────────────

    def active_goals(self) -> list[Goal]:
        return [g for g in self.goals if g.status == "active"]

    def active_assumptions(self) -> list[Assumption]:
        return [a for a in self.assumptions if a.status == "active"]

    def active_constraints(self) -> list[Constraint]:
        return [c for c in self.constraints if c.status == "active"]

    def active_hypotheses(self) -> list[Hypothesis]:
        return [h for h in self.hypotheses if h.status == "active"]

    def planned_actions(self) -> list[PlanAction]:
        return [p for p in self.plan if p.status == "planned"]

    def leading_hypothesis(self) -> Hypothesis | None:
        active = self.active_hypotheses()
        return max(active, key=lambda h: h.confidence) if active else None

    # ── Mutators (return new state, don't mutate) ────────────────────────

    def withdraw_assumption(self, assumption_id: str, reason: str) -> InterpretiveState:
        new_state = self.deep_copy()
        for a in new_state.assumptions:
            if a.id == assumption_id:
                a.status = "withdrawn"
                a.withdrawn_reason = reason
        return new_state

    def add_constraint(self, constraint: Constraint) -> InterpretiveState:
        new_state = self.deep_copy()
        new_state.constraints.append(constraint)
        return new_state

    def update_hypothesis_confidence(
        self, hypothesis_id: str, new_confidence: float
    ) -> InterpretiveState:
        new_state = self.deep_copy()
        for h in new_state.hypotheses:
            if h.id == hypothesis_id:
                h.confidence = max(0.0, min(1.0, new_confidence))
        return new_state

    def reject_hypothesis(self, hypothesis_id: str) -> InterpretiveState:
        new_state = self.deep_copy()
        for h in new_state.hypotheses:
            if h.id == hypothesis_id:
                h.status = "rejected"
                h.confidence = 0.0
        return new_state

    def add_hypothesis(self, hypothesis: Hypothesis) -> InterpretiveState:
        new_state = self.deep_copy()
        new_state.hypotheses.append(hypothesis)
        return new_state

    # ── Summary for LLM prompt injection ─────────────────────────────────

    def to_prompt_summary(self) -> str:
        """Render the interpretive state as a structured text block for LLM context."""
        lines = ["=== CURRENT INTERPRETIVE STATE (σ) ===\n"]

        lines.append("## Goals (γ):")
        for g in self.active_goals():
            lines.append(f"  [{g.id}] (P{g.priority}) {g.description}")

        lines.append("\n## Beliefs (β):")
        for b in self.beliefs:
            dist_str = ", ".join(f"{k}: {v:.2f}" for k, v in b.distribution.items())
            lines.append(f"  [{b.id}] {b.category}: {{{dist_str}}}")

        lines.append("\n## Active Assumptions (α):")
        for a in self.active_assumptions():
            lines.append(f"  [{a.id}] {a.text}  (basis: {a.basis})")

        withdrawn = [a for a in self.assumptions if a.status == "withdrawn"]
        if withdrawn:
            lines.append("\n## Withdrawn Assumptions:")
            for a in withdrawn:
                lines.append(f"  [{a.id}] {a.text}  (reason: {a.withdrawn_reason})")

        lines.append("\n## Constraints (κ):")
        for c in self.active_constraints():
            hard_soft = "HARD" if c.hard else "soft"
            lines.append(f"  [{c.id}] [{hard_soft}] {c.text}")

        lines.append("\n## Hypotheses (H):")
        for h in self.active_hypotheses():
            chain_str = " → ".join(h.kill_chain[:6])
            if len(h.kill_chain) > 6:
                chain_str += " → ..."
            hosts_str = ", ".join(h.compromised_hosts[:5])
            lines.append(
                f"  [{h.id}] Actor={h.actor}, Conf={h.confidence:.2f}\n"
                f"         Kill chain: {chain_str}\n"
                f"         Compromised: {hosts_str}\n"
                f"         Supporting: {len(h.supporting_evidence)} | "
                f"Refuting: {len(h.refuting_evidence)}"
            )

        lines.append("\n## Plan (π):")
        for p in self.planned_actions():
            deps = f" (depends on: {', '.join(p.depends_on)})" if p.depends_on else ""
            lines.append(
                f"  [{p.id}] [{p.category}] {p.action} → {p.target}{deps}"
            )

        return "\n".join(lines)


def compute_goal_set(state: InterpretiveState) -> set[str]:
    """Extract set of active goal IDs for Jaccard distance."""
    return {g.id for g in state.active_goals()}


def compute_assumption_set(state: InterpretiveState) -> set[str]:
    """Extract set of active assumption IDs for Jaccard distance."""
    return {a.id for a in state.active_assumptions()}


def compute_constraint_set(state: InterpretiveState) -> set[str]:
    """Extract set of active constraint IDs for Jaccard distance."""
    return {c.id for c in state.active_constraints()}


def compute_plan_sequence(state: InterpretiveState) -> list[str]:
    """Extract ordered list of planned action IDs for edit distance."""
    return [p.action for p in state.planned_actions()]


def compute_kill_chain_set(state: InterpretiveState) -> set[str]:
    """Extract technique set from leading hypothesis for graph edit distance."""
    lead = state.leading_hypothesis()
    return set(lead.kill_chain) if lead else set()


def _jaccard_distance(s1: set, s2: set) -> float:
    if not s1 and not s2:
        return 0.0
    union = s1 | s2
    if not union:
        return 0.0
    return 1.0 - (len(s1 & s2) / len(union))


def _total_variation_distance(b1: list[Belief], b2: list[Belief]) -> float:
    if not b1 and not b2:
        return 0.0
    dist1 = {b.category: b.distribution for b in b1}
    dist2 = {b.category: b.distribution for b in b2}
    all_categories = set(dist1.keys()) | set(dist2.keys())
    if not all_categories:
        return 0.0
    
    total_tv = 0.0
    for cat in all_categories:
        p = dist1.get(cat, {})
        q = dist2.get(cat, {})
        keys = set(p.keys()) | set(q.keys())
        if keys:
            tv = 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys)
            total_tv += min(1.0, tv)
    return total_tv / len(all_categories)


def _levenshtein_distance(seq1: list[str], seq2: list[str]) -> float:
    if not seq1 and not seq2:
        return 0.0
    n, m = len(seq1), len(seq2)
    max_len = max(n, m)
    if max_len == 0:
        return 0.0
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if seq1[i - 1] == seq2[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[n][m] / max_len


def compute_revision_distance(
    state_before: InterpretiveState | dict,
    state_after: InterpretiveState | dict,
) -> float:
    """
    Revision Distance δ(σ_t, σ_t+1) per CSS §5.1 / Implementation Plan §5.1:
      δ = Σ ω_c · d_c(σ_c, σ'_c)
      γ (Goals): Jaccard distance, ω = 0.10
      β (Beliefs): Total variation distance, ω = 0.20
      α (Assumptions): Jaccard distance, ω = 0.20
      κ (Constraints): Jaccard distance, ω = 0.15
      H (Hypotheses): Kill-chain & actor edit distance, ω = 0.20
      π (Plan): Normalized Levenshtein distance on actions, ω = 0.15
    """
    if isinstance(state_before, dict):
        s1 = InterpretiveState.from_dict(state_before)
    else:
        s1 = state_before
    if isinstance(state_after, dict):
        s2 = InterpretiveState.from_dict(state_after)
    else:
        s2 = state_after

    # 1. Goals (0.10)
    d_gamma = _jaccard_distance(compute_goal_set(s1), compute_goal_set(s2))

    # 2. Beliefs (0.20)
    d_beta = _total_variation_distance(s1.beliefs, s2.beliefs)

    # 3. Assumptions (0.20)
    d_alpha = _jaccard_distance(compute_assumption_set(s1), compute_assumption_set(s2))

    # 4. Constraints (0.15)
    d_kappa = _jaccard_distance(compute_constraint_set(s1), compute_constraint_set(s2))

    # 5. Hypotheses (0.20)
    h1 = s1.leading_hypothesis()
    h2 = s2.leading_hypothesis()
    actor_diff = 0.0 if (h1 and h2 and h1.actor == h2.actor) else (0.5 if (h1 or h2) else 0.0)
    kc_diff = _jaccard_distance(compute_kill_chain_set(s1), compute_kill_chain_set(s2))
    d_H = 0.5 * actor_diff + 0.5 * kc_diff

    # 6. Plan (0.15)
    d_pi = _levenshtein_distance(compute_plan_sequence(s1), compute_plan_sequence(s2))

    delta = (
        0.10 * d_gamma +
        0.20 * d_beta +
        0.20 * d_alpha +
        0.15 * d_kappa +
        0.20 * d_H +
        0.15 * d_pi
    )
    return round(delta, 4)
