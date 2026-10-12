"""
Generate Master Holistic Dashboard & Radar Chart for Contrastive Study
========================================================================
LLaDA (Diffusion LLM) vs FARA (Autoregressive LLM) on METIS Cybersecurity IR
"""

import os
import csv
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

OUTPUT_DIR = r"c:\Users\ASUS\Downloads\METIS Images\case_studies\cybersecurity_ir\figures_contrastive"
os.makedirs(OUTPUT_DIR, exist_ok=True)

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.size"] = 10

def load_data(csv_path):
    with open(csv_path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

llada_rows = load_data(r"c:\Users\ASUS\Downloads\METIS Images\case_studies\cybersecurity_ir\results.csv")
fara_rows = load_data(r"c:\Users\ASUS\Downloads\METIS Images\case_studies\cybersecurity_ir\results_fara.csv")

def aggregate(rows):
    res = defaultdict(lambda: defaultdict(list))
    for r in rows:
        arm = r["arm"]
        diff = r["difficulty"]
        for k, v in r.items():
            try:
                res[(arm, diff)][k].append(float(v))
                res[(arm, "all")][k].append(float(v))
            except (ValueError, TypeError):
                pass
    return res

l = aggregate(llada_rows)
f = aggregate(fara_rows)

tiers = ["easy", "misleading", "conflicting"]
tier_labels = ["Easy", "Misleading", "Conflicting", "Overall"]

# Palette
c_llada_a = "#ef4444"  # Red
c_llada_b = "#10b981"  # Emerald Green
c_fara_a  = "#f97316"  # Orange
c_fara_b  = "#0284c7"  # Sky Blue

# ==============================================================================
# FIGURE 1: 6-PANEL HOLISTIC CONTRASTIVE DASHBOARD
# ==============================================================================
fig, axs = plt.subplots(2, 3, figsize=(18, 11))
fig.suptitle("METIS Contrastive Benchmark: Diffusion (LLaDA) vs Autoregressive (FARA)", fontsize=16, fontweight="bold", y=0.98)

# Panel 1: Q1 Task Success by Tier
ax = axs[0, 0]
x = np.arange(len(tier_labels))
width = 0.20

l_a_q1 = [np.mean(l[("arm_a", d)]["q1_task_success"]) * 100 for d in tiers] + [np.mean(l[("arm_a", "all")]["q1_task_success"]) * 100]
l_b_q1 = [np.mean(l[("arm_b", d)]["q1_task_success"]) * 100 for d in tiers] + [np.mean(l[("arm_b", "all")]["q1_task_success"]) * 100]
f_a_q1 = [np.mean(f[("arm_a", d)]["q1_task_success"]) * 100 for d in tiers] + [np.mean(f[("arm_a", "all")]["q1_task_success"]) * 100]
f_b_q1 = [np.mean(f[("arm_b", d)]["q1_task_success"]) * 100 for d in tiers] + [np.mean(f[("arm_b", "all")]["q1_task_success"]) * 100]

r1 = ax.bar(x - 1.5*width, l_a_q1, width, label="LLaDA: Arm A", color=c_llada_a, alpha=0.85)
r2 = ax.bar(x - 0.5*width, l_b_q1, width, label="LLaDA: Arm B'", color=c_llada_b, alpha=0.85)
r3 = ax.bar(x + 0.5*width, f_a_q1, width, label="FARA: Arm A", color=c_fara_a, alpha=0.85)
r4 = ax.bar(x + 1.5*width, f_b_q1, width, label="FARA: Arm B'", color=c_fara_b, alpha=0.85)

ax.set_ylabel("Task Success Rate (%)", fontweight="bold")
ax.set_title("(A) Q1: Task Success Rate by Difficulty Tier", fontweight="bold", pad=10)
ax.set_xticks(x)
ax.set_xticklabels(tier_labels, fontweight="bold")
ax.set_ylim(0, 35)
ax.legend(frameon=True, fontsize=9, loc="upper right")

# Panel 2: Q2 Solution Quality by Tier
ax = axs[0, 1]
l_a_q2 = [np.mean(l[("arm_a", d)]["q2_solution_quality"]) for d in tiers] + [np.mean(l[("arm_a", "all")]["q2_solution_quality"])]
l_b_q2 = [np.mean(l[("arm_b", d)]["q2_solution_quality"]) for d in tiers] + [np.mean(l[("arm_b", "all")]["q2_solution_quality"])]
f_a_q2 = [np.mean(f[("arm_a", d)]["q2_solution_quality"]) for d in tiers] + [np.mean(f[("arm_a", "all")]["q2_solution_quality"])]
f_b_q2 = [np.mean(f[("arm_b", d)]["q2_solution_quality"]) for d in tiers] + [np.mean(f[("arm_b", "all")]["q2_solution_quality"])]

ax.bar(x - 1.5*width, l_a_q2, width, label="LLaDA: Arm A", color=c_llada_a, alpha=0.85)
ax.bar(x - 0.5*width, l_b_q2, width, label="LLaDA: Arm B'", color=c_llada_b, alpha=0.85)
ax.bar(x + 0.5*width, f_a_q2, width, label="FARA: Arm A", color=c_fara_a, alpha=0.85)
ax.bar(x + 1.5*width, f_b_q2, width, label="FARA: Arm B'", color=c_fara_b, alpha=0.85)

ax.set_ylabel("Composite Quality Score in [0, 1]", fontweight="bold")
ax.set_title("(B) Q2: Investigation Solution Quality", fontweight="bold", pad=10)
ax.set_xticks(x)
ax.set_xticklabels(tier_labels, fontweight="bold")
ax.set_ylim(0, 1.05)
ax.legend(frameon=True, fontsize=9, loc="upper right")

# Panel 3: R1 Revision Distance Trajectory
ax = axs[0, 2]
p_steps = ["P1 (Constraint)", "P2 (Dependency)", "P3 (Assumption)", "P4 (Setting)"]
p_keys = ["r1_delta_p1", "r1_delta_p2", "r1_delta_p3", "r1_delta_p4"]

la_delta = [np.mean(l[("arm_a", "all")][k]) for k in p_keys]
lb_delta = [np.mean(l[("arm_b", "all")][k]) for k in p_keys]
fa_delta = [np.mean(f[("arm_a", "all")][k]) for k in p_keys]
fb_delta = [np.mean(f[("arm_b", "all")][k]) for k in p_keys]

ax.plot(p_steps, la_delta, marker="s", color=c_llada_a, linewidth=2.2, label="LLaDA: Arm A")
ax.plot(p_steps, lb_delta, marker="o", color=c_llada_b, linewidth=2.2, label="LLaDA: Arm B'")
ax.plot(p_steps, fa_delta, marker="^", linestyle="--", color=c_fara_a, linewidth=2.2, label="FARA: Arm A")
ax.plot(p_steps, fb_delta, marker="d", linestyle="--", color=c_fara_b, linewidth=2.2, label="FARA: Arm B'")

ax.set_ylabel("Revision Distance delta", fontweight="bold")
ax.set_title("(C) R1: State Revision Trajectory Across Perturbations", fontweight="bold", pad=10)
ax.set_ylim(-0.02, 0.55)
ax.legend(frameon=True, fontsize=9, loc="upper right")

# Panel 4: R2 Work Preservation
ax = axs[1, 0]
categories = ["LLaDA: Arm A", "LLaDA: Arm B'", "FARA: Arm A", "FARA: Arm B'"]
r2_vals = [
    np.mean(l[("arm_a", "all")]["r2_mean_work_preservation"]),
    np.mean(l[("arm_b", "all")]["r2_mean_work_preservation"]),
    np.mean(f[("arm_a", "all")]["r2_mean_work_preservation"]),
    np.mean(f[("arm_b", "all")]["r2_mean_work_preservation"]),
]
colors_cat = [c_llada_a, c_llada_b, c_fara_a, c_fara_b]

b_r2 = ax.bar(categories, r2_vals, color=colors_cat, alpha=0.85, width=0.50)
ax.set_ylabel("Work Preservation Rate in [0, 1]", fontweight="bold")
ax.set_title("(D) R2: Work Preservation Under Perturbation", fontweight="bold", pad=10)
ax.set_ylim(0.85, 1.05)
for bar in b_r2:
    h = bar.get_height()
    ax.annotate(f"{h:.3f}", xy=(bar.get_x() + bar.get_width()/2, h),
                xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=10, fontweight="bold")

# Panel 5: C2 Token Consumption
ax = axs[1, 1]
c2_vals = [
    np.mean(l[("arm_a", "all")]["c2_total_tokens"]),
    np.mean(l[("arm_b", "all")]["c2_total_tokens"]),
    np.mean(f[("arm_a", "all")]["c2_total_tokens"]),
    np.mean(f[("arm_b", "all")]["c2_total_tokens"]),
]
b_c2 = ax.bar(categories, c2_vals, color=colors_cat, alpha=0.85, width=0.50)
ax.set_ylabel("Total Tokens Consumed", fontweight="bold")
ax.set_title("(E) C2: Resource Efficiency (Total Tokens)", fontweight="bold", pad=10)
ax.set_ylim(0, max(c2_vals) * 1.25)
for bar in b_c2:
    h = bar.get_height()
    ax.annotate(f"{h:,.0f}", xy=(bar.get_x() + bar.get_width()/2, h),
                xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=10, fontweight="bold")

# Panel 6: C5 Execution Latency
ax = axs[1, 2]
c5_vals = [
    np.mean(l[("arm_a", "all")]["c5_time_taken_s"]),
    np.mean(l[("arm_b", "all")]["c5_time_taken_s"]),
    np.mean(f[("arm_a", "all")]["c5_time_taken_s"]),
    np.mean(f[("arm_b", "all")]["c5_time_taken_s"]),
]
b_c5 = ax.bar(categories, c5_vals, color=colors_cat, alpha=0.85, width=0.50)
ax.set_ylabel("Investigation Latency (Seconds)", fontweight="bold")
ax.set_title("(F) C5: End-to-End Latency per Investigation", fontweight="bold", pad=10)
ax.set_ylim(0, max(c5_vals) * 1.25)
for bar in b_c5:
    h = bar.get_height()
    ax.annotate(f"{h:.1f}s", xy=(bar.get_x() + bar.get_width()/2, h),
                xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=10, fontweight="bold")

plt.tight_layout()
dashboard_path = os.path.join(OUTPUT_DIR, "holistic_contrastive_dashboard.png")
plt.savefig(dashboard_path, dpi=300)
plt.close()
print(f"Saved {dashboard_path}")


# ==============================================================================
# FIGURE 2: RADAR CHART ACROSS 6 EVALUATION AXES
# ==============================================================================
labels = [
    "Q1 Task Success",
    "Q2 Solution Quality",
    "R1 Stability (1-RevDist)",
    "R2 Work Preservation",
    "Token Efficiency",
    "Inference Speed"
]
num_vars = len(labels)
angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
angles += angles[:1]

def normalize_scores(q1, q2, r1, r2, c2, c5):
    s_q1 = q1 / 0.35
    s_q2 = q2 / 1.0
    s_r1 = max(0.0, 1.0 - r1)
    s_r2 = r2
    s_c2 = max(0.1, 1.0 - (c2 / 10000.0))
    s_c5 = max(0.1, 1.0 - (c5 / 60.0))
    vals = [s_q1, s_q2, s_r1, s_r2, s_c2, s_c5]
    vals += vals[:1]
    return vals

score_la = normalize_scores(
    np.mean(l[("arm_a", "all")]["q1_task_success"]),
    np.mean(l[("arm_a", "all")]["q2_solution_quality"]),
    np.mean(l[("arm_a", "all")]["r1_mean_revision_distance"]),
    np.mean(l[("arm_a", "all")]["r2_mean_work_preservation"]),
    np.mean(l[("arm_a", "all")]["c2_total_tokens"]),
    np.mean(l[("arm_a", "all")]["c5_time_taken_s"]),
)

score_lb = normalize_scores(
    np.mean(l[("arm_b", "all")]["q1_task_success"]),
    np.mean(l[("arm_b", "all")]["q2_solution_quality"]),
    np.mean(l[("arm_b", "all")]["r1_mean_revision_distance"]),
    np.mean(l[("arm_b", "all")]["r2_mean_work_preservation"]),
    np.mean(l[("arm_b", "all")]["c2_total_tokens"]),
    np.mean(l[("arm_b", "all")]["c5_time_taken_s"]),
)

score_fa = normalize_scores(
    np.mean(f[("arm_a", "all")]["q1_task_success"]),
    np.mean(f[("arm_a", "all")]["q2_solution_quality"]),
    np.mean(f[("arm_a", "all")]["r1_mean_revision_distance"]),
    np.mean(f[("arm_a", "all")]["r2_mean_work_preservation"]),
    np.mean(f[("arm_a", "all")]["c2_total_tokens"]),
    np.mean(f[("arm_a", "all")]["c5_time_taken_s"]),
)

score_fb = normalize_scores(
    np.mean(f[("arm_b", "all")]["q1_task_success"]),
    np.mean(f[("arm_b", "all")]["q2_solution_quality"]),
    np.mean(f[("arm_b", "all")]["r1_mean_revision_distance"]),
    np.mean(f[("arm_b", "all")]["r2_mean_work_preservation"]),
    np.mean(f[("arm_b", "all")]["c2_total_tokens"]),
    np.mean(f[("arm_b", "all")]["c5_time_taken_s"]),
)

fig, ax = plt.subplots(figsize=(8.5, 8.5), subplot_kw=dict(polar=True))
ax.set_theta_offset(np.pi / 2)
ax.set_theta_direction(-1)

ax.set_xticks(angles[:-1])
ax.set_xticklabels(labels, fontweight="bold", fontsize=10)

ax.plot(angles, score_la, color=c_llada_a, linewidth=2, linestyle=":", label="LLaDA: Arm A (Replan)")
ax.fill(angles, score_la, color=c_llada_a, alpha=0.08)

ax.plot(angles, score_lb, color=c_llada_b, linewidth=2.5, linestyle="-", label="LLaDA: Arm B' (Hermeneutic)")
ax.fill(angles, score_lb, color=c_llada_b, alpha=0.18)

ax.plot(angles, score_fa, color=c_fara_a, linewidth=2, linestyle="--", label="FARA: Arm A (Replan)")
ax.fill(angles, score_fa, color=c_fara_a, alpha=0.08)

ax.plot(angles, score_fb, color=c_fara_b, linewidth=2.5, linestyle="-.", label="FARA: Arm B' (Hermeneutic)")
ax.fill(angles, score_fb, color=c_fara_b, alpha=0.18)

ax.set_ylim(0, 1.05)
ax.set_title("Holistic Multi-Attribute Evaluation Across Model Paradigms", fontsize=13, fontweight="bold", pad=25)
ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.12), frameon=True, fontsize=10)

plt.tight_layout()
radar_path = os.path.join(OUTPUT_DIR, "holistic_radar_evaluation.png")
plt.savefig(radar_path, dpi=300)
plt.close()
print(f"Saved {radar_path}")

print("Holistic figures successfully generated!")
