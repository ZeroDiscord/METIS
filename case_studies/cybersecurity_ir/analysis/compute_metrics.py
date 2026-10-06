"""
Compute METIS Standard Metrics (CSS v1.0)
=========================================
Aggregates R1-R7, Q1-Q4, and C1-C5 across difficulty tiers and overall.
Generates tabular summaries for the case study report.
"""

import csv
from collections import defaultdict
import numpy as np


def load_results(csv_path: str = "results.csv"):
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def summarize():
    rows = load_results()

    metrics = [
        "q1_task_success",
        "q2_solution_quality",
        "q3_constraint_satisfaction",
        "q4_evidence_coverage",
        "r1_mean_revision_distance",
        "r1_delta_p1",
        "r1_delta_p2",
        "r1_delta_p3",
        "r1_delta_p4",
        "r2_mean_work_preservation",
        "r2_work_pres_p1",
        "r2_work_pres_p2",
        "r2_work_pres_p3",
        "r2_work_pres_p4",
        "r3_recovery_rate",
        "r5_monotonicity",
        "r6_cascade_efficiency",
        "c1_llm_calls",
        "c2_total_tokens",
        "c3_verifier_calls",
        "c5_runtime_ms",
        "c5_time_taken_s",
        "time_p1_s",
        "time_p2_s",
        "time_p3_s",
        "time_p4_s",
        "mttc_hours",
    ]

    # Group by (arm, difficulty) and arm overall
    groups = defaultdict(lambda: defaultdict(list))
    overall = defaultdict(lambda: defaultdict(list))

    for r in rows:
        arm = r["arm"]
        diff = r["difficulty"]
        for m in metrics:
            val = float(r[m])
            groups[(arm, diff)][m].append(val)
            overall[arm][m].append(val)

    print("=" * 90)
    print(f"{'METIS METRIC SUMMARY TABLE (CSS v1.0 Standard)':^90}")
    print("=" * 90)
    col_b_hdr = "Arm B' (Mean +/- SD)"
    print(f"{'Metric':<28} | {'Arm A (Mean +/- SD)':<28} | {col_b_hdr:<28}")
    print("-" * 90)

    for m in metrics:
        vals_a = overall["arm_a"][m]
        vals_b = overall["arm_b"][m]
        mean_a, sd_a = np.mean(vals_a), np.std(vals_a)
        mean_b, sd_b = np.mean(vals_b), np.std(vals_b)
        print(f"{m:<28} | {mean_a:8.3f} +/- {sd_a:6.3f}         | {mean_b:8.3f} +/- {sd_b:6.3f}")

    print("\n" + "=" * 90)
    print(f"{'BREAKDOWN BY DIFFICULTY TIER':^90}")
    print(f"{'Difficulty':<12} | {'Arm':<6} | {'Q1 (Success)':<13} | {'Q2 (Quality)':<13} | {'R1 (Delta)':<12} | {'Tokens':<8} | {'Time (s)':<9} | {'MTTC (h)':<9}")
    print("-" * 105)

    for diff in ["easy", "misleading", "conflicting"]:
        for arm in ["arm_a", "arm_b"]:
            q1 = np.mean(groups[(arm, diff)]["q1_task_success"])
            q2 = np.mean(groups[(arm, diff)]["q2_solution_quality"])
            r1 = np.mean(groups[(arm, diff)]["r1_mean_revision_distance"])
            tok = np.mean(groups[(arm, diff)]["c2_total_tokens"])
            t_sec = np.mean(groups[(arm, diff)]["c5_time_taken_s"])
            mttc = np.mean(groups[(arm, diff)]["mttc_hours"])
            print(f"{diff:<12} | {arm:<6} | {q1:13.3f} | {q2:13.3f} | {r1:12.3f} | {tok:8.0f} | {t_sec:9.2f} | {mttc:9.2f}")
        print("-" * 105)


if __name__ == "__main__":
    summarize()
