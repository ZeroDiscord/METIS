# METIS Domain-Selection Case Study Report (CSS v1.0)

**Domain:** Biomedical Genetic Variant Classification Under Evolving Evidence (ACMG/AMP Standards)  
**Category:** Clinical Genomics / Diagnostics  
**Owner:** AIML Specialization Team  
**Standard Version:** CSS v1.0 (Phase 2 Problem Setting Selection)  
**Status:** Completed & Validated (Full Empirical Benchmark: 72 Runs)  
**Date:** October 6, 2026  

---

## Section A: Executive Summary & Recommendation

| Assessment Metric | Evaluation Result |
|:---|:---|
| **Domain Score (out of 100)** | **96.0 / 100** (Top-Tier Primary Candidate) |
| **Recommendation** | **ACCEPT** — Primary Benchmark Candidate for Phase 2 METIS Problem Setting |
| **G1–G4 Admissibility** | **PASS on all 4 Gates** (G1 Global Dep, G2 Dynamic Ev, G3 Revisable Interp, G4 Verifiable Output) |
| **Baseline Headroom (F6)** | **50.0% Arm A Success** (Optimal discriminative window: neither ceiling >95% nor floor <5%) |
| **Discriminative Advantage** | **+22.2% overall accuracy** (Arm B' 72.2% vs Arm A 50.0%, $p = 0.0209$); **+50.0% on Conflicting Tier** (75.0% vs 25.0%) |
| **Revision Churn Reduction** | **-20.9% lower revision distance $\bar{\delta}$** ($p < 0.0001$, Cohen's $d = 1.10$); **-32.1% minimal repair ratio** ($d = 1.78$) |
| **Empirical Scope** | 12 Evaluation Instances × 2 Arms × 3 Seeds = **72 Executed Benchmark Trajectories** |

### Key Takeaway
Clinical genomic variant interpretation embodies the classical **hermeneutic circle**. When evaluating whether a patient's DNA alteration causes inherited disease, individual evidence items (the *parts* — computational predictions, in-vitro assays, allele frequencies, and family pedigrees) only acquire diagnostic weight through the overarching disease mechanism (the *whole* — mode of inheritance, penetrance, transcript isoform). 

When real-world evidence arrives dynamically (new population exomes, functional assay revisions, or discovery of somatic mosaicism), standard autoregressive agents (Arm A) fail catastrophically: they re-anchor on misleading initial context, thrash across established criteria, or conflate patient-level carrier states with locus properties (falling to 25.0% accuracy on conflicting evidence). In contrast, the METIS Hermeneutic Chamber (Arm B'), powered by an explicit epistemic state $\sigma = \langle \gamma, \beta, \alpha, \kappa, H, \pi \rangle$, performs targeted surgical retraction of contradicted assumptions while preserving 93.8% of valid sub-decisions, boosting conflicting-tier diagnostic recovery by 3.0× ($75.0\%$ vs $25.0\%$).

---

## Section B: Problem Formulation & Hermeneutic Grounding

### B.1 Domain Description & Real-World Clinical Stakes
In precision medicine, next-generation sequencing identifies millions of sequence variants. Determining whether an observed sequence change is disease-causing governs life-altering clinical decisions: prophylactic mastectomy for *BRCA1/PALB2*, cardiac defibrillator implantation for *MYH7/KCNQ1/SCN5A*, or targeted CFTR potentiator therapy for *CFTR*. 

Variant classification is standardized internationally by the **ACMG/AMP 2015 criteria framework** (Richards et al., *Genet Med*), which assigns discrete clinical classifications:
1. **Pathogenic (P)**
2. **Likely Pathogenic (LP)**
3. **Variant of Uncertain Significance (VUS)**
4. **Likely Benign (LB)**
5. **Benign (B)**

### B.2 The Hermeneutic Circle in Genomic Interpretation
The relationship between molecular evidence codes and clinical diagnosis constitutes a natural hermeneutic circle:

```
          ┌────────────────────────────────────────────────────────┐
          │                  THE INTERPRETIVE WHOLE                │
          │         Global Diagnostic Classification & Mechanism   │
          │         (e.g., "Autosomal Dominant LoF Cardiomyopathy")│
          └───────────────────────────┬────────────────────────────┘
                                      │
            Interprets evidentiary    │    Revises classification when
            weight of indicators      │    contradictions refute
                                      │    core assumptions
                                      ▼
          ┌────────────────────────────────────────────────────────┐
          │                  THE EVIDENCE PARTS                    │
          │          ACMG/AMP Discrete Criteria Codes              │
          │       (PVS1, PS1-4, PM1-6, PP1-5, BA1, BS1-4, BP1-7)   │
          └────────────────────────────────────────────────────────┘
```

- **The Whole shapes the Part:** A truncating nonsense mutation is assigned Very Strong pathogenic weight ($\text{PVS1}$) only if the *whole* gene mechanism is established as Loss-of-Function. In missense-driven diseases (e.g. *MYH7*), $\text{PVS1}$ is illegal.
- **The Part reshapes the Whole:** A single subpopulation allele frequency observation $>5\%$ ($\text{BA1}$) instantly overrides all accumulated pathogenic criteria, collapsing the global diagnosis from Pathogenic to Benign.

### B.3 Epistemic Interpretive State $\sigma$ Mapping
We formalize the agent's internal state as the 6-tuple $\sigma = \langle \gamma, \beta, \alpha, \kappa, H, \pi \rangle$:

1. **$\gamma$ (Goals):** Target variant classification under specific clinical phenotype (e.g., "Classify *SCN5A* c.4372G>A for familial channelopathy; determine Brugada vs LQT3 mechanism").
2. **$\beta \in \Delta(\Omega)$ (Beliefs):** Probability distribution over the five discrete ACMG diagnostic states:
   $$\beta = [P(\text{P}), P(\text{LP}), P(\text{VUS}), P(\text{LB}), P(\text{B})]$$
3. **$\alpha$ (Assumptions):** Active working premises with explicit evidentiary justification:
   $$\alpha = \{ \alpha_1: \text{"Allele is absent in healthy population exomes (PM2)"}, \alpha_2: \text{"In-vitro patch clamp reflects physiological body temperature kinetics"} \}$$
4. **$\kappa$ (Constraints):** Regulatory combination rules and ClinGen Variant Curation Expert Panel (VCEP) specifications:
   $$\kappa = \{ K_{\text{mutex}}: \text{Disallow PM2} \cap \text{BA1}, K_{\text{gene}}: \text{Disallow PVS1 for missense in } MYH7 \}$$
5. **$H$ (Hypotheses):** Competing diagnostic readings held in parallel:
   $$H = \{ H_1: \langle \text{Pathogenic}, c_1 \rangle, H_2: \langle \text{VUS with moderate penetrance}, c_2 \rangle, H_3: \langle \text{Benign polymorphism}, c_3 \rangle \}$$
6. **$\pi$ (Plan):** Next diagnostic actions:
   $$\pi = [ a_1: \text{check\_gnomAD\_subpopulations}, a_2: \text{evaluate\_hotspot}, a_3: \text{verify\_37C\_assay} ]$$

### B.4 Admissibility Proofs (CSS v1.0 Gates G1–G4)

- **Gate G1 (Global Dependency): PASS.**  
  *Proof:* ACMG criteria combine non-linearly. Modifying a single frequency criterion (adding $\text{BA1}$) instantly overrides all accumulated pathogenic evidence ($\text{PVS1}, \text{PS1}, \dots$) and collapses the classification to Benign, regardless of independent sub-evidence.
- **Gate G2 (Dynamic Evidence): PASS.**  
  *Proof:* Evidence arrives asynchronously over patient lifetimes. Across all 12 instances, longitudinal ClinVar timelines inject four canonical perturbation classes ($P_1..P_4$) refuting early clinical assumptions.
- **Gate G3 (Revisable Interpretation): PASS.**  
  *Proof:* Early misattributions (e.g., conflating somatic CHIP mosaicism with constitutional germline mutation in *TP53*, or ambient-temperature in-vitro artifacts in *SCN5A*) represent true epistemic re-interpretations, not simple mechanical syntax errors.
- **Gate G4 (Verifiable Output): PASS.**  
  *Proof:* Evaluated via a 100% deterministic, rules-based verifier (`acmg_verifier.py`) implementing the mathematical combinatoric matrix of Richards et al. 2015 and ClinGen VCEP constraints. **Zero LLM evaluation is used in verification.**

---

## Section C: Evaluation Suite (12 Instances)

The benchmark comprises 12 authentic sequence variants with documented ClinVar longitudinal reclassifications across three difficulty tiers:

| Instance ID | Tier | Gene | cDNA / Protein Alteration | Clinical Condition | ClinVar ID | Key Evidentiary Dilemma |
|:---|:---:|:---:|:---|:---|:---:|:---|
| **biomed-001** | Easy | *CFTR* | c.1521_1523delCTT, p.Phe508del | Cystic Fibrosis | RCV000007559 | Canonical in-frame deletion; population frequency thresholding. |
| **biomed-002** | Easy | *PALB2* | c.3113G>A, p.Trp1038Ter | Hereditary Breast/Ovarian Cancer | RCV000018442 | High-penetrance nonsense null mutation with established LoF. |
| **biomed-003** | Easy | *HBB* | c.9T>C, p.His3His | Beta-Thalassemia locus | RCV000009823 | Common benign synonymous polymorphism in non-splice residue. |
| **biomed-004** | Misleading | *MSH2* | c.942+3A>T | Lynch Syndrome | RCV000003418 | Intronic variant suspected of splice defect; RNA assays proved neutral. |
| **biomed-005** | Misleading | *MYH7* | c.2155C>T, p.Arg719Trp | Hypertrophic Cardiomyopathy | RCV000025211 | Mild in-silico prediction overturned by multi-family LOD = 4.2 linkage. |
| **biomed-006** | Misleading | *LDLR* | c.1775G>A, p.Gly592Glu | Familial Hypercholesterolemia | RCV000009214 | Noisy lymphoblast assay refuted by primary fibroblast uptake assay. |
| **biomed-007** | Misleading | *BRCA1* | c.5095C>T, p.Arg1699Gln | Hereditary Breast/Ovarian Cancer | RCV000014210 | Intermediate-penetrance allele reclassified from Pathogenic to VUS. |
| **biomed-008** | Conflicting | *KCNQ1* | c.1022C>T, p.Ala341Val | Long QT Syndrome Type 1 | RCV000020141 | Discordant patch-clamp resolved by KCNE1 beta-subunit co-expression. |
| **biomed-009** | Conflicting | *TP53* | c.743G>A, p.Arg248Gln | Li-Fraumeni Syndrome / CHIP | RCV000012543 | Blood somatic CHIP mosaicism distinguished from constitutional syndrome. |
| **biomed-010** | Conflicting | *RYR1* | c.6487C>T, p.Arg2163Cys | Malignant Hyperthermia | RCV000041289 | Muscle biopsy contracture test with secondary CACNA1S confounder. |
| **biomed-011** | Easy | *MLH1* | c.350C>T, p.Thr117Met | Lynch Syndrome | RCV000003881 | ATPase ATP-binding pocket missense with complete PMS2 uncoupling. |
| **biomed-012** | Conflicting | *SCN5A* | c.4372G>A, p.Asp1458Asn | LQT3 / Brugada Arrhythmia | RCV000021948 | 22°C vs 37°C patch-clamp temperature-sensitive channelopathy kinetics. |

---

## Section D: Deterministic External Verifier Suite (G4)

The verifier suite (`verifier/acmg_verifier.py`) is a standalone, deterministic Python module with zero LLM dependencies:
1. **Constraint Checking:** Enforces mutual exclusions:
   - $\text{PM2} \cap \text{BA1} = \emptyset$ (cannot be both rare $<0.01\%$ and common $>5\%$).
   - $\text{PS3} \cap \text{BS3} = \emptyset$ (cannot claim both functional damage and functional neutral).
   - $\text{PVS1} \cap \text{BP7} = \emptyset$ (null truncation incompatible with synonymous neutral).
   - Gene-specific ClinGen VCEP disallowed rules (e.g., *MYH7* and *RYR1* disallow $\text{PVS1}$).
2. **ACMG Combinatoric Matrix:** Evaluates criterion strength counts (Very Strong, Strong, Moderate, Supporting) against the canonical ACMG combination algebra to compute the mathematical classification.
3. **Execution Characteristics:** $< 1.0\text{ ms}$ evaluation latency, 100% deterministic, zero financial cost.

---

## Section E: Experimental Protocol & Control Parameters

- **Underlying Model Backbone:** Gemini 3.5 Flash-Lite (Google GenAI API), fixed sampling parameters.
- **Evaluation Arms:**
  - **Arm A (Autoregressive Replan):** Prompt contains cumulative evidence; generates reasoning trace from scratch.
  - **Arm B' (Hermeneutic Chamber):** Maintains explicit state $\sigma$; surgically retracts only invalidated assumptions $\alpha$.
- **Random Seeds:** 3 independent random seeds ($42, 123, 999$).
- **Total Executions:** 12 instances × 2 arms × 3 seeds = **72 benchmark runs**.
- **Distance Metric $\delta$:**
  $$\delta(\sigma_t, \sigma_{t+1}) = 0.30 \cdot d_{\text{crit}} + 0.20 \cdot d_\beta + 0.20 \cdot d_\alpha + 0.10 \cdot d_\kappa + 0.10 \cdot d_H + 0.10 \cdot d_\pi$$

---

## Section F: Empirical Benchmark Results (N = 72 Runs)

### F.1 Overall Metric Summary Table
*Aggregated across all 72 experimental runs (N=36 paired evaluations):*

| Metric Category | Metric ID & Description | Arm A (Autoregressive) Mean ± Std [95% CI] | Arm B' (Hermeneutic) Mean ± Std [95% CI] | Delta (B' - A) | Statistical Significance ($p$-value, Cohen's $d$) |
|:---|:---|:---:|:---:|:---:|:---:|
| **Quality** | **Q1: Diagnostic Accuracy** | $0.5000 \pm 0.5071$ <br> $[0.3333, 0.6667]$ | **$0.7222 \pm 0.4543$** <br> $[0.5826, 0.8611]$ | **+22.2%** | $p = 0.0209$, Cohen's $d = -0.46$ (Significant) |
| | **Q2: Constraint Violations** | $0.0278 \pm 0.1667$ | $0.0833 \pm 0.2803$ | +0.056 | Invariant (Governed by verifier $\nu$) |
| | **Q3: Semantic Consistency** | $0.9722 \pm 0.1667$ | $0.9167 \pm 0.2803$ | -0.055 | High consistency across both arms |
| | **Q4: Uncertainty Calibration (Brier)** | $0.7141 \pm 0.8541$ | **$0.2860 \pm 0.5421$** | **-0.428** | **2.5× better calibrated** (lower is better) |
| **Recovery** | **R1: Mean Revision Distance $\bar{\delta}$** | $0.5605 \pm 0.0992$ <br> $[0.5283, 0.5925]$ | **$0.4432 \pm 0.1133$** <br> $[0.4069, 0.4795]$ | **-20.9%** | $p = 0.000047$, Cohen's $d = 1.10$ (Large effect) |
| | **R2: Minimal Repair Ratio ($\delta/\delta^*$)** | $0.7654 \pm 0.1404$ <br> $[0.7208, 0.8087]$ | **$0.5199 \pm 0.1348$** <br> $[0.4776, 0.5629]$ | **-32.1%** | $p < 10^{-6}$, Cohen's $d = 1.78$ (Huge effect) |
| | **R3: Preserved Valid Work** | $0.8374 \pm 0.1683$ <br> $[0.7833, 0.8931]$ | **$0.9375 \pm 0.1319$** <br> $[0.8924, 0.9778]$ | **+10.0%** | $p = 0.0027$, Cohen's $d = -0.66$ (Significant) |
| | **R4: Repeated Regression Errors** | $0.0694 \pm 0.0924$ <br> $[0.0394, 0.1019]$ | **$0.0231 \pm 0.0512$** <br> $[0.0069, 0.0394]$ | **-66.7%** | $p = 0.0127$, Cohen's $d = 0.62$ ($3\times$ error drop) |
| | **R5: Verifier Calls to Acceptance** | $5.7778 \pm 1.6232$ | $5.5000 \pm 1.3202$ | -0.278 | $p = 0.5524$ (Constrained by budget ceiling) |
| | **R6: Perturbation Recovery Rate** | $0.9653 \pm 0.1061$ | $0.9653 \pm 0.1061$ | 0.0% | Both recover valid states |
| | **R7: Recovery Latency (cycles/pert)** | $1.4444 \pm 0.4058$ | $1.3750 \pm 0.3300$ | -0.069 | Fast single-step adaptation |
| **Cost** | **C1: Agent Cycles per Run** | $5.78 \pm 1.62$ | $5.50 \pm 1.32$ | -0.28 | Balanced interaction budget |
| | **C2: Total Tokens per Run** | $4,011 \pm 1,245$ | $4,604 \pm 1,176$ | +593 | +9.0% token overhead for structured $\sigma$ |
| | **C3: Tool Invocations** | $8.0 \pm 0.0$ | $8.0 \pm 0.0$ | 0.0 | Identical environment queries |
| | **C4: Inference Cost ($USD)** | $\$0.0020 \pm 0.0006$ | $\$0.0023 \pm 0.0006$ | +$0.0003 | Ultra-cheap ($<\$0.0025$ per run) |
| | **C5: Human Interventions** | $0 \pm 0$ | $0 \pm 0$ | 0 | 100% autonomous execution |

### F.2 Breakdown by Instance Difficulty Tier

| Difficulty Tier ($N$ runs) | Arm | Q1 Diagnostic Success | Q4 Brier Score | R1 Revision Distance $\bar{\delta}$ | R2 Minimal Repair | R3 Preserved Work |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **Easy** ($n=24$) | Arm A (Baseline) | **100.0%** | 0.0001 | 0.5186 | 0.7028 | 87.7% |
| | **Arm B' (Hermeneutic)** | 83.3% | 0.1408 | **0.4272** | **0.5052** | **94.8%** |
| **Misleading** ($n=24$) | Arm A (Baseline) | 25.0% | 1.1070 | 0.5519 | 0.7511 | 94.4% |
| | **Arm B' (Hermeneutic)** | **58.3%** | **0.4079** | **0.4024** | **0.4578** | **97.9%** |
| **Conflicting** ($n=24$) | Arm A (Baseline) | 25.0% | 1.0353 | 0.6111 | 0.8423 | 69.1% |
| | **Arm B' (Hermeneutic)** | **75.0%** | **0.3093** | **0.5000** | **0.5968** | **88.5%** |

### F.3 Key Statistical Takeaways
1. **$R_1$ Revision Distance ($p < 0.0001$, Cohen's $d = 1.10$):** Hermeneutic Chamber cuts revision churn by $20.9\%$, refuting the null hypothesis of equal revision distance.
2. **$R_2$ Minimal Repair ($p < 10^{-6}$, Cohen's $d = 1.78$):** Arm B' stays $32.1\%$ closer to the minimal edit path without collateral damage.
3. **Accuracy Leaps on Hard Tiers:** While Arm A collapses on Misleading ($25\%$) and Conflicting ($25\%$) instances, Arm B' achieves **$58.3\%$ and $75.0\%$** accuracy ($2.33\times$ and $3.0\times$ gains).

---

## Section G: Qualitative Failure-Case Catalogue

### Case 1: Arm A Context Re-Anchoring on Misleading In-Silico Scores (`biomed-005`, *MYH7* p.Arg719Trp)
- **Clinical Context:** Hypertrophic cardiomyopathy missense variant with initial mild in-silico prediction (REVEL 0.52), initially called VUS.
- **Perturbation P3:** Large international family registry confirms definitive co-segregation across 5 families ($LOD = 4.2$), mandating Pathogenic via $\text{PP1\_Strong} + \text{PS4}$.
- **Arm A Failure:** Regenerating from scratch re-anchors the model on the initial REVEL score in the prompt. It hallucinates that computational predictions remain discordant, retains $\text{BP4}$, and classifies as VUS ($Q_1 = 0.0$ across all 3 seeds).
- **Arm B' Success:** Arm B' retracts only $\alpha_1$ (*"Mild in-silico score"*), adds $\text{PP1\_Strong}$, and preserves validated criteria $\text{PM1}$ (hotspot) and $\text{PM5}$, reaching Pathogenic ($Q_1 = 1.0$ across all 3 seeds).

### Case 2: Arm A Ontological Conflation of Somatic Mosaicism with Germline Syndrome (`biomed-009`, *TP53* p.Arg248Gln)
- **Clinical Context:** Somatic hotspot detected at 12% VAF in blood panel.
- **Perturbation P3:** Skin biopsy confirms 0% VAF, proving the finding is benign somatic aging (CHIP), NOT inherited Li-Fraumeni syndrome in this patient.
- **Arm A Failure:** Arm A conflates patient carrier state with variant locus properties. Hearing the patient lacks Li-Fraumeni, it discards all pathogenic evidence and calls the variant "Benign/VUS" ($Q_1 = 0.0$).
- **Arm B' Success:** Arm B' decouples patient context ($\alpha_{\text{proband}}$) from locus properties ($\alpha_{\text{locus}}$). It retracts proband criteria ($\text{PP4}$) while preserving invariant transactivation defect ($\text{PS3}$) and DNA contact hotspot ($\text{PM1}$), correctly outputting Pathogenic ($Q_1 = 1.0$).

### Case 3: Over-Conservative Minimal Pruning on Canonical Variant (`biomed-001`, *CFTR* p.Phe508del) — *Negative Result*
- **Clinical Context:** Classic Cystic Fibrosis variant. Ground truth is Pathogenic.
- **Perturbation P3:** gnomAD reports allele frequency 0.8%, invalidating $\text{PM2}$ (rarity threshold $<0.01\%$).
- **Arm A Success:** Arm A regenerates and relies on overwhelming textbook literature, outputting Pathogenic ($Q_1 = 1.0$).
- **Arm B' Failure:** Arm B' follows the pruning rule so strictly that it drops $\text{PM2}$ and downgrades functional assays to avoid double-counting, scoring "Likely Pathogenic" in 2 seeds ($Q_1 = 0.0$). This proves the necessity of bidirectional diffusion search in Phase 3.

---

## Section H: Detailed Assessment Ratings (F1–F9)

| Criterion | Name | Rating (0–5) | Justification & Empirical Evidence |
|:---:|:---|:---:|:---|
| **F1** | **Perturbation Realism** | **5 / 5** | All 4 perturbation classes (P1–P4) reconstructed directly from historical ClinVar/ClinGen expert panel reclassification timelines. |
| **F2** | **Verifier Strength** | **5 / 5** | 100% deterministic ACMG/AMP rules engine (`acmg_verifier.py`) with zero LLM judge, sub-millisecond checks, and strict constraint reporting. |
| **F3** | **Data Availability & Licensing** | **5 / 5** | Completely open public data from ClinVar, ClinGen, and gnomAD (CC0 / public domain). Millions of variants available. |
| **F4** | **Generation Scalability** | **5 / 5** | High-throughput generation: instances can be auto-synthesized from ClinVar submission differences at $>50$ instances/day. |
| **F5** | **Engineering Effort** | **4 / 5** | Full benchmark, verifier suite, and 72-trajectory runner built and validated in $< 2$ days. |
| **F6** | **Baseline Headroom** | **5 / 5** | **Ideal headroom ($50.0\%$)**: Arm A achieves 50% overall (25% on hard tiers), providing maximum discriminative separation. |
| **F7** | **Discriminative Headroom** | **5 / 5** | Massive effect sizes across $R_1$ ($d=1.10$), $R_2$ ($d=1.78$), $R_3$ ($d=-0.66$), and $Q_1$ ($+50\%$ jump on conflicting tier). |
| **F8** | **Risk & Ethics** | **4 / 5** | De-identified archival public records; zero PII or clinical harm. High real-world translation stakes. |
| **F9** | **Stakeholder Relevance & Impact** | **5 / 5** | VUS reclassification is the foremost bottleneck in genomic medicine; top-tier audience across Nature, Cell, and AI venues. |

---

## Section I: Scorecard & Final Domain Score (S1–S9)

Using the standardized CSS v1.0 weighting formula:
$$\text{Domain Score} = \left( \frac{\sum_{i=1}^9 w_i \cdot S_i}{5.0} \right) \times 100$$

| Criterion | Weight ($w_i$) | Score ($S_i$, 1–5) | Weighted Points | Rationale & Evidence |
|:---|:---:|:---:|:---:|:---|
| **S1: Structural Fit (G1–G3)** | 0.20 | **5.0** | 1.000 | Deep non-linear coupling; criteria combinatorics match the hermeneutic circle. |
| **S2: Verifier Strength (G4)** | 0.20 | **5.0** | 1.000 | 100% deterministic mathematical ACMG matrix; zero LLM judge, zero hallucination. |
| **S3: Perturbation Realism** | 0.10 | **5.0** | 0.500 | P1–P4 drawn directly from authentic ClinVar multi-year reclassifications. |
| **S4: Data Availability** | 0.10 | **5.0** | 0.500 | Millions of structured public ClinVar records licensed for research. |
| **S5: Discriminative Power** | 0.15 | **5.0** | 0.750 | $\Delta = +50\%$ on conflicting tier, $p < 0.0001$ on $\delta$, Cohen's $d = 1.78$ on minimal repair. |
| **S6: Feasibility & Simplicity** | 0.10 | **4.0** | 0.400 | Full protocol validated and executed in $< 2$ days; fast run times. |
| **S7: Risk & Safety Profile** | 0.05 | **4.0** | 0.200 | Archival public genomic data, zero live patient risk. |
| **S8: Novelty & Scientific Value** | 0.05 | **5.0** | 0.250 | First application of hermeneutic state revision to clinical genomics. |
| **S9: Generalizability & Cost** | 0.05 | **4.0** | 0.200 | Ultra-cheap ($<\$0.0025$ / run); framework extensible to oncology and pharmacology. |
| **TOTAL** | **1.00** | — | **4.800 / 5.0** | **Final Domain Score: 96.0 / 100** |

### Sensitivity Analysis
- **Equal Weights Model (Each 11.11%):** Score = **$93.3 / 100$**.
- **Perturbation Weights Model (±5% shifts):** Score = **$95.0 / 100$**.
Under all models, Domain Score exceeds 93 points, confirming robust superiority.

---

## Section J: Reproducibility Package & Artifact Verification

### J.1 Codebase Structure
```
case_studies/biomedical_variant_classification/
├── README.md                      # D1: This comprehensive CSS v1.0 report
├── summary.md                     # D6: Executive summary slide
├── results.csv                    # D5: Complete results table (72 runs, all metrics)
├── runner.py                      # D4: Experiment runner (72 benchmark runs)
├── requirements.txt               # Pinned dependencies
├── instances/                     # D2: 12 evaluation instances (JSON)
│   ├── biomed-001.json to biomed-012.json
├── verifier/                      # D3: Deterministic verifier suite
│   └── acmg_verifier.py           # Mathematical ACMG combinatorics & ClinGen constraints
├── agents/
│   ├── agent_arm_a.py             # Arm A baseline (autoregressive replanning)
│   ├── agent_arm_b.py             # Arm B' Hermeneutic Chamber agent (state σ)
│   └── tools.py                   # Registry and database tools
├── analysis/
│   ├── metrics.py                 # Tier 1/2/3 metric suite (R1-R7, Q1-Q4)
│   └── analyze_results.py         # Statistical analysis script (Bootstrap CIs, Wilcoxon)
└── runs/                          # 72 per-run execution traces (JSON)
    ├── run_arm_a_biomed-001_42.json ... run_arm_b_biomed-012_999.json
```

### J.2 Reproduction Instructions
```bash
cd case_studies/biomedical_variant_classification

# 1. Run verifier unit tests
python verifier/acmg_verifier.py

# 2. Execute full 72-run benchmark
python runner.py

# 3. Compute aggregate metrics & statistical tests
python analysis/analyze_results.py
```
