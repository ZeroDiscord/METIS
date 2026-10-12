"""
Generate Contrastive Figures: LLaDA (Diffusion) vs FARA (Autoregressive)
========================================================================
Outputs publication-ready comparison charts into figures_contrastive/
"""

import os
import csv
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

OUTPUT_DIR = "figures_contrastive"
os.makedirs(OUTPUT_DIR, exist_ok=True)

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.size"] = 11

def load_rows(csv_path):
    with open(csv_path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

llada_rows = load_rows("results.csv")
fara_rows = load_rows("results_fara.csv")

def aggregate(rows):
    overall = defaultdict(lambda: defaultdict(list))
    tier = defaultdict(lambda: defaultdict(list))
    for r in rows:
        arm = r["arm"]
        diff = r["difficulty"]
        for k, v in r.items():
            try:
                val = float(v)
                overall[arm][k].append(val)
                tier[(arm, diff)][k].append(val)
            except (ValueError, TypeError):
                pass
    return overall, tier

ov_llada, tr_llada = aggregate(llada_rows)
ov_fara, tr_fara = aggregate(fara_rows)

# ── 1. Q1 Task Success & Q2 Solution Quality Contrast ────────────────────────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

categories = [
    "LLaDA (Arm A)", "LLaDA (Arm B')",
    "FARA (Arm A)", "FARA (Arm B')"
]

q1_vals = [
    np.mean(ov_llada["arm_a"]["q1_task_success"]) * 100,
    np.mean(ov_llada["arm_b"]["q1_task_success"]) * 100,
    np.mean(ov_fara["arm_a"]["q1_task_success"]) * 100,
    np.mean(ov_fara["arm_b"]["q1_task_success"]) * 100,
]

q2_vals = [
    np.mean(ov_llada["arm_a"]["q2_solution_quality"]),
    np.mean(ov_llada["arm_b"]["q2_solution_quality"]),
    np.mean(ov_fara["arm_a"]["q2_solution_quality"]),
    np.mean(ov_fara["arm_b"]["q2_solution_quality"]),
]

colors = ["#f87171", "#34d399", "#fb923c", "#38bdf8"]

# Subplot 1: Q1 Task Success
bars1 = ax1.bar(categories, q1_vals, color=colors, alpha=0.88, width=0.55)
ax1.set_ylabel("Task Success Rate (%)", fontsize=11, fontweight="bold")
ax1.set_title("Q1: Task Success Rate (Contrastive)", fontsize=12, fontweight="bold")
ax1.set_ylim(0, 35)
ax1.tick_params(axis="x", rotation=15)
for b in bars1:
    h = b.get_height()
    ax1.annotate(f"{h:.1f}%", xy=(b.get_x() + b.get_width() / 2, h),
                 xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=10, fontweight="bold")

# Subplot 2: Q2 Solution Quality
bars2 = ax2.bar(categories, q2_vals, color=colors, alpha=0.88, width=0.55)
ax2.set_ylabel("Composite Quality Score in [0, 1]", fontsize=11, fontweight="bold")
ax2.set_title("Q2: Investigation Solution Quality (Contrastive)", fontsize=12, fontweight="bold")
ax2.set_ylim(0, 0.85)
ax2.tick_params(axis="x", rotation=15)
for b in bars2:
    h = b.get_height()
    ax2.annotate(f"{h:.3f}", xy=(b.get_x() + b.get_width() / 2, h),
                 xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=10, fontweight="bold")

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "contrastive_q1_q2_comparison.png"), dpi=300)
plt.close()
print(f"Saved {OUTPUT_DIR}/contrastive_q1_q2_comparison.png")

# ── 2. Latency & Token Efficiency Contrast ──────────────────────────────────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

latency_vals = [
    np.mean(ov_llada["arm_a"]["c5_time_taken_s"]),
    np.mean(ov_llada["arm_b"]["c5_time_taken_s"]),
    np.mean(ov_fara["arm_a"]["c5_time_taken_s"]),
    np.mean(ov_fara["arm_b"]["c5_time_taken_s"]),
]

token_vals = [
    np.mean(ov_llada["arm_a"]["c2_total_tokens"]),
    np.mean(ov_llada["arm_b"]["c2_total_tokens"]),
    np.mean(ov_fara["arm_a"]["c2_total_tokens"]),
    np.mean(ov_fara["arm_b"]["c2_total_tokens"]),
]

bars1 = ax1.bar(categories, latency_vals, color=colors, alpha=0.88, width=0.55)
ax1.set_ylabel("Execution Time (Seconds)", fontsize=11, fontweight="bold")
ax1.set_title("C5: Investigation Execution Latency", fontsize=12, fontweight="bold")
ax1.set_ylim(0, max(latency_vals) * 1.25)
ax1.tick_params(axis="x", rotation=15)
for b in bars1:
    h = b.get_height()
    ax1.annotate(f"{h:.1f}s", xy=(b.get_x() + b.get_width() / 2, h),
                 xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=10, fontweight="bold")

bars2 = ax2.bar(categories, token_vals, color=colors, alpha=0.88, width=0.55)
ax2.set_ylabel("Total Tokens Consumed", fontsize=11, fontweight="bold")
ax2.set_title("C2: Token Consumption", fontsize=12, fontweight="bold")
ax2.set_ylim(0, max(token_vals) * 1.25)
ax2.tick_params(axis="x", rotation=15)
for b in bars2:
    h = b.get_height()
    ax2.annotate(f"{h:,.0f}", xy=(b.get_x() + b.get_width() / 2, h),
                 xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=10, fontweight="bold")

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "contrastive_efficiency_comparison.png"), dpi=300)
plt.close()
print(f"Saved {OUTPUT_DIR}/contrastive_efficiency_comparison.png")

# ── 3. R1 Revision Distance Trajectories ────────────────────────────────────
p_steps = ["P1 (Constraint)", "P2 (Dependency)", "P3 (Assumption)", "P4 (Setting)"]
p_keys = ["r1_delta_p1", "r1_delta_p2", "r1_delta_p3", "r1_delta_p4"]

llada_a_delta = [np.mean(ov_llada["arm_a"][k]) for k in p_keys]
llada_b_delta = [np.mean(ov_llada["arm_b"][k]) for k in p_keys]
fara_a_delta = [np.mean(ov_fara["arm_a"][k]) for k in p_keys]
fara_b_delta = [np.mean(ov_fara["arm_b"][k]) for k in p_keys]

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(p_steps, llada_a_delta, marker="s", color="#ef4444", linewidth=2.2, label="LLaDA: Arm A (Full Replan)")
ax.plot(p_steps, llada_b_delta, marker="o", color="#10b981", linewidth=2.2, label="LLaDA: Arm B' (Hermeneutic σ)")
ax.plot(p_steps, fara_a_delta, marker="^", linestyle="--", color="#f97316", linewidth=2.2, label="FARA: Arm A (Full Replan)")
ax.plot(p_steps, fara_b_delta, marker="d", linestyle="--", color="#0284c7", linewidth=2.2, label="FARA: Arm B' (Hermeneutic σ)")

ax.set_ylabel("Revision Distance δ in [0, 1]", fontsize=12, fontweight="bold")
ax.set_title("R1: Revision Distance Trajectories (LLaDA Diffusion vs FARA Autoregressive)", fontsize=12, fontweight="bold", pad=15)
ax.set_ylim(-0.02, 0.6)
ax.legend(frameon=True, loc="upper right")

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "contrastive_r1_trajectory.png"), dpi=300)
plt.close()
print(f"Saved {OUTPUT_DIR}/contrastive_r1_trajectory.png")

print("All contrastive figures generated successfully!")
