"""
Universal Inference Client for Microsoft FARA LLM (GGUF).
=========================================================
Supports fast local GPU execution via llama-server (OpenAI-compatible REST API)
with automatic fallback to llama-cli.

Usage:
    from fara_client import FARA, generate

    res = generate("Explain cybersecurity incident response in one sentence.")
    print(res.text)
"""

from __future__ import annotations

import os
import sys
import time
import json
import re
import subprocess
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any


DEFAULT_DIR = r"c:\Users\ASUS\Downloads\LLada"
DEFAULT_MODEL = os.path.join(DEFAULT_DIR, "FARA", "microsoft_Fara-7B-Q4_K_M.gguf")
DEFAULT_BIN = os.path.join(DEFAULT_DIR, "llama_cpp", "bin", "llama-cli.exe")
DEFAULT_SERVER = os.path.join(DEFAULT_DIR, "llama_cpp", "bin", "llama-server.exe")
DEFAULT_PORT = 8081


@dataclass
class GenerationResult:
    text: str
    total_time_ms: Optional[float] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    return_code: int = 0
    raw_output: str = ""

    def __str__(self) -> str:
        return self.text


class FARA:
    """
    Client for Microsoft FARA 7B GGUF Model.
    Automatically leverages llama-server on GPU or falls back to llama-cli.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        bin_path: Optional[str] = None,
        server_path: Optional[str] = None,
        port: int = DEFAULT_PORT,
        n_gpu_layers: Optional[int] = None,
        ctx_size: int = 4096,
        auto_server: bool = True,
    ):
        self.model_path = model_path or os.getenv("FARA_MODEL", DEFAULT_MODEL)
        self.bin_path = bin_path or os.getenv("FARA_BIN", DEFAULT_BIN)
        self.server_path = server_path or os.getenv("FARA_SERVER", DEFAULT_SERVER)
        self.port = port
        self.n_gpu_layers = n_gpu_layers if n_gpu_layers is not None else int(os.getenv("FARA_GPU_LAYERS", "33"))
        self.ctx_size = ctx_size
        self.auto_server = auto_server
        self._server_process: Optional[subprocess.Popen] = None

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"FARA GGUF model not found at: {self.model_path}\n"
                f"Please ensure microsoft_Fara-7B-Q4_K_M.gguf exists or set FARA_MODEL."
            )

    def is_server_ready(self) -> bool:
        """Check if llama-server is healthy and ready to serve requests."""
        url = f"http://127.0.0.1:{self.port}/health"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FARA-Client"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data.get("status") == "ok"
        except Exception:
            return False
        return False

    def ensure_server(self, timeout_sec: int = 30) -> bool:
        """Ensure llama-server is running on the specified port."""
        if self.is_server_ready():
            return True

        if not self.auto_server:
            return False

        if not os.path.exists(self.server_path):
            return False

        # Launch llama-server in background
        cmd = [
            self.server_path,
            "-m", self.model_path,
            "-ngl", str(self.n_gpu_layers),
            "-c", str(self.ctx_size),
            "-np", "1",
            "--port", str(self.port),
        ]

        try:
            self._server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except Exception as e:
            print(f"[FARA] Warning: Could not auto-launch llama-server ({e}). Falling back to CLI.")
            return False

        # Poll until healthy
        t0 = time.time()
        while time.time() - t0 < timeout_sec:
            if self.is_server_ready():
                return True
            time.sleep(1.0)

        return False

    def _query_server(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.1,
    ) -> GenerationResult:
        """Query via local OpenAI-compatible REST server endpoint."""
        url = f"http://127.0.0.1:{self.port}/v1/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "FARA-Client"},
        )

        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=60) as resp:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            res_obj = json.loads(resp.read().decode("utf-8"))

        content = res_obj["choices"][0]["message"]["content"]
        usage = res_obj.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", len(prompt.split()))
        completion_tokens = usage.get("completion_tokens", len(content.split()))

        return GenerationResult(
            text=content,
            total_time_ms=round(elapsed_ms, 2),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            return_code=0,
            raw_output=content,
        )

    def _query_cli(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.1,
    ) -> GenerationResult:
        """Query directly using llama-cli subprocess."""
        if not os.path.exists(self.bin_path):
            raise FileNotFoundError(f"llama-cli binary not found at: {self.bin_path}")

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        cmd = [
            self.bin_path,
            "-m", self.model_path,
            "-ngl", str(self.n_gpu_layers),
            "-c", str(self.ctx_size),
            "-p", full_prompt,
            "-n", str(max_tokens),
            "--temp", str(temperature),
            "--single-turn",
            "--no-display-prompt",
        ]

        t0 = time.perf_counter()
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        output = proc.stdout
        # Strip banner and REPL artifacts
        # llama-cli prints generation after prompt or between prompt marker and stats
        cleaned = output
        if "> " in cleaned:
            parts = cleaned.split("> ", 1)
            if len(parts) > 1:
                cleaned = parts[1]
                # Strip the prompt line if echoed
                lines = cleaned.split("\n", 1)
                if len(lines) > 1:
                    cleaned = lines[1]
        
        # Remove prompt timing line
        cleaned = re.sub(r'\[\s*Prompt:[^\]]*\]', '', cleaned)
        cleaned = re.sub(r'Exiting\.\.\.', '', cleaned)
        cleaned = cleaned.strip()

        p_tokens = len(full_prompt.split())
        c_tokens = len(cleaned.split())

        return GenerationResult(
            text=cleaned,
            total_time_ms=round(elapsed_ms, 2),
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            return_code=proc.returncode,
            raw_output=output,
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.1,
    ) -> GenerationResult:
        """
        Generate completion using FARA.
        Prefers running llama-server (fastest, keeps model resident in VRAM);
        falls back to direct llama-cli execution if server is unavailable.
        """
        if self.is_server_ready() or self.ensure_server():
            try:
                return self._query_server(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except Exception as e:
                print(f"[FARA] Server query failed ({e}), falling back to llama-cli...")

        return self._query_cli(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )


def generate(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 512,
    temperature: float = 0.1,
) -> GenerationResult:
    """Convenience functional interface for FARA generation."""
    client = FARA()
    return client.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
    )
