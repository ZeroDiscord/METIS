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
    - Preamble / postamble commentary
    - Trailing commas or common formatting quirks
    """
    cleaned = text.strip()

    # 1. Look for ```json ... ``` or ``` ... ``` code blocks
    fence_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    fence_matches = re.findall(fence_pattern, cleaned)
    if fence_matches:
        for match in fence_matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

    # 2. Try direct json.loads
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 3. Find outermost curly braces { ... }
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = cleaned[first_brace : last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # Try to fix common trailing comma issue: , } -> }
            sanitized = re.sub(r",\s*([\]}])", r"\1", candidate)
            try:
                return json.loads(sanitized)
            except json.JSONDecodeError:
                pass

    raise ValueError(f"Failed to extract valid JSON from LLM response:\n{text[:500]}...")


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

        # Infer provider
        self.provider = self._detect_provider(model, base_url)

    def _detect_provider(self, model: str, base_url: Optional[str]) -> str:
        if base_url and ("localhost" in base_url or "127.0.0.1" in base_url):
            return "openai_compatible"
        if base_url and "groq" in base_url:
            return "groq"
        m = model.lower()
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

        if self.provider == "groq":
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
        if "o1" not in self.model and "o3" not in self.model:
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
