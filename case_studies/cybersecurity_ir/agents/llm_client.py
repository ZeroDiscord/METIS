"""
Unified LLM Client for METIS Case Studies
==========================================
Provides a multi-provider interface for live LLM inference:
- OpenAI (GPT-4o, GPT-4o-mini, o1, etc.)
- OpenAI-compatible local endpoints (Ollama, vLLM, LM Studio)
- Anthropic (Claude 3.5 Sonnet, Claude 3 Haiku, etc.)
- Google Gemini (gemini-1.5-pro, gemini-2.0-flash, etc.)

Features:
- Robust JSON extraction & schema validation
- Token usage tracking (prompt, completion, total)
- Exact wall-clock latency measurement
- Graceful fallbacks and clear error diagnostics
"""

from __future__ import annotations

import os
import re
import json
import time
from typing import Any, Dict, Optional, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def extract_json_from_response(text: str) -> dict:
    """
    Extract a valid JSON object from LLM output text, handling:
    - Markdown code fences (```json ... ```)
    - Preamble / postamble commentary and tool call annotations
    - Inline comments (// ...)
    - Trailing commas or common formatting quirks
    """
    cleaned = text.strip()

    def _sanitize_json_str(s: str) -> str:
        # Strip C-style inline comments: // ...
        s = re.sub(r'//.*', '', s)
        # Strip trailing commas before closing braces/brackets
        s = re.sub(r',\s*([\]}])', r'\1', s)
        return s.strip()

    # 1. Look for ```json ... ``` or ``` ... ``` code blocks
    fence_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    fence_matches = re.findall(fence_pattern, cleaned)
    if fence_matches:
        for match in fence_matches:
            try:
                candidate = _sanitize_json_str(match)
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    # 2. Try direct json.loads (with comment & trailing comma stripping)
    try:
        candidate = _sanitize_json_str(cleaned)
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # 3. Find first balanced curly brace { ... } block
    def _extract_first_json_object(s: str) -> Optional[str]:
        start = s.find('{')
        if start == -1:
            return None
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(s)):
            c = s[i]
            if escape:
                escape = False
                continue
            if c == '\\':
                escape = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if not in_string:
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        return s[start : i + 1]
        return None

    first_obj = _extract_first_json_object(cleaned)
    if first_obj:
        try:
            return json.loads(_sanitize_json_str(first_obj))
        except json.JSONDecodeError:
            pass

    # Fallback to outermost curly braces
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = cleaned[first_brace : last_brace + 1]
        try:
            return json.loads(_sanitize_json_str(candidate))
        except json.JSONDecodeError:
            pass

    # 4. Fallback: Extract structured security entities from raw text / partial JSON
    extracted = {}

    actor_match = re.search(r'["\']?(?:attributed_group|actor)["\']?\s*[:=]\s*["\']?([A-Za-z0-9_-]+)["\']?', cleaned, re.IGNORECASE)
    if actor_match:
        extracted["attributed_group"] = actor_match.group(1).upper()
    else:
        grp_match = re.search(r'\b(G\d{4}|INSIDER)\b', cleaned, re.IGNORECASE)
        if grp_match:
            extracted["attributed_group"] = grp_match.group(1).upper()

    techniques = re.findall(r'\b(T\d{4}(?:\.\d{3})?)\b', cleaned)
    if techniques:
        extracted["kill_chain"] = list(dict.fromkeys(techniques))

    hosts = re.findall(r'\b([A-Z0-9]+(?:-[A-Z0-9]+)+)\b', cleaned)
    valid_hosts = [h for h in hosts if any(k in h for k in ["WS", "WORKSTATION", "SERVER", "DC", "PROD", "MON", "CTRL", "NAS", "GW", "DB", "HOST"])]
    if valid_hosts:
        extracted["compromised_hosts"] = list(dict.fromkeys(valid_hosts))

    conf_match = re.search(r'["\']?confidence["\']?\s*[:=]\s*([0-9]*\.?[0-9]+)', cleaned)
    if conf_match:
        try:
            extracted["confidence"] = float(conf_match.group(1))
        except ValueError:
            pass

    if extracted:
        return extracted

    return {}


class LLMClient:
    """Unified client for live model inference across providers."""

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.0,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model = model
        self.temperature = temperature
        self.api_key = api_key
        self.base_url = base_url
        self._llada_engine = None
        self._fara_engine = None

        # Infer provider
        self.provider = self._detect_provider(model, base_url)

    def _detect_provider(self, model: str, base_url: Optional[str]) -> str:
        if base_url and ("localhost" in base_url or "127.0.0.1" in base_url):
            return "openai_compatible"
        if base_url and "groq" in base_url:
            return "groq"
        m = model.lower()
        if "fara" in m:
            return "fara"
        if "llada" in m or "diffusion" in m:
            return "llada"
        if "groq" in m or m.startswith("qwen/"):
            return "groq"
        if os.getenv("GROQ_API_KEY") and (self.api_key and self.api_key.startswith("gsk_") or "qwen" in m):
            return "groq"
        if "claude" in m:
            return "anthropic"
        if "gemini" in m:
            return "gemini"
        if "ollama" in m:
            return "ollama"
        return "openai"

    def query(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_hint: Optional[str] = None,
    ) -> Tuple[dict, dict]:
        """
        Execute query against live LLM.
        Returns:
            (parsed_json_dict, usage_metadata)
            usage_metadata contains: prompt_tokens, completion_tokens, total_tokens, latency_seconds, model
        """
        t0 = time.time()

        if self.provider == "fara":
            raw_text, usage = self._query_fara(system_prompt, user_prompt)
        elif self.provider == "llada":
            raw_text, usage = self._query_llada(system_prompt, user_prompt)
        elif self.provider == "groq":
            raw_text, usage = self._query_groq(system_prompt, user_prompt)
        elif self.provider in ("openai", "openai_compatible", "ollama"):
            raw_text, usage = self._query_openai(system_prompt, user_prompt)
        elif self.provider == "anthropic":
            raw_text, usage = self._query_anthropic(system_prompt, user_prompt)
        elif self.provider == "gemini":
            raw_text, usage = self._query_gemini(system_prompt, user_prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

        latency = time.time() - t0
        parsed = extract_json_from_response(raw_text)

        metadata = {
            "model": self.model,
            "provider": self.provider,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)),
            "latency_seconds": round(latency, 3),
            "raw_text": raw_text,
        }

        return parsed, metadata

    def _query_groq(self, system_prompt: str, user_prompt: str) -> Tuple[str, dict]:
        from groq import Groq

        api_key = self.api_key if (self.api_key and self.api_key.startswith("gsk_")) else os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. Please set the GROQ_API_KEY environment variable "
                "or pass api_key to use Groq live LLM mode."
            )

        client = Groq(api_key=api_key)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = None
        for attempt in range(5):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    response_format={"type": "json_object"},
                    max_tokens=600,
                )
                break
            except Exception as e:
                err_str = str(e).lower()
                if "rate_limit" in err_str and attempt < 4:
                    wait_time = 4 + (attempt * 4)
                    time.sleep(wait_time)
                    continue
                raise

        content = response.choices[0].message.content or "{}"

        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }
    def _query_llada(self, system_prompt: str, user_prompt: str) -> Tuple[str, dict]:
        if not hasattr(self, "_llada_engine") or self._llada_engine is None:
            try:
                from llada_client import LLaDA
            except ImportError:
                import sys
                cand_paths = [
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    r"c:\Users\ASUS\Downloads\LLada"
                ]
                for cp in cand_paths:
                    if cp not in sys.path:
                        sys.path.insert(0, cp)
                from llada_client import LLaDA
            self._llada_engine = LLaDA()

        if system_prompt:
            prompt = f"{system_prompt.strip()}\n\nIncident Investigation:\n{user_prompt}\n\nRespond ONLY with valid JSON:"
        else:
            prompt = f"Analyze incident:\n{user_prompt}\nProvide valid JSON output:"

        res = self._llada_engine.generate(
            prompt=prompt,
            system_prompt=None,
            steps=32,
            temperature=self.temperature if self.temperature > 0 else 0.7,
            dynamic_allocation=True,
        )
        content = res.text
        p_tokens = len(prompt.split()) + (len(system_prompt.split()) if system_prompt else 0)
        c_tokens = 128
        usage = {
            "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens,
            "total_tokens": p_tokens + c_tokens,
            "latency_ms": res.total_time_ms or 0.0,
            "step_time_ms": res.step_time_ms or 0.0,
        }
        return content, usage

    def _query_fara(self, system_prompt: str, user_prompt: str) -> Tuple[str, dict]:
        if not hasattr(self, "_fara_engine") or self._fara_engine is None:
            try:
                from fara_client import FARA
            except ImportError:
                import sys
                cand_paths = [
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    r"c:\Users\ASUS\Downloads\LLada"
                ]
                for cp in cand_paths:
                    if cp not in sys.path:
                        sys.path.insert(0, cp)
                from fara_client import FARA
            self._fara_engine = FARA()

        res = self._fara_engine.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=512,
            temperature=self.temperature if self.temperature > 0 else 0.1,
        )
        content = res.text
        usage = {
            "prompt_tokens": res.prompt_tokens,
            "completion_tokens": res.completion_tokens,
            "total_tokens": res.prompt_tokens + res.completion_tokens,
            "latency_ms": res.total_time_ms or 0.0,
        }
        return content, usage

    def _query_openai(self, system_prompt: str, user_prompt: str) -> Tuple[str, dict]:
        import openai

        api_key = self.api_key if (self.api_key and not self.api_key.startswith("gsk_")) else os.getenv("OPENAI_API_KEY", "")
        base_url = self.base_url or os.getenv("OPENAI_BASE_URL", None)

        if not api_key and not base_url:
            raise ValueError(
                "OPENAI_API_KEY is not set. Please set the OPENAI_API_KEY environment variable "
                "or pass api_key to use live LLM mode."
            )

        client = openai.OpenAI(
            api_key=api_key or "sk-dummy-for-local",
            base_url=base_url,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }

        # Enable JSON object response format for models that support it
        if "o1" not in self.model and "o3" not in self.model and "llada" not in self.model.lower():
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or "{}"

        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }
        return content, usage

    def _query_anthropic(self, system_prompt: str, user_prompt: str) -> Tuple[str, dict]:
        import anthropic

        api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set.")

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=self.temperature,
            max_tokens=4096,
        )

        text = response.content[0].text if response.content else "{}"
        usage = {
            "prompt_tokens": response.usage.input_tokens if response.usage else 0,
            "completion_tokens": response.usage.output_tokens if response.usage else 0,
            "total_tokens": (response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0,
        }
        return text, usage

    def _query_gemini(self, system_prompt: str, user_prompt: str) -> Tuple[str, dict]:
        import google.generativeai as genai

        api_key = self.api_key or os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system_prompt,
        )
        response = model.generate_content(
            user_prompt,
            generation_config={"temperature": self.temperature, "response_mime_type": "application/json"},
        )
        text = response.text or "{}"
        # Approximate tokens if usage metadata not directly provided
        usage = {
            "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", len(user_prompt) // 4),
            "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", len(text) // 4),
            "total_tokens": getattr(response.usage_metadata, "total_token_count", (len(user_prompt) + len(text)) // 4),
        }
        return text, usage
