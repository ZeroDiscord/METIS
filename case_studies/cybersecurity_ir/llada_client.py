"""
Standalone, single-file drop-in client for LLaDA Diffusion inference.
Copy this file into any project and use immediately:

    from llada_client import LLaDA, generate

    text = generate("Explain diffusion models in simple terms.")
    print(text)
"""
import os
import sys
import re
import subprocess
from dataclasses import dataclass
from typing import Optional, Generator, Callable

DEFAULT_DIR = r"c:\Users\ASUS\Downloads\LLada"
MSVC_BIN = os.path.join(DEFAULT_DIR, "llama_src", "build_msvc", "bin", "Release", "llama-diffusion-cli.exe")
MINGW_BIN = os.path.join(DEFAULT_DIR, "llama_src", "build", "bin", "llama-diffusion-cli.exe")
DEFAULT_BIN = MSVC_BIN if os.path.exists(MSVC_BIN) else MINGW_BIN
DEFAULT_MODEL = os.path.join(DEFAULT_DIR, "LLaDA-MoE-7B-A1B-Instruct.i1-Q4_K_M.gguf")

@dataclass
class GenerationResult:
    text: str
    total_time_ms: Optional[float] = None
    step_time_ms: Optional[float] = None
    steps: int = 32
    return_code: int = 0
    raw_output: str = ""

    def __str__(self) -> str:
        return self.text

class LLaDA:
    """
    Universal Inference Client for LLaDA Diffusion LLM.
    Callable from any directory or application. Supports NVIDIA GPU CUDA acceleration.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        bin_path: Optional[str] = None,
        threads: int = 16,
        n_gpu_layers: int = 33,
    ):
        self.model_path = model_path or os.getenv("LLADA_MODEL", DEFAULT_MODEL)
        self.bin_path = bin_path or os.getenv("LLADA_BIN", DEFAULT_BIN)
        self.threads = threads
        self.n_gpu_layers = n_gpu_layers

        if not os.path.exists(self.bin_path):
            raise FileNotFoundError(
                f"llama-diffusion-cli binary not found at: {self.bin_path}\n"
                f"Set environment variable LLADA_BIN or pass bin_path to LLaDA()."
            )

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"LLaDA GGUF model not found at: {self.model_path}\n"
                f"Set environment variable LLADA_MODEL or pass model_path to LLaDA()."
            )

    def _prepare_env(self) -> dict:
        env = os.environ.copy()
        bin_dir = os.path.dirname(self.bin_path)
        if bin_dir not in env.get("PATH", ""):
            env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
        env["PYTHONIOENCODING"] = "utf-8"
        return env

    def _build_cmd(
        self,
        prompt: str,
        steps: int = 32,
        block_length: int = 32,
        max_tokens: int = 64,
        temperature: float = 0.8,
        algorithm: int = 4,
        system_prompt: Optional[str] = None,
        visual: bool = False,
    ) -> list:
        cmd = [
            self.bin_path,
            "-m", self.model_path,
            "-p", prompt,
            "-ub", str(max_tokens),
            "--diffusion-block-length", str(block_length),
            "--diffusion-steps", str(steps),
            "-t", str(self.threads),
            "--temp", str(temperature),
            "--diffusion-algorithm", str(algorithm),
        ]
        if self.n_gpu_layers > 0:
            cmd.extend(["-ngl", str(self.n_gpu_layers)])
        if system_prompt:
            cmd.extend(["-sys", system_prompt])
        if visual:
            cmd.append("--diffusion-visual")
        return cmd

    @staticmethod
    def _parse_output(raw_output: str, steps: int, return_code: int) -> GenerationResult:
        time_line = re.search(r'total time:\s*([0-9\.]+)ms,\s*time per step:\s*([0-9\.]+)ms[^\n]*\n', raw_output)
        if time_line:
            total_time_ms = float(time_line.group(1))
            step_time_ms = float(time_line.group(2))
            after_time = raw_output[time_line.end():]
            cleaned_text = re.sub(r'^[0-9\.]+\s+[IWE]\s*\n?', '', after_time.strip(), flags=re.MULTILINE).strip()
            return GenerationResult(
                text=cleaned_text,
                total_time_ms=total_time_ms,
                step_time_ms=step_time_ms,
                steps=steps,
                return_code=return_code,
                raw_output=raw_output,
            )
        return GenerationResult(
            text=raw_output.strip(),
            steps=steps,
            return_code=return_code,
            raw_output=raw_output,
        )

    def generate(
        self,
        prompt: str,
        steps: int = 16,
        block_length: int = 32,
        max_tokens: int = 64,
        temperature: float = 0.8,
        algorithm: int = 4,
        system_prompt: Optional[str] = None,
        on_progress: Optional[Callable[[str], None]] = None,
        dynamic_allocation: bool = True,
    ) -> GenerationResult:
        """
        Runs synchronous inference and returns the parsed generated text.
        Calculates dynamic sequence length (n_prompt + 128) by default to prevent C++ aborts.
        """
        if dynamic_allocation:
            full_text = f"{system_prompt}\n{prompt}" if system_prompt else prompt
            tokens = re.findall(r"\w+|[^\w\s]", full_text)
            n_prompt_est = max(len(tokens), int(len(full_text) / 2.8)) + 16
            target_len = n_prompt_est + 128

            # Block-based alignment: max_length must be divisible by block_length (32),
            # and steps must be divisible by num_blocks (max_length / block_length)
            if target_len <= 256:
                num_blocks = 8
                dyn_ub = 256
                dyn_steps = max(steps, 16)
                dyn_steps = ((dyn_steps + num_blocks - 1) // num_blocks) * num_blocks
            elif target_len <= 512:
                num_blocks = 16
                dyn_ub = 512
                dyn_steps = max(steps, 16)
                dyn_steps = ((dyn_steps + num_blocks - 1) // num_blocks) * num_blocks
            else:
                num_blocks = 32
                dyn_ub = 1024
                dyn_steps = max(steps, 32)
                dyn_steps = ((dyn_steps + num_blocks - 1) // num_blocks) * num_blocks
        else:
            dyn_ub = max_tokens
            dyn_steps = steps

        cmd = self._build_cmd(
            prompt=prompt,
            steps=dyn_steps,
            block_length=block_length,
            max_tokens=dyn_ub,
            temperature=temperature,
            algorithm=algorithm,
            system_prompt=system_prompt,
            visual=False,
        )
        env = self._prepare_env()

        proc = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        captured = []
        for line in proc.stdout:
            captured.append(line)
            if on_progress:
                on_progress(line)

        proc.wait()
        full_output = "".join(captured)
        return self._parse_output(full_output, steps, proc.returncode)

    def stream_lines(
        self,
        prompt: str,
        steps: int = 32,
        block_length: int = 32,
        max_tokens: int = 64,
        temperature: float = 0.8,
        algorithm: int = 4,
        system_prompt: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        Streams raw output lines as the diffusion process proceeds.
        """
        cmd = self._build_cmd(
            prompt=prompt,
            steps=steps,
            block_length=block_length,
            max_tokens=max_tokens,
            temperature=temperature,
            algorithm=algorithm,
            system_prompt=system_prompt,
            visual=False,
        )
        env = self._prepare_env()

        proc = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        for line in proc.stdout:
            yield line

        proc.wait()

def generate(
    prompt: str,
    steps: int = 32,
    block_length: int = 32,
    max_tokens: int = 64,
    temperature: float = 0.8,
    algorithm: int = 4,
    system_prompt: Optional[str] = None,
    model_path: Optional[str] = None,
    bin_path: Optional[str] = None,
) -> str:
    """
    Convenience one-liner function to get generated text from any script.
    """
    client = LLaDA(model_path=model_path, bin_path=bin_path)
    result = client.generate(
        prompt=prompt,
        steps=steps,
        block_length=block_length,
        max_tokens=max_tokens,
        temperature=temperature,
        algorithm=algorithm,
        system_prompt=system_prompt,
    )
    return result.text

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LLaDA Drop-in Client CLI")
    parser.add_argument("prompt", nargs="?", default="Hello, what can you do?", help="Input prompt")
    parser.add_argument("--tokens", "-ub", type=int, default=64, help="Tokens / length")
    parser.add_argument("--steps", "-s", type=int, default=32, help="Steps")
    args = parser.parse_args()

    print(f"Prompt: {args.prompt}")
    res = LLaDA().generate(prompt=args.prompt, max_tokens=args.tokens, steps=args.steps)
    print("\nResult:")
    print(res.text)
    if res.total_time_ms:
        print(f"\n[Generated in {res.total_time_ms:.1f}ms ({res.step_time_ms:.1f}ms/step)]")
