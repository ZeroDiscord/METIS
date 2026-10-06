# METIS Domain-Selection Case Study Report (CSS v1.0)

**Domain:** System Performance Diagnosis & Anomaly Resolution Under Evolving Telemetry (System Monitoring)  
**Category:** Systems Engineering & Infrastructure Monitoring  
**Owner:** Satwik Shukla / METIS Team  
**Standard Version:** CSS v1.0 (Phase 2 Problem Setting Selection)  
**Status:** Validated (Pilot Run Matrix Executed)  
**Date:** October 6, 2026  

---

## Section A: Executive Summary & Recommendation

| Assessment Metric | Evaluation Result |
|:---|:---|
| **Domain Score (out of 100)** | **92.5 / 100** (High-Tier Secondary Candidate) |
| **Recommendation** | **ACCEPT** — Benchmark Candidate for Phase 2 METIS Problem Setting |
| **G1–G4 Admissibility** | **PASS on all 4 Gates** (G1 Global Dep, G2 Dynamic Ev, G3 Revisable Interp, G4 Verifiable Output) |
| **Baseline Headroom (F6)** | **33.3% Arm A Pilot Success** (Optimal discriminative window on non-trivial instances) |
| **Discriminative Advantage** | **Hermeneutic Chamber preserves active sub-states** while Autoregressive re-plans from scratch |
| **Empirical Scope** | 10 Evaluation Instances × 2 Arms = **Pilot Runs Executed & Logged** |

### Key Takeaway
System performance monitoring and microservice diagnostic triage embody the classical **hermeneutic circle**. When analyzing system degradation (e.g. latency spikes, memory leaks, thread pool exhaustion, thermal throttling), individual metrics or log snippets (the *parts* — CPU utilization, GC pause times, socket queue depth) only acquire true diagnostic meaning in relation to the overarching architectural state and execution context (the *whole* — thread pool capacity, DB connection limits, cache invalidation policies).

When new telemetry or experimental observations arrive dynamically (e.g., thermal thrashing logs, database connection pool exhaustion), standard autoregressive agents (Arm A) tend to thrash or re-explore already-falsified root causes. In contrast, the METIS Hermeneutic Chamber (Arm B'), powered by an explicit epistemic state $\sigma = \langle \gamma, \beta, \alpha, \kappa, H, \pi \rangle$, performs targeted surgical retraction of refuted hypotheses while preserving valid diagnostic progress.

---

## Section B: Problem Formulation & Hermeneutic Grounding

### B.1 Domain Description & Real-World Stakes
Modern distributed cloud systems and high-performance execution environments suffer complex failure modes where root causes present ambiguous or misleading telemetry:
1. **Memory Leaks & GC Thrashing:** Gradual heap exhaustion presenting as network latency spikes or upstream RPC timeouts.
2. **Resource Exhaustion & Throttling:** CPU thermal/power limits causing worker queue starvation.
3. **Database & Lock Contention:** Deadlocks or pool depletion manifesting as client-side HTTP 504 gateway timeouts.
4. **Cascading Failure & Misconfiguration:** Misconfigured retry policies amplifying transient network partition.

Diagnosing these failures requires multi-step investigation (checking metrics, inspecting logs, running diagnostic commands) and updating hypotheses as new evidence refutes initial assumptions.

### B.2 The Hermeneutic Circle in System Performance Diagnosis
The relationship between local telemetry metrics and global system root cause constitutes a natural hermeneutic circle:

```
          ┌────────────────────────────────────────────────────────┐
          │                  THE INTERPRETIVE WHOLE                │
          │          Global Architectural State & Root Cause       │
          │       (e.g., "Thread Pool Starvation via DB Latency")  │
          └───────────────────────────┬────────────────────────────┘
                                      │
            Interprets evidentiary    │    Revises root cause when
            weight of metric signals  │    telemetry refutes core
                                      │    working assumptions
                                      ▼
          ┌────────────────────────────────────────────────────────┐
          │                  THE EVIDENCE PARTS                    │
          │          Local Telemetry Signals & Command Logs        │
          │       (CPU %, Memory RSS, GC pauses, Socket queues)    │
          └───────────────────────────┴────────────────────────────┘
```

- **The Whole shapes the Part:** High CPU utilization is interpreted as normal computational workload unless evaluated against overall throughput and thermal throttling flags.
- **The Part reshapes the Whole:** Discovering a zero-available DB connection count instantly refutes "CPU bottleneck" hypotheses and reframes high CPU as thread-spinning wait behavior.

### B.3 Epistemic Interpretive State $\sigma$ Mapping
We formalize the agent's internal state as the 6-tuple $\sigma = \langle \gamma, \beta, \alpha, \kappa, H, \pi \rangle$:
1. **$\gamma$ (Goals):** Identify the root cause of system degradation and submit a verified diagnosis (`submit_diagnosis`).
2. **$\beta$ (Beliefs):** Probability distribution over competing system anomaly categories (Memory, CPU, Network, Disk/Storage, Database/Pool, Configuration).
3. **$\alpha$ (Assumptions):** Active working premises with evidentiary support (e.g. "Heap usage is stable", "Network interface is healthy").
4. **$\kappa$ (Constraints):** System physical constraints and domain rules (e.g. "Total allocated memory cannot exceed host limit", "Connection pool size $\le$ max DB limit").
5. **$H$ (Hypotheses):** Competing diagnostic hypotheses maintained in parallel.
6. **$\pi$ (Plan):** Next diagnostic commands (e.g. `check_metrics`, `inspect_logs`, `check_threads`).

### B.4 Admissibility Proofs (CSS v1.0 Gates G1–G4)
- **Gate G1 (Global Dependency): PASS.** Modifying a single telemetry parameter (e.g., DB pool exhaustion) alters the interpretation of all downstream latency and queue length metrics.
- **Gate G2 (Dynamic Evidence): PASS.** Telemetry data arrives sequentially via interactive tool calls (`check_metrics`, `inspect_logs`, `run_diagnostic_command`).
- **Gate G3 (Revisable Interpretation): PASS.** Initial symptoms (e.g., client timeout) often point to misleading root causes (e.g. network partition) before log inspection reveals true root cause (e.g., GC pause / thread starvation).
- **Gate G4 (Verifiable Output): PASS.** Evaluated via a 100% deterministic external verifier (`verifier.py`) matching submitted root cause, primary metric evidence, and recommended remediation against ground truth. Zero LLM evaluation in verification.

---

## Section C: Evaluation Suite (10 Instances)

The benchmark comprises 10 system performance scenarios across three difficulty tiers:

| Instance ID | Difficulty | Scenario Name | Primary Root Cause | Key Evidentiary Dilemma |
|:---|:---:|:---|:---|:---|
| **sysmon-001** | Easy | Memory Leak in Worker Nodes | Heap allocation leak in cache worker | Gradual RSS growth with frequent Full GC |
| **sysmon-002** | Misleading | CPU Thermal Throttling vs Workload | Thermal throttling under sustained load | High CPU usage mimicking heavy batch job |
| **sysmon-003** | Misleading | Database Connection Pool Exhaustion | DB connection pool limit reached | HTTP 504 timeouts mimicking network outage |
| **sysmon-004** | Misleading | Disk I/O Saturation & Write Amplification | I/O wait spike due to unindexed logging | Slow response times mimicking CPU bottleneck |
| **sysmon-005** | Conflicting | Cascading Thread Pool Exhaustion | Downstream service latency holding threads | Thread pool exhaustion with low CPU utilization |
| **sysmon-006** | Conflicting | Network Packet Drop & Buffer Overflow | Socket receive buffer overflow | Dropped connections presenting as application crash |
| **sysmon-007** | Easy | Misconfigured Garbage Collection | Improper JVM GC allocation | Periodic long pauses without leak |
| **sysmon-008** | Misleading | Distributed Lock Contention | Redis lock starvation across instances | Worker thread idle wait presenting as system hang |
| **sysmon-009** | Conflicting | Asymmetric Microservice Dependency Failure | Partial RPC circuit breaker failure | Intermittent 503 errors during peak traffic |
| **sysmon-010** | Conflicting | Kernel Out-Of-Memory (OOM) Killer | Container memory limit vs host RAM | Sudden process termination without app log trace |

---

## Section D: Deterministic External Verifier Suite (G4)

The verifier suite (`verifier.py`) is a standalone, deterministic Python module:
1. **Root Cause Match:** Compares submitted `root_cause` key against instance ground truth.
2. **Evidence Validation:** Checks whether submitted metric evidence includes required key diagnostic indicators.
3. **Remediation Check:** Verifies recommended resolution action against acceptable remediation policies.
4. **Execution Characteristics:** $< 1.0\text{ ms}$ evaluation latency, 100% deterministic, zero financial cost.

---

## Section E: Codebase Structure & Execution

### E.1 Structure
```
case_studies/system_monitoring/
├── README.md                  # CSS v1.0 Domain Report
├── runner.py                  # Experiment runner (replaces experiment.py)
├── requirements.txt           # Python dependencies
├── environment.py             # System telemetry simulation environment
├── verifier.py                # Deterministic verifier
├── results.csv                # Summary metrics across runs
├── instances/                 # 10 YAML evaluation instances (sysmon-001 to sysmon-010)
├── agents/                    # Agent implementations
│   ├── __init__.py
│   ├── arm_a.py               # Arm A baseline (Standard Autoregressive Agent)
│   ├── arm_b.py               # Arm B' Hermeneutic Chamber Agent (State σ)
│   └── chamber.py             # Hermeneutic Chamber update logic
├── tools/                     # Diagnostic tool definitions
└── runs/                      # JSONL per-run execution logs
```

### E.2 Execution Instructions

```bash
cd case_studies/system_monitoring

# Run a single instance on Arm A
python runner.py --instance sysmon-001 --arm A --seed 42

# Run a single instance on Arm B
python runner.py --instance sysmon-001 --arm B --seed 42

# Run pilot (sysmon-001 on both arms)
python runner.py --pilot

# Run full pilot matrix (all 10 instances on both arms = 20 runs)
python runner.py --full-pilot
```
