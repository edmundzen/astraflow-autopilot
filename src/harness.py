"""The Harness — why you can trust the loop in production.

Five jobs: Contract (schemas, loaded from /contract), Execute (agent.py),
Verify (deterministic checks + Qwen grading), Observe (replay traces),
Control (Telegram human gate, pause, kill).
"""
import json
import time
from pathlib import Path

import requests

from .agent import _json, qwen
from .config import TELEGRAM_CHAT_ID, TELEGRAM_TOKEN

TRACES = Path(__file__).resolve().parent.parent / "traces"

VERIFY_SYSTEM = (
    "You are the Verify step. Grade the draft against these criteria: "
    "only ECS's six service domains referenced; exactly one clear next step; "
    "professional tone; no invented facts beyond the email and memory context. "
    'Respond ONLY with JSON: {"approve":true|false,"issues":["..."]}'
)


# ---- Verify ----------------------------------------------------------------
def verify(email: str, memory: str, draft_text: str) -> dict:
    issues = []
    # Deterministic checks first (cheap, non-gameable)
    if "Drago" not in draft_text:
        issues.append("missing Drago signature")
    if any(tok in draft_text.lower() for tok in ("$", "usd", "per hour", "/hr")) \
            and "free" not in draft_text.lower():
        issues.append("prices quoted outside contract")
    if issues:
        return {"approve": False, "issues": issues, "stage": "deterministic"}
    # Model-graded second
    graded = _json(qwen(VERIFY_SYSTEM,
                        f"EMAIL:\n{email}\n\nMEMORY:\n{memory}\n\nDRAFT:\n{draft_text}",
                        max_tokens=200))
    graded["stage"] = "model_graded"
    return graded


# ---- Observe ----------------------------------------------------------------
def observe(run: dict) -> Path:
    """Every run is written as a replay trace: input, steps, verdict, latency."""
    TRACES.mkdir(exist_ok=True)
    out = TRACES / f"run_{int(time.time())}.json"
    out.write_text(json.dumps(run, indent=2, default=str))
    return out


# ---- Control ----------------------------------------------------------------
def send_for_approval(draft_text: str, classification: dict) -> dict:
    """Human gate: the draft goes to Telegram with approve/reject buttons.
    Nothing is ever sent to a customer without a human tap."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return {"sent": False, "reason": "telegram not configured (sandbox mode)"}
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": (f"📥 New {classification.get('intent')} "
                     f"({classification.get('service_domain')})\n\n{draft_text}\n\n"
                     "Approve to send?"),
            "reply_markup": {"inline_keyboard": [[
                {"text": "✅ Approve", "callback_data": "approve"},
                {"text": "❌ Reject", "callback_data": "reject"},
            ]]},
        },
        timeout=30,
    )
    return {"sent": r.status_code == 200, "status": r.status_code}


def kill_switch_engaged() -> bool:
    """One-action kill: drop a file named KILL next to the code (or detach the
    email trigger in the Function Compute console)."""
    return (Path(__file__).resolve().parent.parent / "KILL").exists()
