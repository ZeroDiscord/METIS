"""
sysmon_tools.py — Diagnostic tools for System Performance Diagnosis.

Provides structured LangChain tools wrapping SystemEnvironment queries and final diagnosis submission.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

from environment import SystemEnvironment

# Global environment instance bound per run
_ACTIVE_ENV: Optional[SystemEnvironment] = None


def set_active_environment(env: SystemEnvironment) -> None:
    global _ACTIVE_ENV
    _ACTIVE_ENV = env


def get_active_environment() -> SystemEnvironment:
    global _ACTIVE_ENV
    if _ACTIVE_ENV is None:
        _ACTIVE_ENV = SystemEnvironment()
    return _ACTIVE_ENV


@tool
def performance_monitor() -> Dict[str, Any]:
    """
    Queries current gaming performance metrics including FPS, baseline target, 1% lows, and frametime stability.
    """
    env = get_active_environment()
    return env.get_performance_metrics()


@tool
def cpu_monitor() -> Dict[str, Any]:
    """
    Queries CPU metrics including overall CPU utilization, main game-thread utilization, CPU temperature, and clock speed.
    """
    env = get_active_environment()
    return env.get_cpu_metrics()


@tool
def gpu_monitor() -> Dict[str, Any]:
    """
    Queries GPU metrics including GPU utilization, GPU core temperature, GPU clock, VRAM usage, and power draw.
    """
    env = get_active_environment()
    return env.get_gpu_metrics()


@tool
def memory_monitor() -> Dict[str, Any]:
    """
    Queries RAM utilization, total capacity, memory pressure status, and paging file usage.
    """
    env = get_active_environment()
    return env.get_memory_metrics()


@tool
def system_events() -> Dict[str, Any]:
    """
    Queries system history including recent game updates, graphics driver changes, Windows updates, and background load.
    """
    env = get_active_environment()
    return env.get_system_events()


@tool
def game_diagnostics() -> Dict[str, Any]:
    """
    Queries game engine diagnostics including asset streaming status, rendering stalls, and thread waits.
    """
    env = get_active_environment()
    return env.get_game_diagnostics()


@tool
def settings_monitor() -> Dict[str, Any]:
    """
    Queries current game graphics settings, resolution, quality presets, and ray tracing status.
    """
    env = get_active_environment()
    return env.get_settings_metrics()


@tool
def submit_diagnosis(
    primary_cause: str,
    contributing_factors: List[str],
    supporting_evidence: List[str],
    confidence: float,
    rejected_alternatives: List[str],
) -> Dict[str, Any]:
    """
    Submit the final diagnostic conclusion for the performance degradation.
    
    Args:
        primary_cause: The single main root cause of degradation (e.g. asset_streaming_issue_after_game_update, gpu_bottleneck, etc.)
        contributing_factors: Secondary factors contributing to the issue.
        supporting_evidence: Concrete telemetry points or events supporting this diagnosis.
        confidence: Confidence score from 0.0 to 1.0.
        rejected_alternatives: Competing hypotheses that were investigated and explicitly ruled out.
    """
    return {
        "submission_type": "final_diagnosis",
        "primary_cause": primary_cause,
        "contributing_factors": contributing_factors,
        "supporting_evidence": supporting_evidence,
        "confidence": confidence,
        "rejected_alternatives": rejected_alternatives,
    }


ALL_TOOLS = [
    performance_monitor,
    cpu_monitor,
    gpu_monitor,
    memory_monitor,
    system_events,
    game_diagnostics,
    settings_monitor,
    submit_diagnosis,
]
