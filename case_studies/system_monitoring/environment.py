"""
environment.py — Simulated System Telemetry Environment

Provides realistic, internally consistent telemetry for system performance diagnosis.
Contains hidden state and ground truth, but exposes ONLY raw observations through diagnostic queries.
"""

from __future__ import annotations
from typing import Dict, Any


class SystemEnvironment:
    """
    Simulated System Telemetry Environment.
    Maintains hidden ground truth internally while providing objective telemetry observations.
    """

    def __init__(self, instance_data: dict | None = None):
        # Default state representing sysmon-001 initial telemetry
        self.state: Dict[str, Any] = {
            "fps": 45,
            "fps_baseline": 90,
            "one_percent_low": 24,
            "frametime_variance": "high (spikes up to 48ms)",
            
            "cpu_utilization_total": 65,
            "game_thread_utilization": 100,
            "cpu_temperature": 68,
            "cpu_clock_ghz": 4.2,
            "cpu_cores": 8,
            
            # Initial misleading metric: high GPU utilization
            "gpu_utilization": 97,
            "gpu_temperature": 62,
            "gpu_clock_mhz": 2400,
            "gpu_power_watts": 210,
            "gpu_power_limit_watts": 280,
            "vram_used_gb": 7.2,
            "vram_total_gb": 12.0,
            
            "ram_used_gb": 11.2,
            "ram_total_gb": 16.0,
            "memory_pressure": "normal",
            "paging_file_usage_percent": 14,
            
            "recent_game_update": True,
            "game_update_info": "v1.4.0 installed yesterday (refactored asset streaming pipeline)",
            "recent_driver_update": False,
            "driver_version": "551.23 (installed 21 days ago)",
            "windows_update": False,
            "background_processes": "normal (system idle 98% non-game)",
            
            "asset_streaming_status": "delayed (buffer underrun in stream cache)",
            "rendering_stalls": "frequent render thread waits on I/O queue",
            "game_thread_state": "blocked waiting for asset chunk decompression",
            
            "resolution": "1920x1080",
            "graphics_preset": "Ultra",
            "ray_tracing": False,
            "dlss_fsr": "Off",
        }

        # Override defaults if instance config specifies overrides (either top-level or under initial_spec)
        if instance_data:
            overrides = instance_data.get("environment_overrides") or instance_data.get("initial_spec", {}).get("environment_overrides")
            if overrides:
                self.state.update(overrides)

    # ── Telemetry Query Methods ──────────────────────────────────────────────

    def get_performance_metrics(self) -> Dict[str, Any]:
        return {
            "current_fps": self.state["fps"],
            "baseline_fps": self.state["fps_baseline"],
            "one_percent_low_fps": self.state["one_percent_low"],
            "frametime_variance": self.state["frametime_variance"],
        }

    def get_cpu_metrics(self) -> Dict[str, Any]:
        return {
            "overall_cpu_utilization_percent": self.state["cpu_utilization_total"],
            "main_game_thread_utilization_percent": self.state["game_thread_utilization"],
            "cpu_temperature_celsius": self.state["cpu_temperature"],
            "cpu_clock_ghz": self.state["cpu_clock_ghz"],
            "cpu_core_count": self.state["cpu_cores"],
        }

    def get_gpu_metrics(self) -> Dict[str, Any]:
        return {
            "gpu_utilization_percent": self.state["gpu_utilization"],
            "gpu_temperature_celsius": self.state["gpu_temperature"],
            "gpu_clock_mhz": self.state["gpu_clock_mhz"],
            "gpu_power_draw_watts": self.state["gpu_power_watts"],
            "gpu_power_limit_watts": self.state["gpu_power_limit_watts"],
            "vram_used_gb": self.state["vram_used_gb"],
            "vram_total_gb": self.state["vram_total_gb"],
        }

    def get_memory_metrics(self) -> Dict[str, Any]:
        return {
            "ram_used_gb": self.state["ram_used_gb"],
            "ram_total_gb": self.state["ram_total_gb"],
            "memory_pressure": self.state["memory_pressure"],
            "paging_file_usage_percent": self.state["paging_file_usage_percent"],
        }

    def get_system_events(self) -> Dict[str, Any]:
        return {
            "recent_game_update": self.state["recent_game_update"],
            "game_update_info": self.state["game_update_info"],
            "recent_driver_update": self.state["recent_driver_update"],
            "driver_version": self.state["driver_version"],
            "windows_update": self.state["windows_update"],
            "background_processes": self.state["background_processes"],
        }

    def get_game_diagnostics(self) -> Dict[str, Any]:
        return {
            "asset_streaming_status": self.state["asset_streaming_status"],
            "rendering_stalls": self.state["rendering_stalls"],
            "game_thread_state": self.state["game_thread_state"],
        }

    def get_settings_metrics(self) -> Dict[str, Any]:
        return {
            "resolution": self.state["resolution"],
            "graphics_preset": self.state["graphics_preset"],
            "ray_tracing": self.state["ray_tracing"],
            "upscaling": self.state["dlss_fsr"],
        }
