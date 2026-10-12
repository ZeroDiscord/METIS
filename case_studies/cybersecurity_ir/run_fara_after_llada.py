"""
METIS Contrastive Benchmark Orchestrator: LLaDA -> FARA
======================================================
1. Monitored wait: Watches active LLaDA live run until all 72 runs complete.
2. Plots LLaDA: Generates LLaDA figures in figures_llada/ and figures/.
3. Runs FARA: Executes live FARA inference across all 72 runs into runs_fara/ and results_fara.csv.
4. Plots FARA: Generates FARA figures in figures_fara/.
5. Generates Contrastive Report: Compares Diffusion LLM (LLaDA) vs Autoregressive LLM (FARA).
"""

import os
import sys
import time
import subprocess
import csv
import psutil
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RESULTS_LLADA = BASE_DIR / "results.csv"
RESULTS_FARA = BASE_DIR / "results_fara.csv"
RUNS_LLADA = BASE_DIR / "runs"
RUNS_FARA = BASE_DIR / "runs_fara"
FIGS_LLADA = BASE_DIR / "figures_llada"
FIGS_FARA = BASE_DIR / "figures_fara"
FIGS_CONTRAST = BASE_DIR / "figures_contrastive"


def get_llada_process():
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = " ".join(p.info['cmdline'] or [])
            if "runner.py" in cmd and "llada" in cmd:
                return p
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None


def count_csv_rows(csv_path: Path) -> int:
    if not csv_path.exists():
        return 0
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            return len(reader)
    except Exception:
        return 0


def wait_for_llada_completion(poll_interval: int = 30):
    print("=" * 80)
    print("[Orchestrator] Monitoring LLaDA benchmark execution...")
    print("=" * 80)

    start_time = time.time()
    last_count = -1

    while True:
        proc = get_llada_process()
        completed_rows = count_csv_rows(RESULTS_LLADA)

        if completed_rows != last_count:
            last_count = completed_rows
            print(f"[LLaDA Progress] {completed_rows} / 72 runs completed in results.csv (Elapsed: {round(time.time() - start_time)}s)")

        if proc is None:
            # Check if process really exited or finished
            time.sleep(5)
            if get_llada_process() is None:
                print(f"[Orchestrator] LLaDA benchmark process has completed! (Total runs in results.csv: {completed_rows})")
                break

        time.sleep(poll_interval)


def generate_llada_plots():
    print("\n" + "=" * 80)
    print("[Orchestrator] Generating LLaDA benchmark figures...")
    print("=" * 80)
    plots_script = BASE_DIR / "analysis" / "plots.py"

    # Generate in figures_llada and default figures/
    for out_dir in [FIGS_LLADA, BASE_DIR / "figures"]:
        cmd = [
            sys.executable,
            str(plots_script),
            "--csv", str(RESULTS_LLADA),
            "--output-dir", str(out_dir),
            "--model", "LLaDA-Diffusion",
        ]
        res = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)
        print(f"Output for {out_dir.name}:\n{res.stdout.strip()}")
        if res.returncode != 0:
            print(f"Error generating LLaDA plots: {res.stderr}")


def run_fara_benchmark():
    print("\n" + "=" * 80)
    print("[Orchestrator] Launching Full FARA Benchmark (72 runs)...")
    print("  Runs Directory: runs_fara/")
    print("  Results CSV:    results_fara.csv")
    print("=" * 80)

    runner_script = BASE_DIR / "runner.py"
    cmd = [
        sys.executable,
        "-u",
        str(runner_script),
        "--mode", "live",
        "--model", "fara",
        "--runs-dir", str(RUNS_FARA),
        "--results-csv", str(RESULTS_FARA),
    ]

    t0 = time.time()
    proc = subprocess.Popen(
        cmd,
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    for line in iter(proc.stdout.readline, ""):
        print(line, end="", flush=True)

    proc.stdout.close()
    return_code = proc.wait()
    total_time = round(time.time() - t0, 1)

    print(f"\n[Orchestrator] FARA benchmark completed in {total_time}s with exit code {return_code}.")
    return return_code


def generate_fara_plots():
    print("\n" + "=" * 80)
    print("[Orchestrator] Generating FARA benchmark figures in figures_fara/...")
    print("=" * 80)
    plots_script = BASE_DIR / "analysis" / "plots.py"

    cmd = [
        sys.executable,
        str(plots_script),
        "--csv", str(RESULTS_FARA),
        "--output-dir", str(FIGS_FARA),
        "--model", "Microsoft-FARA-7B",
    ]
    res = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)
    print(res.stdout.strip())
    if res.returncode != 0:
        print(f"Error generating FARA plots: {res.stderr}")


def generate_contrastive_comparison():
    print("\n" + "=" * 80)
    print("[Orchestrator] Generating Diffusion vs Autoregressive Contrastive Report...")
    print("=" * 80)

    if not RESULTS_LLADA.exists() or not RESULTS_FARA.exists():
        print("Both results.csv and results_fara.csv must exist to generate contrastive analysis.")
        return

    import numpy as np

    with open(RESULTS_LLADA, "r", encoding="utf-8") as f:
        llada_rows = list(csv.DictReader(f))
    with open(RESULTS_FARA, "r", encoding="utf-8") as f:
        fara_rows = list(csv.DictReader(f))

    def summarize(rows):
        arms = {"arm_a": {}, "arm_b": {}}
        for arm in ["arm_a", "arm_b"]:
            arm_rows = [r for r in rows if r.get("arm") == arm]
            if not arm_rows:
                continue
            arms[arm] = {
                "q1_task_success": np.mean([float(r["q1_task_success"]) for r in arm_rows if r.get("q1_task_success")]),
                "q2_solution_quality": np.mean([float(r["q2_solution_quality"]) for r in arm_rows if r.get("q2_solution_quality")]),
                "r1_revision_distance": np.mean([float(r["r1_mean_revision_distance"]) for r in arm_rows if r.get("r1_mean_revision_distance")]),
                "r2_work_preservation": np.mean([float(r["r2_mean_work_preservation"]) for r in arm_rows if r.get("r2_mean_work_preservation")]),
                "c2_total_tokens": np.mean([float(r["c2_total_tokens"]) for r in arm_rows if r.get("c2_total_tokens")]),
                "c5_time_taken_s": np.mean([float(r["c5_time_taken_s"]) for r in arm_rows if r.get("c5_time_taken_s")]),
            }
        return arms

    s_llada = summarize(llada_rows)
    s_fara = summarize(fara_rows)

    report_lines = [
        "# METIS Contrastive Benchmark Study: LLaDA (Diffusion) vs FARA (Autoregressive)",
        "",
        "## Summary Metrics Comparison (72 Runs per Model)",
        "",
        "| Architecture | Model Paradigm | Arm | Q1 Success | Q2 Quality | R1 Rev Dist | R2 Work Pres | C2 Tokens | C5 Latency (s) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for model_name, paradigm, s in [
        ("LLaDA-MoE-7B", "Diffusion LLM", s_llada),
        ("Microsoft-FARA-7B", "Autoregressive LLM", s_fara),
    ]:
        for arm, arm_label in [("arm_a", "Arm A (Autoregressive Replan)"), ("arm_b", "Arm B' (Hermeneutic σ)")]:
            data = s.get(arm, {})
            if data:
                report_lines.append(
                    f"| {model_name} | {paradigm} | {arm_label} | "
                    f"{data.get('q1_task_success', 0)*100:.1f}% | "
                    f"{data.get('q2_solution_quality', 0):.3f} | "
                    f"{data.get('r1_revision_distance', 0):.3f} | "
                    f"{data.get('r2_work_preservation', 0):.3f} | "
                    f"{data.get('c2_total_tokens', 0):,.0f} | "
                    f"{data.get('c5_time_taken_s', 0):.1f}s |"
                )

    report_path = BASE_DIR / "contrastive_study_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

    print(f"Saved contrastive report to {report_path.name}")


def main():
    wait_for_llada_completion(poll_interval=20)
    generate_llada_plots()
    run_fara_benchmark()
    generate_fara_plots()
    generate_contrastive_comparison()
    print("\n[Orchestrator] All tasks successfully completed!")


if __name__ == "__main__":
    main()
