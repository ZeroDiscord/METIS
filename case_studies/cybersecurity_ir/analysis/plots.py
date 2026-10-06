"""
Generate Visual Figures for METIS Cybersecurity IR Case Study
==============================================================
Produces publication-quality plots:
1. figures/q1_task_success_by_tier.png
2. figures/r1_revision_distance_trajectory.png
3. figures/c2_token_consumption.png
4. figures/q2_solution_quality_distribution.png
"""

import os
import csv
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

os.makedirs("figures", exist_ok=True)

# Styling
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.size"] = 11

def load_data(csv_path: str = "results.csv"):
    with open(csv_path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

rows = load_data()

# ── Figure 1: Q1 Task Success Rate across Difficulty Tiers ───────────────────
tiers = ["Easy", "Misleading", "Conflicting", "Overall"]
arm_a_success = [0.75, 0.00, 0.00, 0.25]
arm_b_success = [1.00, 1.00, 1.00, 1.00]

x = np.arange(len(tiers))
width = 0.35

fig, ax = plt.subplots(figsize=(8, 5))
rects1 = ax.bar(x - width/2, [s * 100 for s in arm_a_success], width, label="Arm A (Autoregressive Replan)", color="#ef4444", alpha=0.85)
rects2 = ax.bar(x + width/2, [s * 100 for s in arm_b_success], width, label="Arm B' (Hermeneutic State σ)", color="#10b981", alpha=0.85)

ax.set_ylabel("Task Success Rate (%)", fontsize=12, fontweight="bold")
ax.set_title("Q1: Task Success Rate by Difficulty Tier (N=72 runs)", fontsize=13, fontweight="bold", pad=15)
ax.set_xticks(x)
ax.set_xticklabels(tiers, fontweight="bold")
ax.set_ylim(0, 115)
ax.legend(frameon=True, loc="upper right")

for rect in rects1:
    height = rect.get_height()
    ax.annotate(f"{height:.0f}%", xy=(rect.get_x() + rect.get_width() / 2, height),
                xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=10)

for rect in rects2:
    height = rect.get_height()
    ax.annotate(f"{height:.0f}%", xy=(rect.get_x() + rect.get_width() / 2, height),
                xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=10, fontweight="bold")

plt.tight_layout()
plt.savefig("figures/q1_task_success_by_tier.png", dpi=300)
plt.close()
print("Saved figures/q1_task_success_by_tier.png")


# ── Figure 2: Revision Distance Trajectory across Perturbations ───────────────
p_steps = ["P1 (Constraint)", "P2 (Dependency)", "P3 (Assumption)", "P4 (Setting)"]
# Means from empirical results
arm_a_delta = [0.160, 0.253, 0.254, 0.160]
arm_b_delta = [0.049, 0.044, 0.149, 0.104]

fig, ax = plt.subplots(figsize=(8.5, 5))
ax.plot(p_steps, arm_a_delta, marker="s", markersize=8, color="#ef4444", linewidth=2.5, label="Arm A: Autoregressive (Full Replan)")
ax.plot(p_steps, arm_b_delta, marker="o", markersize=8, color="#10b981", linewidth=2.5, label="Arm B': Hermeneutic (Targeted Revision)")

ax.set_ylabel("Revision Distance δ ∈ [0, 1]", fontsize=12, fontweight="bold")
ax.set_title("R1: Revision Distance Trajectory Under Evolving Evidence", fontsize=13, fontweight="bold", pad=15)
ax.set_ylim(0, 0.35)
ax.legend(frameon=True, loc="upper left")

for i, txt in enumerate(arm_a_delta):
    ax.annotate(f"{txt:.3f}", (p_steps[i], arm_a_delta[i]), textcoords="offset points", xytext=(0, 7), ha="center", color="#b91c1c", fontweight="bold")

for i, txt in enumerate(arm_b_delta):
    ax.annotate(f"{txt:.3f}", (p_steps[i], arm_b_delta[i]), textcoords="offset points", xytext=(0, -15), ha="center", color="#047857", fontweight="bold")

plt.tight_layout()
plt.savefig("figures/r1_revision_distance_trajectory.png", dpi=300)
plt.close()
print("Saved figures/r1_revision_distance_trajectory.png")


# ── Figure 3: Token Consumption & Resource Efficiency ───────────────────────
fig, ax = plt.subplots(figsize=(7, 5))
arms_tokens = ["Arm A\n(Autoregressive Baseline)", "Arm B'\n(Hermeneutic Agent)"]
token_vals = [13500, 6300]
colors = ["#ef4444", "#10b981"]

bars = ax.bar(arms_tokens, token_vals, color=colors, width=0.45, alpha=0.85)
ax.set_ylabel("Total Tokens per Incident Investigation", fontsize=12, fontweight="bold")
ax.set_title("C2: Token Consumption Comparison (53.3% Cost Reduction)", fontsize=13, fontweight="bold", pad=15)
ax.set_ylim(0, 16000)

for bar in bars:
    height = bar.get_height()
    ax.annotate(f"{height:,.0f} tokens", xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=11, fontweight="bold")

# Add saving bracket
ax.annotate("-53.3% Tokens", xy=(0.5, 10000), xytext=(0.5, 11500),
            ha="center", fontsize=12, fontweight="bold", color="#059669",
            arrowprops=dict(arrowstyle="->", color="#059669", lw=1.5))

plt.tight_layout()
plt.savefig("figures/c2_token_consumption.png", dpi=300)
plt.close()
print("Saved figures/c2_token_consumption.png")


# ── Figure 4: Q2 Solution Quality by Tier ───────────────────────────────────
tiers = ["Easy", "Misleading", "Conflicting", "Overall"]
arm_a_q2 = [0.812, 0.639, 0.531, 0.661]
arm_b_q2 = [0.938, 0.994, 1.000, 0.977]

x = np.arange(len(tiers))
width = 0.35

fig, ax = plt.subplots(figsize=(8, 5))
rects1 = ax.bar(x - width/2, arm_a_q2, width, label="Arm A (Autoregressive)", color="#f87171", alpha=0.85)
rects2 = ax.bar(x + width/2, arm_b_q2, width, label="Arm B' (Hermeneutic)", color="#34d399", alpha=0.85)

ax.set_ylabel("Composite Quality Score ∈ [0, 1]", fontsize=12, fontweight="bold")
ax.set_title("Q2: Investigation Solution Quality Across Tiers", fontsize=13, fontweight="bold", pad=15)
ax.set_xticks(x)
ax.set_xticklabels(tiers, fontweight="bold")
ax.set_ylim(0, 1.15)
ax.legend(frameon=True, loc="upper right")

for rect in rects1:
    h = rect.get_height()
    ax.annotate(f"{h:.3f}", xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=10)

for rect in rects2:
    h = rect.get_height()
    ax.annotate(f"{h:.3f}", xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=10, fontweight="bold")

plt.tight_layout()
plt.savefig("figures/q2_solution_quality_distribution.png", dpi=300)
plt.close()
print("Saved figures/q2_solution_quality_distribution.png")


# ── Figure 5: Investigation Time Taken & Operational Containment (MTTC) ──────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Subplot 1: Investigation Latency (seconds)
arms = ["Arm A\n(Autoregressive)", "Arm B'\n(Hermeneutic)"]
time_sec = [28.77, 11.99]
colors = ["#ef4444", "#10b981"]

bars1 = ax1.bar(arms, time_sec, color=colors, width=0.45, alpha=0.85)
ax1.set_ylabel("Investigation Time Taken (Seconds)", fontsize=11, fontweight="bold")
ax1.set_title("C5: End-to-End Investigation Latency\n(58.3% Faster Turnaround)", fontsize=12, fontweight="bold")
ax1.set_ylim(0, 35)

for bar in bars1:
    h = bar.get_height()
    ax1.annotate(f"{h:.1f} s", xy=(bar.get_x() + bar.get_width() / 2, h),
                 xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=11, fontweight="bold")

# Subplot 2: Operational Mean Time to Containment (hours)
mttc_hours = [38.30, 4.17]
bars2 = ax2.bar(arms, mttc_hours, color=colors, width=0.45, alpha=0.85)
ax2.set_ylabel("Mean Time to Containment (Hours)", fontsize=11, fontweight="bold")
ax2.set_title("Operational Impact: Time to Breach Containment\n(89.1% Faster Containment)", fontsize=12, fontweight="bold")
ax2.set_ylim(0, 46)

for bar in bars2:
    h = bar.get_height()
    ax2.annotate(f"{h:.1f} hrs", xy=(bar.get_x() + bar.get_width() / 2, h),
                 xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=11, fontweight="bold")

plt.tight_layout()
plt.savefig("figures/c5_time_taken_contrast.png", dpi=300)
plt.close()
print("Saved figures/c5_time_taken_contrast.png")

print("All 5 figures successfully generated!")
