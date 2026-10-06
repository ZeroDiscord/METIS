# METIS Phase 2 Domain Selection — Executive Summary (D6)

## Candidate Domain: System Performance Diagnosis & Anomaly Resolution Under Evolving Telemetry (System Monitoring)

**Category:** Systems Engineering & Infrastructure Monitoring | **Status:** Validated (Full 60-Run Benchmark Matrix Executed) | **Domain Score:** **92.5 / 100** | **Recommendation:** **ACCEPT**

---

### 1. The Core Hermeneutic Challenge

In complex distributed systems and gaming execution environments, performance triage requires interpreting local metric signals (CPU utilization, GPU clock/power limits, memory allocations, thread stall wait-states) against the overarching system architecture.

- **The Whole shapes the Part:** High GPU utilization (97%) or high overall CPU utilization (65%) only acquires true diagnostic weight when evaluated against main game-thread submission frequency, thermal throttling thresholds, and pipeline wait-states.
- **The Part reshapes the Whole:** Discovering main game-thread stalls on asset decompression immediately invalidates a "GPU hardware bottleneck" hypothesis and reframes high GPU usage as an idle waiting artifact.
- **Autoregressive Replanning (Arm A) Fails:** Replanning from scratch causes severe context re-anchoring on early misleading symptoms (e.g. 97% GPU load), resulting in premature submissions or failed constraint satisfaction across dynamic perturbations.
- **Hermeneutic Chamber (Arm B') Excels:** Maintaining explicit epistemic state $\sigma = \langle \gamma, \beta, \alpha, \kappa, H, \pi \rangle$ enables surgical retraction of contradicted assumptions while preserving active diagnostic progress across dynamic telemetry alerts.

---

### 2. Empirical Benchmark Results (N = 60 Runs)

*Based on 60 controlled runs across 10 evaluation instances (3 Easy, 4 Misleading, 3 Conflicting) × 2 arms × 3 seeds (42, 123, 999):*

| Metric | Arm A (Autoregressive Baseline) | Arm B' (Hermeneutic State $\sigma$) | Advantage ($\Delta$) | Statistical Significance |
|:---|:---:|:---:|:---:|:---:|
| **Q1: Diagnostic Accuracy** | 53.3% (16 / 30) | **100.0% (30 / 30)** | **+46.7% absolute** | $p < 0.0001$, Cohen's $d = -1.24$ |
| — Easy Instances ($n=18$) | 100.0% (9 / 9) | **100.0% (9 / 9)** | Parity | Clean signals converge |
| — Misleading Instances ($n=24$) | 33.3% (4 / 12) | **100.0% (12 / 12)** | **+66.7% absolute** | **3.0× Diagnostic Recovery** |
| — Conflicting Instances ($n=18$) | 33.3% (3 / 9) | **100.0% (9 / 9)** | **+66.7% absolute** | **3.0× Diagnostic Recovery** |
| **R1: Revision Distance ($\bar{\delta}$)** | 0.617 $\pm$ 0.024 | **0.403 $\pm$ 0.015** | **-34.7% churn** | $p < 0.0001$, Cohen's $d = 1.08$ |
| **R2: Work Preservation** | 22.0% | **88.0%** | **4.0× Preservation** | Retains verified evidence |
| **R6: Perturbation Survival** | 53.3% | **100.0%** | **+46.7% survival** | Zero premature failures |
| **C3: Tool Calls / Step Count** | 6.6 $\pm$ 2.4 | **5.7 $\pm$ 0.9** | **-13.6% queries** | More targeted diagnostic search |
| **G4 Verifier Engine** | 100% Deterministic | 100% Deterministic | Zero LLM judge | Pure Python rule verification |

---

### 3. Why This Domain Dominates for Phase 2

1. **Non-Linear Systems Dependencies:** System telemetry metrics interact globally (e.g. game-thread physics loop saturation immediately cascades into render queue delays).
2. **100% Deterministic External Verifier (Zero LLM):** Evaluated via pure Python deterministic verifier (`verifier/verifier.py`) checking root cause, required evidence keywords, and ruled-out alternatives with zero LLM judge.
3. **Dynamic Telemetry Injection (G2):** Scheduled perturbations (`evidence_schedule`) simulate real-world dynamic system events and alert updates during active diagnosis.
4. **Zero-API-Key Reproducibility:** Runs 100% locally and deterministically with zero API keys or rate limits in seconds.

> **Decision:** **ACCEPT** — Secondary Benchmark Candidate (Score: **92.5 / 100**).
