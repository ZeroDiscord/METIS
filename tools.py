from langchain_core.tools import tool

@tool
def performance_tool():
    """Check the current GTA V performance, including FPS and stuttering."""
    return {
        "fps_before": 90,
        "fps_now": 45,
        "frametime": "highly variable",
        "stuttering": True,
    }


@tool
def gpu_monitor_tool():
    """Check GPU utilization, temperature, and VRAM usage."""
    return {
        "gpu_usage": "97%",
        "gpu_temperature": "62°C",
        "vram_usage": "7.2 / 12 GB",
        "gpu_status": "normal_temperature",
    }


@tool
def cpu_monitor_tool():
    """Check CPU utilization, game-thread utilization, and CPU temperature."""
    return {
        "overall_cpu_usage": "65%",
        "game_thread_usage": "100%",
        "background_cpu_usage": "normal",
        "cpu_temperature": "68°C",
    }


@tool
def game_settings_tool():
    """Check GTA V graphics settings and whether they were recently changed."""
    return {
        "resolution": "1920x1080",
        "graphics_preset": "Very High",
        "ray_tracing": False,
        "settings_changed_recently": False,
    }


@tool
def recent_changes_tool():
    """Check recent GTA V, graphics driver, Windows, and mod changes."""
    return {
        "game_update": "GTA V updated yesterday",
        "graphics_driver_update": False,
        "windows_update": False,
        "mods_changed": False,
    }


@tool
def game_logs_tool():
    """Check GTA V logs for warnings and errors related to the performance problem."""
    return {
        "warnings": [
            "Repeated asset-streaming warning",
            "Streaming request delayed",
            "Game thread waiting for asset data",
        ],
        "errors": [],
        "warning_frequency": "high",
    }