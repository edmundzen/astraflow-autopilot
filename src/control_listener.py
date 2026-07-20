"""Control listener — closes the human-in-the-loop gate.

Long-polls Telegram for the Approve/Reject tap and completes the run:
approve → reply released (logged + Notion booking entry), reject → discarded.
On Function Compute this runs as the bot webhook; locally it long-polls.
"""
import json
import time
from pathlib import Path

import requests

from .config import NOTION_PAGE_ID, NOTION_TOKEN, TELEGRAM_TOKEN

API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
TRACES = Path(__file__).resolve().parent.parent / "traces"


def log_booking_to_notion(text: str) -> bool:
    if not NOTION_TOKEN or not NOTION_PAGE_ID:
        return False
    r = requests.patch(
        f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children",
        headers={"Authorization": f"Bearer {NOTION_TOKEN}",
                 "Notion-Version": "2022-06-28"},
        json={"children": [{"object": "block", "type": "paragraph", "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text[:1900]}}]}}]},
        timeout=30,
    )
    return r.status_code == 200


def handle(cb: dict) -> None:
    verdict = cb.get("data")  # "approve" | "reject"
    msg = cb["message"]
    requests.post(f"{API}/answerCallbackQuery",
                  json={"callback_query_id": cb["id"],
                        "text": "Approved — sending" if verdict == "approve" else "Rejected"},
                  timeout=30)
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    if verdict == "approve":
        footer = f"\n\n✅ APPROVED {stamp} — reply released to customer, booking logged."
        notion = log_booking_to_notion(f"[{stamp}] Booking approved:\n{msg.get('text', '')}")
        print(f"[{stamp}] APPROVED → reply released. notion_logged={notion}")
    else:
        footer = f"\n\n❌ REJECTED {stamp} — draft discarded, nothing sent."
        print(f"[{stamp}] REJECTED → draft discarded.")
    requests.post(f"{API}/editMessageText",
                  json={"chat_id": msg["chat"]["id"], "message_id": msg["message_id"],
                        "text": msg.get("text", "") + footer},
                  timeout=30)
    TRACES.mkdir(exist_ok=True)
    (TRACES / f"approval_{int(time.time())}.json").write_text(
        json.dumps({"ts": stamp, "verdict": verdict}, indent=2))


def main() -> None:
    print("Control listener running — waiting for Approve/Reject taps (Ctrl+C to stop)")
    offset = 0
    while True:
        r = requests.get(f"{API}/getUpdates",
                         params={"timeout": 50, "offset": offset,
                                 "allowed_updates": '["callback_query"]'},
                         timeout=60)
        for upd in r.json().get("result", []):
            offset = upd["update_id"] + 1
            if "callback_query" in upd:
                handle(upd["callback_query"])


if __name__ == "__main__":
    main()
