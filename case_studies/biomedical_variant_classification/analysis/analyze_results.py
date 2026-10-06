"""
Analysis script for Biomedical Genetic Variant Classification results.
Computes comprehensive statistical comparisons, bootstrap CIs, effect sizes,
breakdowns by difficulty, and formats publication-quality tables.
"""

import os
import sys
import pandas as pd
import numpy as np
from scipy import stats

CASE_STUDY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_CSV = os.path.join(CASE_STUDY_DIR, "results.csv")
OUT_SUMMARY_JSON = os.path.join(CASE_STUDY_DIR, "statistical_summary.json")

def bootstrap_ci(data, num_bootstraps=2000, ci=95):
    if len(data) == 0:
        return (0.0, 0.0)
    boot_means = []
    n = len(data)
    for _ in range(num_bootstraps):
        sample = np.random.choice(data, size=n, replace=True)
        boot_means.append(np.mean(sample))
    lower = np.percentile(boot_means, (100 - ci) / 2)
    upper = np.percentile(boot_means, 100 - (100 - ci) / 2)
    return float(lower), float(upper)

def cohens_d(x, y):
    nx = len(x)
    ny = len(y)
    dof = nx + ny - 2
    pooled_std = np.sqrt(((nx - 1) * np.std(x, ddof=1) ** 2 + (ny - 1) * np.std(y, ddof=1) ** 2) / dof)
    if pooled_std == 0:
        return 0.0
    return float((np.mean(x) - np.mean(y)) / pooled_std)

def cliffs_delta(x, y):
    n_x, n_y = len(x), len(y)
    more = 0
    less = 0
    for i in x:
        for j in y:
            if i > j:
                more += 1
            elif i < j:
                less += 1
    return float((more - less) / (n_x * n_y))

def main():
    if not os.path.exists(RESULTS_CSV):
        print(f"Error: {RESULTS_CSV} does not exist.")
        return

    df = pd.read_csv(RESULTS_CSV)
    if len(df) == 0:
        print("Results CSV is empty.")
        return

    print(f"Total rows loaded: {len(df)}")
    arms = df["arm"].unique()
    print("Arms present:", arms)

    tier1_metrics = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
    tier2_metrics = ["Q1", "Q2", "Q3", "Q4", "C1", "C2", "C3", "C4"]

    summary = {
        "overall": {},
        "by_difficulty": {},
        "hypothesis_tests": {}
    }

    # 1. Overall stats per arm
    for arm in arms:
        arm_df = df[df["arm"] == arm]
        summary["overall"][arm] = {}
        for m in tier1_metrics + tier2_metrics:
            vals = arm_df[m].dropna().values
            mean_val = float(np.mean(vals))
            std_val = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
            ci_low, ci_high = bootstrap_ci(vals)
            summary["overall"][arm][m] = {
                "mean": round(mean_val, 4),
                "std": round(std_val, 4),
                "ci_95": [round(ci_low, 4), round(ci_high, 4)]
            }

    # 2. Hypothesis testing between Arm A and Arm B
    arm_a_df = df[df["arm"] == "Arm_A_Autoregressive"].sort_values(["instance_id", "seed"])
    arm_b_df = df[df["arm"] == "Arm_B_Hermeneutic"].sort_values(["instance_id", "seed"])

    if len(arm_a_df) > 0 and len(arm_b_df) > 0 and len(arm_a_df) == len(arm_b_df):
        for m in ["R1", "R2", "R3", "R4", "R5", "Q1", "C1"]:
            vals_a = arm_a_df[m].values
            vals_b = arm_b_df[m].values
            
            d_val = cohens_d(vals_a, vals_b)
            delta_val = cliffs_delta(vals_a, vals_b)
            
            diff = vals_a - vals_b
            if np.all(diff == 0):
                w_stat, p_val = 0.0, 1.0
            else:
                try:
                    w_stat, p_val = stats.wilcoxon(vals_a, vals_b)
                    w_stat, p_val = float(w_stat), float(p_val)
                except Exception:
                    w_stat, p_val = 0.0, 1.0

            summary["hypothesis_tests"][m] = {
                "cohens_d": round(d_val, 4),
                "cliffs_delta": round(delta_val, 4),
                "wilcoxon_stat": w_stat,
                "p_value": round(p_val, 6),
                "significant_at_05": bool(p_val < 0.05)
            }

    # 3. Breakdown by difficulty
    for diff in ["easy", "misleading", "conflicting"]:
        summary["by_difficulty"][diff] = {}
        for arm in arms:
            sub_df = df[(df["difficulty"] == diff) & (df["arm"] == arm)]
            summary["by_difficulty"][diff][arm] = {}
            for m in ["R1", "R3", "R5", "Q1"]:
                vals = sub_df[m].dropna().values
                summary["by_difficulty"][diff][arm][m] = {
                    "mean": round(float(np.mean(vals)), 4) if len(vals) else 0.0,
                    "std": round(float(np.std(vals, ddof=1)), 4) if len(vals) > 1 else 0.0
                }

    import json
    with open(OUT_SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n================== AGGREGATED METRICS SUMMARY ==================")
    print(f"{'Metric':<6} | {'Arm A (Autoregressive)':<24} | {'Arm B (Hermeneutic)':<24} | {'Effect (Cohen d)':<16} | {'p-value':<10}")
    print("-" * 90)
    for m in ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "Q1", "Q2", "Q3", "Q4", "C1", "C2", "C4"]:
        a_stats = summary["overall"].get("Arm_A_Autoregressive", {}).get(m, {})
        b_stats = summary["overall"].get("Arm_B_Hermeneutic", {}).get(m, {})
        a_str = f"{a_stats.get('mean', 0):.4f} ± {a_stats.get('std', 0):.4f}"
        b_str = f"{b_stats.get('mean', 0):.4f} ± {b_stats.get('std', 0):.4f}"
        
        test = summary["hypothesis_tests"].get(m, {})
        d_str = f"d = {test.get('cohens_d', 0):.2f}" if test else "-"
        p_str = f"{test.get('p_value', 1.0):.4f}" if test else "-"
        print(f"{m:<6} | {a_str:<24} | {b_str:<24} | {d_str:<16} | {p_str:<10}")

if __name__ == "__main__":
    main()
