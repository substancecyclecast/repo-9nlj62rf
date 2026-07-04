# SnabAgent — Qwen-Powered Autopilot for Enterprise Procurement

**Track:** Autopilot Agent (with MemoryAgent + Agent Society elements)
**Built with:** Qwen Cloud (Alibaba DashScope) · LangGraph · FastAPI · PostgreSQL · Qdrant · Redis · Streamlit · Alibaba Cloud ECS

## Elevator pitch
SnabAgent turns a messy, free-text procurement request into a **verified, explainable
purchasing decision** — automatically. Eight specialized agents (on LangGraph) plan,
source suppliers, send RFQs, negotiate, independently verify offers, and produce a Top-3
recommendation with measurable savings. All reasoning runs on **Qwen Cloud**, with a
*second, different* Qwen model acting as an anti-hallucination verifier.

## Inspiration
Enterprise procurement is a trillion-dollar, painfully manual process. A buyer receives a
"dirty" request ("швеллер 14-й, трёшка, 20 тонн, срочно"), then spends **~6 hours**
normalizing items, hunting suppliers, sending RFQs, chasing quotes, and comparing offers —
and still risks picking a sub-optimal or non-compliant supplier. We wanted an **autopilot**
that does the whole loop end-to-end, but is trustworthy enough for a real company:
grounded, auditable, and able to learn from every deal it closes.

## What it does
1. **Memory Recall** — loads the company's preference profile, accumulated supplier
   reliability scores, and similar past lots.
2. **Planner** — parses the raw request, maps every line to the corporate catalog (NSI) via
   vector search + Qwen validation; escalates to a human when confidence is low.
3. **Sourcer** — gathers supplier candidates from history, vector search and a registry,
   then ranks them with Qwen — boosted by long-term memory.
4. **Communicator** — generates and sends RFQ emails.
5. **Negotiator** — runs a bounded negotiation round (with a regulatory filter).
6. **Verifier** — an **independent Qwen model** cross-checks each offer against the spec,
   supplier INN/OGRN validity and lead times — catching the primary model's mistakes.
7. **Reporter** — produces a Top-3 comparison with rationale and **savings vs. baseline**.
8. **Memory Writeback** — updates supplier reliability (EMA) and records the decision, so
   the agent improves with every lot.

Every step is written to a **full audit trail** (prompt, model, tokens, latency,
confidence, decision) — explainability by construction.

## How we built it with Qwen
- Qwen Cloud is **OpenAI-compatible**, so we added a clean provider
  (`src/snabagent/llm/qwen.py`) hitting `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`,
  wired through the same router as every other provider (retry, fallback, PII masking, cost metering).
- **Role-aware model selection**: primary reasoning uses `qwen-max`; the independent
  verifier uses `qwen-plus`. The settings validator enforces
  `qwen_model != qwen_verifier_model`, preserving the anti-hallucination guarantee even
  though both are Qwen.
- **PII masking** (INN, OGRN, emails, phones) happens before *any* call leaves for Qwen.
- Deployed on **Alibaba Cloud ECS** via `deploy/alibaba/` (Docker Compose + one-shot
  `deploy.sh` + ECS guide).

## Challenges we ran into
- Keeping the verifier genuinely independent while using a single provider — solved with
  role-aware model routing and a startup invariant.
- Making memory useful without over-engineering — we chose a compact, explainable SQL
  memory (profile + EMA reliability + decision log) that plugs into ranking.
- Staying grounded: no invented SKUs, graceful escalation when the catalog has no match.

## Accomplishments we're proud of
- A **production-grade** stack (migrations, audit, PII masking, metrics, tests) — not a toy.
- **196 unit tests green**, `ruff` clean, deterministic offline demo (`fake` LLM) that runs
  the full 8-node graph with no external dependencies.
- Measurable outcomes: e.g. **~10% savings** on the chemistry scenario in the offline demo.

## What we learned
Multi-agent + an independent verifier beats a single monolithic prompt for high-stakes,
auditable decisions — and persistent memory is what turns an "agent demo" into something
that compounds value over time.

## What's next
- Self-tuning preference weights from outcomes; richer supplier-negotiation dialogues
  (Agent Society); vector-based memory of past lots; multi-region Qwen model tiering
  (flash for cheap steps, max for hard reasoning).

## Try it
```bash
cp .env.example .env       # set LLM_PRIMARY=qwen + LLM_QWEN_API_KEY
make dev                   # or deploy/alibaba/ for ECS
# offline, zero-dependency demo:
python scripts/run_offline_demo.py
```

## Links
- Architecture + diagram: `deploy/alibaba/architecture.md`
- Alibaba Cloud deployment: `deploy/alibaba/ecs-deployment.md`
- Qwen provider: `src/snabagent/llm/qwen.py`
