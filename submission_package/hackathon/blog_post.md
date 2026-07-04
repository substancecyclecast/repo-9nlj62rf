# How we built a production procurement autopilot with Qwen multi-agents

*Submitted for the Qwen Cloud Global AI Hackathon — bonus blog track.*

Most "AI agent" demos are a single prompt in a trench coat. For enterprise procurement —
a trillion-dollar, compliance-heavy process — that isn't good enough. You need something
**grounded, auditable, and self-improving**. Here's how we built SnabAgent: an 8-agent
autopilot that turns a messy purchase request into a verified, explainable decision, with
every ounce of reasoning running on **Qwen Cloud**.

## The problem
A buyer gets a free-text request — misspelled items, no catalog codes, a deadline. Turning
that into three comparable, compliant quotes takes ~6 hours of manual work, and a wrong
pick quietly burns ~7% of the order value. Companies can't just paste this into a chatbot:
they need an audit trail, PII handling, and no hallucinated suppliers.

## The design: a small society of agents
We used **LangGraph** to wire eight specialized nodes:

`Memory Recall → Planner → Sourcer → Communicator → Negotiator → Verifier → Reporter → Memory Writeback`

Two design decisions carried most of the weight.

### 1. An independent verifier — on a *different* Qwen model
The classic failure mode of LLM automation is confident nonsense. Our fix: a dedicated
**Verifier** agent that re-checks each offer against the spec, lead times, and supplier
INN/OGRN validity — running on a **different model than the one that produced the answer**.

Qwen Cloud made this elegant. It's OpenAI-compatible, so our provider is thin:

```python
client_base = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
# primary reasoning:  qwen-max
# independent verifier: qwen-plus
```

We route by *role*: `role="verifier"` → `qwen-plus`, everything else → `qwen-max`, and a
startup invariant enforces `qwen_model != qwen_verifier_model`. Same provider, genuinely
independent second opinion.

### 2. Persistent memory — so the agent compounds value
Before planning, `Memory Recall` loads three things from Postgres:
- the company's **preference profile** (price vs. lead-time vs. quality),
- accumulated **supplier reliability** (an EMA updated after each deal),
- **similar past lots**.

After the report, `Memory Writeback` bumps reliability scores and records the decision.
The Sourcer then boosts suppliers we've succeeded with before. Every closed lot makes the
next one smarter — the MemoryAgent loop, in ~200 lines of explainable SQL-backed code.

## Why Qwen fit the job
- **Reasoning quality** on messy, domain-specific Russian procurement text (catalog mapping,
  negotiation, verification) was strong out of the box.
- **OpenAI compatibility** meant we plugged Qwen into our existing router — with retry,
  fallback, PII masking, and cost metering — in an afternoon.
- **Model tiering** (`max` / `plus` / `flash`) let us match model strength to task and keep
  the independent-verifier guarantee.

## Production, not prototype
SnabAgent ships with FastAPI + Celery, PostgreSQL, Qdrant, Redis, Alembic migrations,
Prometheus metrics, PII masking before every external call, and a full audit trail (prompt,
model, tokens, confidence, decision) for every step. It runs on **Alibaba Cloud ECS** via a
one-shot `deploy.sh`. There's also a zero-dependency offline demo that runs the entire
8-node graph deterministically — 196 unit tests stay green in CI.

## Results
On our offline benchmark, SnabAgent produced verified Top-3 recommendations with measurable
savings (~10% on the chemistry scenario), collapsing a ~6-hour manual task into minutes —
while remaining fully auditable.

## What's next
Self-tuning preference weights from realized outcomes, richer multi-agent negotiation
(Agent Society), vector memory of past lots, and dynamic Qwen model tiering for cost.

*Try it: set `LLM_PRIMARY=qwen` and your DashScope key, then `make dev`. Repo and demo video
in the submission.*
