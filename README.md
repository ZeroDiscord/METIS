# METIS: Hermeneutic AI Benchmark & Domain Selection

This repository hosts candidate domain studies for **Phase 2 Problem Setting Selection** of the **METIS** benchmark (under the Case Study Standard, CSS v1.0).

---

## Repository Structure

Each candidate experiment sits in its own isolated subfolder under `case_studies/` so teammates can independently develop and push their experimental evaluations:

```
METIS/
├── README.md                      # Repository overview & structure guidelines
├── .gitignore
├── images/                        # METIS synopsis diagrams & figures
└── case_studies/
    ├── biomedical_variant_classification/ # [COMPLETED] Biomedical Genetic Variant Classification (ACMG/AMP)
    │   ├── README.md              # Full CSS v1.0 evaluation report (Ratings F1-F9, S1-S9)
    │   ├── summary.md             # D6 Executive summary slide
    │   ├── runner.py              # Experiment runner (72 benchmark runs)
    │   ├── results.csv            # Empirical results across all 72 runs
    │   ├── requirements.txt       # Pinned dependencies
    │   ├── agents/                # Arm A (baseline) and Arm B' (hermeneutic agent)
    │   ├── analysis/              # Metrics, statistical tests (Bootstrap CIs, Wilcoxon)
    │   ├── instances/             # 12 evaluation instances (JSON)
    │   ├── runs/                  # 72 per-run execution traces (JSON)
    │   └── verifier/              # 100% deterministic ACMG/AMP rules engine (zero LLM)
    │
    ├── cybersecurity_ir/          # [COMPLETED] Cybersecurity Incident Response & Threat Attribution
    │   ├── README.md              # Full CSS v1.0 evaluation report
    │   ├── summary.md             # D6 Executive summary slide
    │   ├── runner.py              # Experiment runner (72 benchmark runs)
    │   ├── results.csv            # Empirical results across all runs
    │   ├── requirements.txt       # Pinned dependencies
    │   ├── agents/                # Arm A (baseline) and Arm B' (hermeneutic agent)
    │   ├── analysis/              # Metrics, statistical tests, and plots
    │   ├── data/                  # Official MITRE ATT&CK STIX & Sigma rules
    │   ├── figures/               # High-res publication plots
    │   ├── instances/             # 12 evaluation instances (YAML)
    │   ├── runs/                  # 72 per-run execution traces (JSONL)
    │   └── verifier/              # Deterministic G4-compliant verifier suite
    │
    └── <teammate_domain>/         # Placeholder for Candidate Domain 3
```

---

## Domain Comparisons & Overview

| Candidate Domain | Category | Domain Score | G1–G4 Gates | Benchmark Runs | Key Result | Recommendation |
|:---|:---|:---:|:---:|:---:|:---|:---:|
| **Biomedical Variant Classification** | Clinical Genomics | **96.0 / 100** | **PASS (4/4)** | 72 runs (12 inst × 2 arms × 3 seeds) | **-20.9% revision distance** ($p < 10^{-4}$), **+50% accuracy on conflicting tier** | **ACCEPT (Top-Ranked)** |
| **Cybersecurity Incident Response** | Systems / Security | **94.0 / 100** | **PASS (4/4)** | 72 runs (12 inst × 2 arms × 3 seeds) | **+75.0% task success**, **53.3% token savings** | **ACCEPT** |

---

### Quickstart: Biomedical Variant Classification

```bash
cd case_studies/biomedical_variant_classification

# 1. Run deterministic verifier tests
python verifier/acmg_verifier.py

# 2. Execute full 72-run benchmark
python runner.py

# 3. Compute metrics & statistical tests
python analysis/analyze_results.py
```

### Quickstart: Cybersecurity IR

```bash
cd case_studies/cybersecurity_ir

# 1. Run verifier unit tests
python -m unittest verifier/tests/test_verifier.py

# 2. Execute benchmark runner (72 runs)
python runner.py

# 3. Compute metrics & statistical tests
python analysis/compute_metrics.py
python analysis/statistical_tests.py

# 4. Generate figures
python analysis/plots.py
```

---

## Instructions for Teammates Adding New Domains

When adding a new candidate domain:
1. Create a new directory under `case_studies/<domain_name>/`.
2. Follow the standard CSS v1.0 layout (`instances/`, `verifier/`, `agents/`, `runner.py`, `results.csv`, `README.md`).
3. Ensure the verifier is 100% deterministic (zero LLM, G4-compliant).
4. Run all 72 executions (12 instances × 2 arms × 3 seeds).
5. Document ratings F1–F9, Scorecard S1–S9, and final Domain Score in your domain's `README.md`.

