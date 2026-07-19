"""Drago — AstraFlow's master agent. Reasoning runs on Qwen (Qwen Cloud).

Three jobs, deliberately narrow tools: classify the inquiry, recall memory
context, draft a reply. Drago cannot send anything — Control owns that.
"""
import json

import requests

from .config import QWEN_API_KEY, QWEN_BASE_URL, QWEN_MODEL, SERVICE_DOMAINS

CLASSIFY_SYSTEM = (
    "Classify this customer inquiry email for Edmund Cloud Solutions. "
    'Respond ONLY with JSON matching: {"intent":"booking|inquiry|spam",'
    f'"service_domain":one of {SERVICE_DOMAINS} or null,'
    '"requested_time":"<text or null>","team_size":int or null,'
    '"budget":"<text or null>","confidence":0-1}'
)

DRAFT_SYSTEM = (
    "You are Drago, booking assistant for Edmund Cloud Solutions (AI - Space - Security). "
    "Draft a short professional reply to the inquiry. Rules: only reference the six ECS "
    "service domains; initial 30-min consultation is free; exactly one clear next step; "
    "no invented facts; sign as Drago, Booking Assistant, Edmund Cloud Solutions.\n"
    "Context from memory: {memory}"
)


def qwen(system: str, user: str, max_tokens: int = 500, temperature: float = 0) -> str:
    """Single entry point for all model calls — everything routes through Qwen Cloud."""
    r = requests.post(
        f"{QWEN_BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {QWEN_API_KEY}"},
        json={"model": QWEN_MODEL, "temperature": temperature, "max_tokens": max_tokens,
              "messages": [{"role": "system", "content": system},
                           {"role": "user", "content": user}]},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _json(text: str) -> dict:
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def classify(email: str) -> dict:
    return _json(qwen(CLASSIFY_SYSTEM, email, max_tokens=150))


def recall(classification: dict) -> str:
    """Memory context. Sandbox mode ships a static profile; production pulls
    Supabase (structured) + Chroma (semantic) using the classification as the query."""
    return ("Known services: cloud migration, Kubernetes, AI agents, security, "
            "space solutions, consulting. Initial 30-min consultation is free.")


def draft(email: str, memory: str) -> str:
    return qwen(DRAFT_SYSTEM.format(memory=memory), email)
