# AstraFlow Autopilot — Inquiry-to-Booking Agent

**Track 4: Autopilot Agent** · Global AI Hackathon Series with Qwen

A Qwen agent (Drago) that turns customer inquiry emails into approved quotes and
bookings — with a human gate, full run traces, and a kill switch. Built for
production, not demo day.

## What it does

A customer email arrives at `bookings@`. Drago reads it, classifies the request
against our six service domains, recalls similar past inquiries from memory, and
drafts a quote/booking reply. **Then it stops.** Nothing sends until a human
approves — the approval arrives as a Telegram message with one-tap approve or
reject. On approval, the reply goes out, the booking is logged to Notion, and
the full run trace is stored.

## Architecture

```
Customer email ──► Alibaba Cloud Function Compute ──► Qwen Cloud (Model API)
(bookings@ inbox)   ├─ Drago — Qwen agent                   ▲ all reasoning
                    │  (classify, draft, recall)            │
                    └─ Harness ──────────────► Telegram (approve / reject)
                       (verify, observe, control)
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
       Memory         Run traces        Bookings
   (Supabase+Chroma)  (replay log)   (Notion + email out)
```

- **Contract** (`contract/`) — typed inquiry schema + draft acceptance criteria, written before the agent runs
- **Execute** (`src/agent.py`) — the only place the model lives; Qwen via Qwen Cloud's OpenAI-compatible API; narrow tools, cannot send
- **Verify** (`src/harness.py`) — deterministic checks first, Qwen grading second; fail → forced retry → escalate
- **Observe** — every run logged with inputs, outputs, verdict, latency; any run is replayable
- **Control** — human gate on Telegram, plus a one-action kill switch

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env          # add your Qwen Cloud key + Telegram bot
python -m src.handler         # runs a sample inquiry end-to-end
```

## Deploy (Alibaba Cloud Function Compute)

1. Create a Function Compute service, Python 3.10 runtime
2. Upload this repo; set handler to `src/handler.handler`
3. Set environment variables from `.env.example`
4. Attach the email/HTTP trigger — see `docs/DEPLOYMENT.md` for the recorded proof

## Model

All reasoning routes through **Qwen (`qwen3.7-plus`) on Qwen Cloud** —
`src/agent.py::qwen()` is the single model entry point.

## License

MIT
