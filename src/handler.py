"""Alibaba Cloud Function Compute entry point.

Trigger: inbound inquiry email (or HTTP POST {"email": "..."} for testing).
Flow: Contract → Execute (Qwen) → Verify → Observe → Control (Telegram gate).
Nothing is sent to a customer inside this function — approval is human-only.
"""
import json
import time

from .agent import classify, draft, recall
from .harness import kill_switch_engaged, observe, send_for_approval, verify

MAX_RETRIES = 2


def process_inquiry(email: str) -> dict:
    run = {"ts": time.time(), "input": email, "steps": []}

    if kill_switch_engaged():
        run["outcome"] = "killed"
        observe(run)
        return run

    cls = classify(email)
    run["steps"].append({"step": "classify", "output": cls})
    if cls.get("intent") == "spam" and cls.get("confidence", 0) > 0.8:
        run["outcome"] = "dropped_spam"
        observe(run)
        return run

    memory = recall(cls)
    run["steps"].append({"step": "recall", "output": memory})

    verdict, draft_text = {"approve": False}, ""
    for attempt in range(1 + MAX_RETRIES):
        draft_text = draft(email, memory)
        verdict = verify(email, memory, draft_text)
        run["steps"].append({"step": f"draft_verify_{attempt}",
                             "draft": draft_text, "verdict": verdict})
        if verdict.get("approve"):
            break

    if verdict.get("approve"):
        gate = send_for_approval(draft_text, cls)
        run["steps"].append({"step": "control_gate", "output": gate})
        run["outcome"] = "awaiting_human_approval"
    else:
        run["outcome"] = "escalated_verify_failed"

    run["trace"] = str(observe(run))
    return run


def handler(event, context):
    """Function Compute handler (event trigger or HTTP)."""
    body = event if isinstance(event, dict) else json.loads(event or "{}")
    if isinstance(body.get("body"), str):  # HTTP trigger wraps payload
        body = json.loads(body["body"])
    result = process_inquiry(body["email"])
    return {"statusCode": 200,
            "body": json.dumps({"outcome": result["outcome"], "trace": result.get("trace")})}


if __name__ == "__main__":  # local smoke test
    sample = ("From: jane@acme.example\nSubject: consultation\n\n"
              "Hello, we need help migrating our workloads to Kubernetes. "
              "Could we book a 30-min call next week? Thursday afternoon works.")
    print(json.dumps(process_inquiry(sample), indent=2, default=str))
