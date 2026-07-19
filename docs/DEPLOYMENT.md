\# Deployment — Alibaba Cloud Function Compute



Backend runs on Alibaba Cloud Function Compute (Singapore region), triggered over HTTP.



\- Handler: `src/handler.handler` — entry point invoked by FC

\- Qwen calls: `src/agent.py::qwen()` — Qwen Cloud (Model Studio) API

\- Env vars set in FC function config (see `.env.example`) — no secrets in code



\## Architecture

!\[Architecture](architecture.png)



\## Proof of deployment

Recording: <link to proof clip — added at submission>

