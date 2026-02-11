#!/usr/bin/env python3
"""
LLM Engine: Text-only LLM interface (future-proof for vision)
==============================================================
Provides a unified interface for calling text LLMs via Ollama.
Designed with a clean abstraction so a vision LLM can be plugged in later.

Supports:
  - Ollama text generation (qwen2.5:7b, llama3.2:3b, etc.)
  - Robust JSON parsing with fallbacks
  - Retry logic for transient failures
  - generate_with_image() stub for future vision LLM integration
"""

from __future__ import annotations

import ast
import json
import re
import time
from typing import Any, Dict, Optional

import requests

try:
    from json_repair import repair_json
    JSON_REPAIR_AVAILABLE = True
except ImportError:
    JSON_REPAIR_AVAILABLE = False


class LLMEngine:
    """
    Text-only LLM interface via Ollama.

    Usage:
        engine = LLMEngine(model="qwen2.5:7b")
        response = engine.generate("Extract these fields ...")
        data = engine.parse_json(response)
    """

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
        timeout: int = 300,
        max_retries: int = 2,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens

    # ------------------------------------------------------------------
    # Text generation
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate text using Ollama.

        Args:
            prompt: User prompt.
            system: Optional system prompt.
            temperature: Override default temperature.
            max_tokens: Override default max_tokens.

        Returns:
            Model response text.
        """
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        # Merge system + user into a single prompt for the /api/generate endpoint
        full_prompt = f"{system}\n\n{prompt}" if system else prompt

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temp,
                "num_predict": tokens,
            },
        }

        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                return resp.json().get("response", "")
            except (requests.RequestException, KeyError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    print(f"  [LLM] Attempt {attempt} failed ({exc}), retrying in {wait}s ...")
                    time.sleep(wait)

        raise RuntimeError(
            f"LLM generation failed after {self.max_retries} attempts: {last_error}"
        )

    # ------------------------------------------------------------------
    # GPU memory management
    # ------------------------------------------------------------------

    def unload_model(self) -> None:
        """Unload the model from Ollama to free GPU memory.

        Uses multiple strategies and verifies GPU memory is actually freed:
          1. `ollama stop <model>` CLI command
          2. API `keep_alive: 0` as fallback
          3. Polls nvidia-smi to confirm GPU memory was released
        The model will be reloaded automatically on the next generate() call.
        """
        import subprocess

        # Strategy 1: CLI stop
        try:
            subprocess.run(
                ["ollama", "stop", self.model],
                capture_output=True, text=True, timeout=30,
            )
        except Exception:
            pass

        # Strategy 2: API keep_alive=0 (belt-and-suspenders)
        try:
            requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": "", "keep_alive": 0},
                timeout=10,
            )
        except Exception:
            pass

        # Strategy 3: Wait and verify GPU memory is freed
        # Poll nvidia-smi for up to 15 seconds to confirm Ollama released VRAM
        for attempt in range(6):
            time.sleep(2 + attempt)  # 2, 3, 4, 5, 6, 7 seconds
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-compute-apps=pid,used_memory",
                     "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=10,
                )
                # Check if any process is using >1 GiB (likely the model)
                ollama_gpu_mb = 0
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        parts = line.split(",")
                        if len(parts) >= 2:
                            mem_str = parts[1].strip().replace("MiB", "").strip()
                            try:
                                mem_mb = int(mem_str)
                                if mem_mb > 1000:
                                    ollama_gpu_mb = max(ollama_gpu_mb, mem_mb)
                            except ValueError:
                                pass
                if ollama_gpu_mb == 0:
                    print(f"  [LLM] Model {self.model} unloaded from GPU")
                    return
                elif attempt < 5:
                    # Retry the stop command
                    try:
                        subprocess.run(
                            ["ollama", "stop", self.model],
                            capture_output=True, text=True, timeout=10,
                        )
                    except Exception:
                        pass
            except Exception:
                pass

        print(f"  [LLM] Model {self.model} unload requested (may still be releasing)")

    # ------------------------------------------------------------------
    # Vision stub (future use)
    # ------------------------------------------------------------------

    def generate_with_image(
        self,
        prompt: str,
        image_path: str,
        system: Optional[str] = None,
    ) -> str:
        """
        Generate text using a vision LLM that can see an image.

        NOTE: This is a STUB for future implementation.
        When a vision model is available (e.g. Groq Llama 4 Scout, GPT-4V),
        implement this method to send the image alongside the prompt.

        Raises:
            NotImplementedError: Always, until a vision model is configured.
        """
        raise NotImplementedError(
            "Vision LLM is not yet configured. "
            "To add vision support, implement this method in llm_engine.py "
            "using a vision-capable model (e.g. Groq Llama 4 Scout, GPT-4V)."
        )

    # ------------------------------------------------------------------
    # JSON parsing
    # ------------------------------------------------------------------

    def parse_json(self, text: str) -> Dict[str, Any]:
        """
        Extract a JSON object from LLM response text.

        Tries in order:
          1. Direct json.loads()
          2. Regex extraction of {...}
          3. json_repair library
          4. Python ast.literal_eval
          5. Trailing-comma removal + retry
          6. Empty dict fallback
        """
        if not text or not text.strip():
            return {}

        cleaned = text.strip()

        # Strip markdown code fence wrappers
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        cleaned = cleaned.strip()

        # 1. Direct parse
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 2. Regex extraction
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            candidate = match.group(0)
            # Remove JS-style single-line comments
            candidate = re.sub(r'//.*?$', '', candidate, flags=re.MULTILINE)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

            # 3. json_repair
            if JSON_REPAIR_AVAILABLE:
                try:
                    repaired = repair_json(candidate, return_objects=True)
                    if isinstance(repaired, dict):
                        return repaired
                except Exception:
                    pass

            # 4. ast.literal_eval (handles single quotes)
            try:
                obj = ast.literal_eval(candidate)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass

            # 5. Trailing comma removal
            no_trailing = re.sub(r',\s*([}\]])', r'\1', candidate)
            try:
                return json.loads(no_trailing)
            except json.JSONDecodeError:
                pass

        # 6. Fallback
        return {}
