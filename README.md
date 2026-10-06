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
    ├── <teammate_domain_1>/       # Placeholder for Candidate Domain 2
    └── <teammate_domain_2>/       # Placeholder for Candidate Domain 3
```

---

## Domain Overview: Cybersecurity Incident Response (Top Candidate)

- **Domain Score:** **94.0 / 100** (Recommendation: **ACCEPT**)
- **Empirical Runs:** 72 runs (12 instances × 2 arms × 3 seeds)
- **Key Findings:**
  - **Task Success (Q1):** Arm B' achieves **100.0%** vs Arm A **25.0%** ($p < 10^{-4}$, Cohen's $d = 1.71$).
  - **Investigation Latency (C5):** Arm B' cuts investigation time by **58.3%** ($11.99\text{ s}$ vs $28.77\text{ s}$, $p < 10^{-4}$).
  - **Operational Containment (MTTC):** Arm B' achieves **89.1% faster breach containment** ($4.17\text{ hrs}$ vs $38.30\text{ hrs}$, Cohen's $d = -2.05$).
  - **Token Consumption (C2):** Arm B' uses **53.3% fewer tokens** (6,300 vs 13,500 tokens).
  - **Knowledge Base:** Direct inference on official MITRE ATT&CK Enterprise STIX 2.1 knowledge base (26,086 STIX objects).

### Quickstart for Cybersecurity IR

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
