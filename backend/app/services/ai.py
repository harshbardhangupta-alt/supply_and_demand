"""Optional OpenAI-powered research / analysis.

This is strictly supplementary: it explains and summarizes the *deterministic*
engine output in natural language. It never computes prices, levels, sizes or
risk decisions, and the platform works fully without it. Uses the OpenAI REST
API directly via httpx so no extra SDK is required.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

log = logging.getLogger("smc.ai")

OPENAI_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "You are an assistant that explains Smart-Money-Concepts (Supply & Demand) "
    "trade setups. You are given the output of a deterministic trading engine. "
    "Explain the setup clearly and concisely for a trader: the bias, the zone, "
    "the structure (BOS/CHOCH), the entry/stop/target logic, the risk, and the "
    "main risks/invalidation. Do NOT invent prices or numbers — use only what is "
    "provided. Add a one-line risk disclaimer. Keep it under 220 words."
)


class OpenAIResearch:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, timeout: float = 30.0):
        self.api_key = api_key
        self.model = model or DEFAULT_MODEL
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def test_connection(self) -> dict:
        if not self.configured:
            raise RuntimeError("OpenAI API key not set.")
        try:
            with httpx.Client(base_url=OPENAI_BASE, headers=self._headers(),
                              timeout=self.timeout) as c:
                r = c.get("/models")
            if r.status_code == 401:
                raise RuntimeError("OpenAI rejected the API key (401).")
            r.raise_for_status()
            models = [m.get("id") for m in r.json().get("data", [])]
            return {"ok": True, "model_count": len(models),
                    "has_configured_model": self.model in models}
        except httpx.HTTPError as exc:
            raise RuntimeError(f"OpenAI connection failed: {exc}") from exc

    def analyze(self, symbol: str, setup: dict, extra_context: str = "") -> str:
        if not self.configured:
            raise RuntimeError("OpenAI API key not set.")
        user = (
            f"Instrument: {symbol}\n"
            f"Engine setup (deterministic):\n{_fmt(setup)}\n"
            f"{extra_context}\n"
            "Explain this setup."
        )
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            "temperature": 0.4,
            "max_tokens": 450,
        }
        try:
            with httpx.Client(base_url=OPENAI_BASE, headers=self._headers(),
                              timeout=self.timeout) as c:
                r = c.post("/chat/completions", json=body)
            if r.status_code == 401:
                raise RuntimeError("OpenAI rejected the API key (401).")
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc


def _fmt(setup: dict) -> str:
    keys = ["direction", "entry_model", "score", "entry", "stop", "target",
            "reward_risk", "qty", "risk_pct", "bos", "fvg", "zone_state",
            "zone_fresh", "biases", "rejection_reason"]
    lines = []
    for k in keys:
        if k in setup and setup[k] is not None:
            lines.append(f"  {k}: {setup[k]}")
    return "\n".join(lines)
