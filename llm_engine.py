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
import base64
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

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
        vision_model: Optional[str] = None,
        vision_describer_model: Optional[str] = None,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.vision_model = vision_model  # e.g. "llava:7b" for Ollama VLM
        # Small VLM for describing image regions (crops); if None, use vision_model
        self.vision_describer_model = vision_describer_model

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

        # Merge system + user into a single prompt for Ollama /api/generate
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
                if resp.status_code == 404:
                    # Ollama 0.15+ or some setups: try /api/chat, then /v1/chat/completions
                    try:
                        return self._generate_via_chat(full_prompt, temp, tokens)
                    except requests.HTTPError as e:
                        if e.response is not None and e.response.status_code == 404:
                            return self._generate_via_openai_compat(full_prompt, temp, tokens)
                        raise
                resp.raise_for_status()
                return resp.json().get("response", "")
            except (requests.RequestException, KeyError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    print(f"  [LLM] Attempt {attempt} failed ({exc}), retrying in {wait}s ...")
                    time.sleep(wait)

        hint = ""
        if last_error and "404" in str(last_error):
            hint = (
                " All Ollama endpoints returned 404. On this machine, ensure the Ollama "
                "server is running (ollama serve) and is what is listening on port 11434. "
                "Check: curl -s http://localhost:11434/api/tags"
            )
        raise RuntimeError(
            f"LLM generation failed after {self.max_retries} attempts: {last_error}{hint}"
        )

    def _generate_via_chat(
        self, prompt: str, temperature: float, max_tokens: int
    ) -> str:
        """Fallback: Ollama /api/chat when /api/generate returns 404."""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        msg = data.get("message") or {}
        content = msg.get("content")
        if isinstance(content, list):
            return " ".join(
                p.get("text", "") for p in content if isinstance(p, dict)
            ).strip()
        return (content or "").strip()

    def _generate_via_openai_compat(
        self, prompt: str, temperature: float, max_tokens: int
    ) -> str:
        """Fallback: OpenAI-compatible /v1/chat/completions (Ollama 0.15.x)."""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        msg = choices[0].get("message") or {}
        return (msg.get("content") or "").strip()

    # ------------------------------------------------------------------
    # GPU memory management (intelligent load/unload with wait time)
    # ------------------------------------------------------------------

    UNLOAD_WAIT_SECONDS = 8  # Time to wait after stop so GPU can release VRAM
    UNLOAD_POLL_INTERVAL = 4  # Seconds between nvidia-smi checks
    UNLOAD_MAX_POLLS = 10    # Max ~40s waiting for GPU to free

    def _stop_ollama_model(self, model_name: str) -> None:
        """Stop one Ollama model via CLI and API."""
        import subprocess
        try:
            subprocess.run(
                ["ollama", "stop", model_name],
                capture_output=True, text=True, timeout=30,
            )
        except Exception:
            pass
        try:
            requests.post(
                f"{self.base_url}/api/generate",
                json={"model": model_name, "prompt": "", "keep_alive": 0},
                timeout=10,
            )
        except Exception:
            pass

    def unload_model(self) -> None:
        """Unload text and vision models from Ollama to free GPU memory.

        Stops both models (if vision_model set), waits UNLOAD_WAIT_SECONDS,
        then polls nvidia-smi until no process uses >1 GiB or max polls reached.
        Gives the GPU time to actually release VRAM before OCR/LLM load.
        """
        import subprocess

        # Stop both text and vision models so OCR has full GPU
        self._stop_ollama_model(self.model)
        if self.vision_model:
            self._stop_ollama_model(self.vision_model)
            print(f"  [LLM] Stopped {self.model} and {self.vision_model}, waiting {self.UNLOAD_WAIT_SECONDS}s for GPU...")
        else:
            print(f"  [LLM] Stopped {self.model}, waiting {self.UNLOAD_WAIT_SECONDS}s for GPU...")

        time.sleep(self.UNLOAD_WAIT_SECONDS)

        for attempt in range(self.UNLOAD_MAX_POLLS):
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-compute-apps=pid,used_memory",
                     "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=10,
                )
                high_mb = 0
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        parts = line.split(",")
                        if len(parts) >= 2:
                            mem_str = parts[1].strip().replace("MiB", "").strip()
                            try:
                                mem_mb = int(mem_str)
                                if mem_mb > 1000:
                                    high_mb = max(high_mb, mem_mb)
                            except ValueError:
                                pass
                if high_mb == 0:
                    print(f"  [LLM] GPU free (models unloaded)")
                    return
                if attempt < self.UNLOAD_MAX_POLLS - 1:
                    time.sleep(self.UNLOAD_POLL_INTERVAL)
                    self._stop_ollama_model(self.model)
                    if self.vision_model:
                        self._stop_ollama_model(self.vision_model)
            except Exception:
                pass

        print(f"  [LLM] Unload requested (GPU may still be releasing)")

    def unload_text_model(self) -> None:
        """Unload only the text model (e.g. before loading VLM for vision pass)."""
        self._stop_ollama_model(self.model)
        print(f"  [LLM] Stopped {self.model}, waiting {self.UNLOAD_WAIT_SECONDS}s for GPU...")
        time.sleep(self.UNLOAD_WAIT_SECONDS)

    def unload_vision_model(self) -> None:
        """Unload only the vision model (e.g. after vision pass so text LLM can load again)."""
        if not self.vision_model:
            return
        self._stop_ollama_model(self.vision_model)
        print(f"  [VLM] Stopped {self.vision_model}, waiting {self.UNLOAD_WAIT_SECONDS}s...")

    def unload_describer_model(self) -> None:
        """Unload the describer VLM after describe step so main VLM can use GPU."""
        describer = self.vision_describer_model or self.vision_model
        if not describer:
            return
        self._stop_ollama_model(describer)
        print(f"  [VLM] Stopped describer {describer}, waiting {self.UNLOAD_WAIT_SECONDS}s...")
        time.sleep(self.UNLOAD_WAIT_SECONDS)

    # ------------------------------------------------------------------
    # Vision (Ollama VLM: llava, llama3.2-vision, etc.)
    # ------------------------------------------------------------------

    def _image_to_base64(self, image_path: Union[str, Path]) -> str:
        """Read image file and return base64-encoded string."""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        data = path.read_bytes()
        return base64.b64encode(data).decode("utf-8")

    def describe_image(
        self,
        image_path: Union[str, Path],
        model: Optional[str] = None,
    ) -> str:
        """
        Use a (small) vision model to describe an image region in 1-2 sentences.
        Used for the describe-then-extract pipeline: describe crops, then send
        crops + descriptions to the main VLM for extraction.
        """
        describer = model or self.vision_describer_model or self.vision_model
        if not describer:
            return ""
        prompt = (
            "Describe this form image region in 1-2 short sentences. "
            "Mention any text, checkboxes (marked or empty), numbers, dates, and labels you see. "
            "Be concise."
        )
        b64 = self._image_to_base64(image_path)
        return self._chat_with_images(
            prompt=prompt,
            images=[b64],
            temperature=0.0,
            max_tokens=150,
            model=describer,
        )

    def generate_with_image(
        self,
        prompt: str,
        image_path: Union[str, Path],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate text using a vision LLM (Ollama) that can see an image.

        Uses Ollama /api/chat with the configured vision_model (e.g. llava:7b).
        Image is sent as base64 in the message.
        """
        if not self.vision_model:
            raise ValueError(
                "No vision_model configured. Pass vision_model='llava:7b' (or similar) to LLMEngine."
            )
        b64 = self._image_to_base64(image_path)
        return self._chat_with_images(
            prompt=prompt,
            images=[b64],
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            model=self.vision_model,
        )

    def generate_with_images(
        self,
        prompt: str,
        image_paths: List[Union[str, Path]],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate text using a vision LLM with multiple images (e.g. form pages).
        Uses the first image if model supports only one; otherwise sends all.
        """
        if not self.vision_model:
            raise ValueError("No vision_model configured.")
        b64_list = [self._image_to_base64(p) for p in image_paths]
        return self._chat_with_images(
            prompt=prompt,
            images=b64_list,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            model=self.vision_model,
        )

    def _chat_with_images(
        self,
        prompt: str,
        images: List[str],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
    ) -> str:
        """Ollama /api/chat with optional images (base64)."""
        model = model or self.vision_model
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens
        content = f"{system}\n\n{prompt}" if system else prompt
        message = {"role": "user", "content": content, "images": images}
        payload = {
            "model": model,
            "messages": [message],
            "stream": False,
            "options": {"temperature": temp, "num_predict": tokens},
        }
        vision_timeout = max(self.timeout, 180)
        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=vision_timeout,
                )
                resp.raise_for_status()
                out = resp.json()
                msg = out.get("message") or {}
                raw = msg.get("content", "") if isinstance(msg, dict) else ""
                if isinstance(raw, list):
                    text = "".join(
                        p.get("text", "") for p in raw if isinstance(p, dict) and p.get("type") == "text"
                    )
                else:
                    text = (raw or "") if isinstance(raw, str) else ""
                # When we get eval_count but empty content, Ollama may have streamed internally;
                # retry with stream=True and accumulate chunks to get the actual output.
                eval_count = out.get("eval_count") if isinstance(out.get("eval_count"), int) else 0
                if not (text or "").strip() and eval_count > 0:
                    print(f"  [VLM] Empty content but eval_count={eval_count}; retrying with stream=True to collect output ...")
                    stream_text = self._chat_with_images_streaming(
                        prompt=prompt, images=images, system=system,
                        temperature=temp, max_tokens=tokens, model=model,
                        content=content, message=message, vision_timeout=vision_timeout,
                    )
                    if (stream_text or "").strip():
                        return stream_text
                if not (text or "").strip():
                    err = out.get("error")
                    print(f"  [VLM] Empty content. message.content type={type(raw).__name__!r} repr={repr(raw)[:120]!r} eval_count={out.get('eval_count', '?')}")
                    if err:
                        print(f"  [VLM] Ollama error: {err}")
                return text or ""
            except (requests.RequestException, KeyError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    print(f"  [VLM] Attempt {attempt} failed ({exc}), retrying in {wait}s ...")
                    time.sleep(wait)
        raise RuntimeError(
            f"Vision LLM failed after {self.max_retries} attempts: {last_error}"
        )

    def _chat_with_images_streaming(
        self,
        prompt: str,
        images: List[str],
        content: str,
        message: Dict[str, Any],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        vision_timeout: int = 180,
    ) -> str:
        """Call Ollama /api/chat with stream=True and accumulate message.content from chunks."""
        payload = {
            "model": model or self.vision_model,
            "messages": [message],
            "stream": True,
            "options": {
                "temperature": temperature or self.temperature,
                "num_predict": max_tokens if max_tokens is not None else self.max_tokens,
            },
        }
        parts: List[str] = []
        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=vision_timeout,
                stream=True,
            )
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = chunk.get("message") or {}
                raw = msg.get("content", "")
                if isinstance(raw, str) and raw:
                    parts.append(raw)
                elif isinstance(raw, list):
                    for p in raw:
                        if isinstance(p, dict) and p.get("type") == "text" and p.get("text"):
                            parts.append(p["text"])
        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"  [VLM] Streaming fallback error: {e}")
            return ""
        out = "".join(parts)
        if out.strip():
            print(f"  [VLM] Recovered {len(out)} chars via stream=True")
        return out

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
