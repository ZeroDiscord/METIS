"""
Generates publication-quality figures for the Cybersecurity Incident Response benchmark:
1. Figure 1: Q1 Task Success Rate across Difficulty Tiers (Bar chart)
2. Figure 2: Revision Distance Trajectory across Perturbations (Line plot)
3. Figure 3: Token Consumption & Resource Efficiency (Bar chart)
4. Figure 4: Solution Quality by Tier (Bar chart)
5. Figure 5: Investigation Time Taken & Operational Containment (MTTC)
"""

import os
import csv
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

# Styling
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.size"] = 11


def generate_plots(csv_path: str = "results.csv", output_dir: str = "figures", model_label: str = ""):
    os.makedirs(output_dir, exist_ok=True)

    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print(f"No data found in {csv_path}. Skipping plot generation.")
        return

    title_suffix = f" [{model_label}]" if model_label else ""

    # Aggregate metrics by (arm, difficulty) and arm overall
    groups = defaultdict(lambda: defaultdict(list))
    overall = defaultdict(lambda: defaultdict(list))

    for r in rows:
        arm = r["arm"]
        diff = r["difficulty"]
        for k, v in r.items():
            try:
                val = float(v)
                groups[(arm, diff)][k].append(val)
                overall[arm][k].append(val)
            except (ValueError, TypeError):
                pass

    tier_keys = ["easy", "misleading", "conflicting"]
    tiers_display = ["Easy", "Misleading", "Conflicting", "Overall"]

    # ── Figure 1: Q1 Task Success Rate across Difficulty Tiers ───────────────────
    arm_a_success = [np.mean(groups[("arm_a", d)]["q1_task_success"]) if groups[("arm_a", d)]["q1_task_success"] else 0.0 for d in tier_keys]
    arm_a_success.append(np.mean(overall["arm_a"]["q1_task_success"]) if overall["arm_a"]["q1_task_success"] else 0.0)

    arm_b_success = [np.mean(groups[("arm_b", d)]["q1_task_success"]) if groups[("arm_b", d)]["q1_task_success"] else 0.0 for d in tier_keys]
    arm_b_success.append(np.mean(overall["arm_b"]["q1_task_success"]) if overall["arm_b"]["q1_task_success"] else 0.0)

    x = np.arange(len(tiers_display))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    rects1 = ax.bar(x - width/2, [s * 100 for s in arm_a_success], width, label="Arm A (Autoregressive Replan)", color="#ef4444", alpha=0.85)
    rects2 = ax.bar(x + width/2, [s * 100 for s in arm_b_success], width, label="Arm B' (Hermeneutic State σ)", color="#10b981", alpha=0.85)

    ax.set_ylabel("Task Success Rate (%)", fontsize=12, fontweight="bold")
    ax.set_title(f"Q1: Task Success Rate by Difficulty Tier (N={len(rows)} runs){title_suffix}", fontsize=13, fontweight="bold", pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(tiers_display, fontweight="bold")
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
    plt.savefig(os.path.join(output_dir, "q1_task_success_by_tier.png"), dpi=300)
    plt.close()
    print(f"Saved {os.path.join(output_dir, 'q1_task_success_by_tier.png')}")

    # ── Figure 2: Revision Distance Trajectory across Perturbations ───────────────
    p_steps = ["P1 (Constraint)", "P2 (Dependency)", "P3 (Assumption)", "P4 (Setting)"]
    p_keys = ["r1_delta_p1", "r1_delta_p2", "r1_delta_p3", "r1_delta_p4"]

    arm_a_delta = [np.mean(overall["arm_a"][k]) if overall["arm_a"][k] else 0.0 for k in p_keys]
    arm_b_delta = [np.mean(overall["arm_b"][k]) if overall["arm_b"][k] else 0.0 for k in p_keys]

    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.plot(p_steps, arm_a_delta, marker="s", markersize=8, color="#ef4444", linewidth=2.5, label="Arm A: Autoregressive (Full Replan)")
    ax.plot(p_steps, arm_b_delta, marker="o", markersize=8, color="#10b981", linewidth=2.5, label="Arm B': Hermeneutic (Targeted Revision)")

    ax.set_ylabel("Revision Distance δ in [0, 1]", fontsize=12, fontweight="bold")
    ax.set_title(f"R1: Revision Distance Trajectory Under Evolving Evidence{title_suffix}", fontsize=13, fontweight="bold", pad=15)
    max_d = max(max(arm_a_delta + [0.1]), max(arm_b_delta + [0.1]))
    ax.set_ylim(-0.02, max_d + 0.1)
    ax.legend(frameon=True, loc="upper left")

    for i, txt in enumerate(arm_a_delta):
        ax.annotate(f"{txt:.3f}", (p_steps[i], arm_a_delta[i]), textcoords="offset points", xytext=(0, 7), ha="center", color="#b91c1c", fontweight="bold")

    for i, txt in enumerate(arm_b_delta):
        ax.annotate(f"{txt:.3f}", (p_steps[i], arm_b_delta[i]), textcoords="offset points", xytext=(0, -15), ha="center", color="#047857", fontweight="bold")

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "r1_revision_distance_trajectory.png"), dpi=300)
    plt.close()
    print(f"Saved {os.path.join(output_dir, 'r1_revision_distance_trajectory.png')}")

    # ── Figure 3: Token Consumption & Resource Efficiency ───────────────────────
    fig, ax = plt.subplots(figsize=(7, 5))
    arms_tokens = ["Arm A\n(Autoregressive Baseline)", "Arm B'\n(Hermeneutic Agent)"]
    tok_a = np.mean(overall["arm_a"]["c2_total_tokens"]) if overall["arm_a"]["c2_total_tokens"] else 0.0
    tok_b = np.mean(overall["arm_b"]["c2_total_tokens"]) if overall["arm_b"]["c2_total_tokens"] else 0.0
    token_vals = [tok_a, tok_b]
    colors = ["#ef4444", "#10b981"]

    bars = ax.bar(arms_tokens, token_vals, color=colors, width=0.45, alpha=0.85)
    ax.set_ylabel("Total Tokens per Incident Investigation", fontsize=12, fontweight="bold")
    ax.set_title(f"C2: Token Consumption Comparison{title_suffix}", fontsize=13, fontweight="bold", pad=15)
    ax.set_ylim(0, max(token_vals + [1000]) * 1.25)

    for bar in bars:
        height = bar.get_height()
        ax.annotate(f"{height:,.0f} tokens", xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=11, fontweight="bold")

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "c2_token_consumption.png"), dpi=300)
    plt.close()
    print(f"Saved {os.path.join(output_dir, 'c2_token_consumption.png')}")

    # ── Figure 4: Q2 Solution Quality by Tier ───────────────────────────────────
    arm_a_q2 = [np.mean(groups[("arm_a", d)]["q2_solution_quality"]) if groups[("arm_a", d)]["q2_solution_quality"] else 0.0 for d in tier_keys]
    arm_a_q2.append(np.mean(overall["arm_a"]["q2_solution_quality"]) if overall["arm_a"]["q2_solution_quality"] else 0.0)

    arm_b_q2 = [np.mean(groups[("arm_b", d)]["q2_solution_quality"]) if groups[("arm_b", d)]["q2_solution_quality"] else 0.0 for d in tier_keys]
    arm_b_q2.append(np.mean(overall["arm_b"]["q2_solution_quality"]) if overall["arm_b"]["q2_solution_quality"] else 0.0)

    fig, ax = plt.subplots(figsize=(8, 5))
    rects1 = ax.bar(x - width/2, arm_a_q2, width, label="Arm A (Autoregressive)", color="#f87171", alpha=0.85)
    rects2 = ax.bar(x + width/2, arm_b_q2, width, label="Arm B' (Hermeneutic)", color="#34d399", alpha=0.85)

    ax.set_ylabel("Composite Quality Score in [0, 1]", fontsize=12, fontweight="bold")
    ax.set_title(f"Q2: Investigation Solution Quality Across Tiers{title_suffix}", fontsize=13, fontweight="bold", pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(tiers_display, fontweight="bold")
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
    plt.savefig(os.path.join(output_dir, "q2_solution_quality_distribution.png"), dpi=300)
    plt.close()
    print(f"Saved {os.path.join(output_dir, 'q2_solution_quality_distribution.png')}")

    # ── Figure 5: Investigation Time Taken & Operational Containment (MTTC) ──────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Subplot 1: Investigation Latency (seconds)
    arms = ["Arm A\n(Autoregressive)", "Arm B'\n(Hermeneutic)"]
    time_a = np.mean(overall["arm_a"]["c5_time_taken_s"]) if overall["arm_a"]["c5_time_taken_s"] else 0.0
    time_b = np.mean(overall["arm_b"]["c5_time_taken_s"]) if overall["arm_b"]["c5_time_taken_s"] else 0.0
    time_sec = [time_a, time_b]
    colors = ["#ef4444", "#10b981"]

    bars1 = ax1.bar(arms, time_sec, color=colors, width=0.45, alpha=0.85)
    ax1.set_ylabel("Investigation Time Taken (Seconds)", fontsize=11, fontweight="bold")
    ax1.set_title(f"C5: End-to-End Investigation Latency{title_suffix}", fontsize=12, fontweight="bold")
    ax1.set_ylim(0, max(time_sec + [10]) * 1.3)

    for bar in bars1:
        h = bar.get_height()
        ax1.annotate(f"{h:.1f} s", xy=(bar.get_x() + bar.get_width() / 2, h),
                     xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=11, fontweight="bold")

    # Subplot 2: Operational Mean Time to Containment (hours)
    mttc_a = np.mean(overall["arm_a"]["mttc_hours"]) if overall["arm_a"]["mttc_hours"] else 0.0
    mttc_b = np.mean(overall["arm_b"]["mttc_hours"]) if overall["arm_b"]["mttc_hours"] else 0.0
    mttc_hours = [mttc_a, mttc_b]
    bars2 = ax2.bar(arms, mttc_hours, color=colors, width=0.45, alpha=0.85)
    ax2.set_ylabel("Mean Time to Containment (Hours)", fontsize=11, fontweight="bold")
    diff_pct = ((mttc_a - mttc_b) / mttc_a) * 100 if mttc_a > 0 else 0
    ax2.set_title(f"Operational Impact: Time to Breach Containment\n({diff_pct:.1f}% Faster Containment){title_suffix}", fontsize=12, fontweight="bold")
    ax2.set_ylim(0, max(mttc_hours + [10]) * 1.25)

    for bar in bars2:
        h = bar.get_height()
        ax2.annotate(f"{h:.1f} hrs", xy=(bar.get_x() + bar.get_width() / 2, h),
                     xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=11, fontweight="bold")

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "c5_time_taken_contrast.png"), dpi=300)
    plt.close()
    print(f"Saved {os.path.join(output_dir, 'c5_time_taken_contrast.png')}")

    print(f"All 5 figures successfully generated in {output_dir}/!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate benchmark figures")
    parser.add_argument("--csv", type=str, default="results.csv", help="Path to results CSV (default: results.csv)")
    parser.add_argument("--output-dir", type=str, default="figures", help="Output directory for figures (default: figures)")
    parser.add_argument("--model", type=str, default="", help="Model name for titles")
    args = parser.parse_args()
    generate_plots(csv_path=args.csv, output_dir=args.output_dir, model_label=args.model)
