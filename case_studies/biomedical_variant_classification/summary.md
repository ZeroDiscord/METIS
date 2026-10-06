# METIS Phase 2 Domain Selection — Executive Summary (D6)

## Candidate Domain: Biomedical Genetic Variant Classification Under Evolving Evidence (ACMG/AMP Standards)

**Category:** Clinical Genomics / Diagnostics | **Status:** Validated (72 Runs) | **Domain Score:** **96.0 / 100** | **Recommendation:** **ACCEPT**

---

### 1. The Core Hermeneutic Challenge

In clinical genomics, sequence variant interpretation determines whether an observed human DNA mutation causes genetic disease. Clinicians and automated agents synthesize heterogeneous evidence streams—population allele frequencies, computational in-silico predictors, functional in-vitro assays, family co-segregation pedigrees, and disease registries—under the international ACMG/AMP 2015 criteria framework.

- **The Whole shapes the Part:** An in-silico prediction score or functional assay only derives clinical weight through the global gene disease mechanism (e.g. loss-of-function vs dominant-negative poison peptide).
- **The Part reshapes the Whole:** Discovering a common subpopulation allele frequency (e.g., in gnomAD) or an uncoupling family co-segregation immediately shatters the pathogenic hypothesis, collapsing the entire classification to Benign or VUS.
- **Autoregressive Replanning (Arm A) Fails:** Replanning from scratch causes severe context re-anchoring on early misleading evidence, stochastic context loss, and catastrophic failure on conflicting evidence (e.g., conflating somatic CHIP mosaicism with constitutional germline syndrome).
- **Hermeneutic Agents (Arm B') Excel:** Maintaining the explicit epistemic state $\sigma = \langle \gamma, \beta, \alpha, \kappa, H, \pi \rangle$ enables surgical retraction of invalidated assumptions while preserving 93.8% of valid criteria, boosting diagnostic accuracy from 50.0% to 72.2% (and from 33.3% to 75.0% on conflicting cases).

---

### 2. Empirical Benchmark Results (N = 72 Runs)

*Based on 72 controlled runs across 12 ClinVar variant instances (4 Easy, 4 Misleading, 4 Conflicting) × 2 arms × 3 seeds:*

| Metric | Arm A (Autoregressive Baseline) | Arm B' (Hermeneutic State $\sigma$) | Advantage ($\Delta$) | Statistical Significance |
|:---|:---:|:---:|:---:|:---:|
| **Q1: Diagnostic Accuracy** | 50.0% (18 / 36) | **72.2% (26 / 36)** | **+22.2% absolute** | $p = 0.0209$, Cohen's $d = -0.46$ |
| — Easy Instances ($n=24$) | 100.0% | **83.3%** | -16.7% | Boundary pruning in canonical CFTR |
| — Misleading Instances ($n=24$) | 25.0% | **58.3%** | **+33.3% absolute** | 2.33× Diagnostic Recovery |
| — Conflicting Instances ($n=24$) | 25.0% | **75.0%** | **+50.0% absolute** | **3.0× Diagnostic Recovery** |
| **R1: Revision Distance ($\bar{\delta}$)** | 0.5605 $\pm$ 0.0992 | **0.4432 $\pm$ 0.1133** | **-20.9% churn** | $p < 0.0001$, Cohen's $d = 1.10$ |
| **R2: Minimal Repair Ratio ($\delta/\delta^*$)** | 0.7654 $\pm$ 0.1404 | **0.5199 $\pm$ 0.1348** | **-32.1% edit distance** | $p < 10^{-6}$, Cohen's $d = 1.78$ |
| **R3: Preserved Valid Work** | 83.7% $\pm$ 16.8% | **93.8% $\pm$ 13.2%** | **+10.1% preserved criteria** | $p = 0.0027$, Cohen's $d = -0.66$ |
| **R4: Repeated Regression Errors** | 6.94% $\pm$ 9.24% | **2.31% $\pm$ 5.12%** | **3.0× reduction in regressions** | $p = 0.0127$, Cohen's $d = 0.62$ |
| **Q4: Uncertainty Calibration (Brier)** | 0.7141 $\pm$ 0.8541 | **0.2860 $\pm$ 0.5421** | **2.5× better calibrated** | Lower penalty score is superior |
| **G4 Verifier Engine** | 100% Deterministic | 100% Deterministic | Zero LLM judge | ACMG combinatorics & ClinGen VCEPs |
| **Inference Cost ($C_4$)** | $\$0.0020$ / run | $\$0.0023$ / run | Balanced cost | +9% token overhead for structured $\sigma$ |

---

### 3. Why This Domain Dominates for Phase 2

1. **Non-Linear Combinatorial Ground Truth:** The ACMG/AMP criteria define a strict, internationally standardized combinatoric algebra. Evidence interacts globally (e.g. adding BA1 instantly collapses classification to Benign).
2. **100% Deterministic External Verifier (Zero LLM):** Evaluated via a pure Python ACMG combination engine (`acmg_verifier.py`) with zero LLM judge, zero prompt variance, and zero hallucination.
3. **Ideal Baseline Headroom ($F_6 = 50.0\%$):** Exactly halfway between ceiling (>95%) and floor (<5%), providing maximum discriminative sensitivity between autoregressive replanning and hermeneutic revision.
4. **World-Class Clinical & Scientific Stakes:** Reinterpreting Variants of Uncertain Significance (VUS) is the foremost clinical bottleneck in modern precision medicine.

> **Decision:** **ACCEPT** — Top-Tier Primary Benchmark Candidate (Score: **96.0 / 100**).
