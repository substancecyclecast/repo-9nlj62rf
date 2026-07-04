# SnabAgent — Pitch Deck Outline (12 slides)

Design: clean, dark, one big idea per slide. Use the Mermaid diagram from
`deploy/alibaba/architecture.md` rendered as an image on slide 4. Colors: Qwen purple +
Alibaba orange accents. Every slide has a one-line takeaway at the bottom.

---

### Slide 1 — Title
**SnabAgent — Qwen-Powered Autopilot for Enterprise Procurement**
Subtitle: *End-to-end. Verified. Self-improving.*
Track: Autopilot Agent (+ MemoryAgent + Agent Society) · Built on Qwen Cloud + Alibaba Cloud.
Speaker note: one sentence — "a dirty procurement request becomes a verified decision, automatically."

### Slide 2 — The Problem
- Procurement is a **trillion-dollar** manual process.
- One buyer: ~6h per request; ~7% loss from sub-optimal / non-compliant choices.
- Compliance + audit pressure make "just use ChatGPT" a non-starter.
Takeaway: *High value, high stakes, poorly automated.*

### Slide 3 — The Solution
SnabAgent = **autopilot** that runs the full loop: request → suppliers → RFQs → negotiation
→ **independent verification** → Top-3 with savings — with a full audit trail and a human
only on escalation.
Takeaway: *Not a chatbot — an accountable decision engine.*

### Slide 4 — Architecture (diagram)
Insert the Mermaid diagram: Memory Recall → Planner → Sourcer → Communicator → Negotiator →
Verifier → Reporter → Memory Writeback, with Qwen (max/plus) on the side and Postgres/Qdrant/Redis below.
Takeaway: *8 agents on LangGraph, all reasoning on Qwen Cloud.*

### Slide 5 — Why Qwen Cloud
- OpenAI-compatible → clean integration (`llm/qwen.py`).
- **qwen-max** for hard reasoning (Planner/Sourcer/Negotiator/Reporter).
- **qwen-plus** as an *independent* verifier → anti-hallucination.
- PII masked before every Qwen call.
Takeaway: *Qwen's reasoning quality + role-tiered models = grounded automation.*

### Slide 6 — Anti-Hallucination Verifier
- Verifier runs on a **different model** than the primary.
- Cross-checks price/spec/lead-time + INN/OGRN validity.
- Startup invariant: `qwen_model != qwen_verifier_model`.
Takeaway: *A second, independent brain catches the first one's mistakes.*

### Slide 7 — Persistent Memory (MemoryAgent)
- `company_profiles` (price/lead-time/quality weights)
- `supplier_memory` (reliability EMA, times selected, on-time)
- `lot_decision_memory` (past decisions)
- Recall before planning; Writeback after report → **self-improving**.
Takeaway: *Every closed lot makes the next one smarter.*

### Slide 8 — Live Demo
Screens: dirty TZ → pipeline run → Top-3 + rationale → **savings %** → audit tree → Approve.
Callout: audit shows `model_name: qwen-max / qwen-plus`.
Takeaway: *Real output, fully traceable.*

### Slide 9 — Impact / Metrics
- ~10% verifiable savings (offline demo, chemistry scenario).
- ~6h → minutes per request; 196 tests green; full audit trail.
- ROI model: as-is vs to-be (see `submission_package/financial_model.md`).
Takeaway: *Measurable time + money saved.*

### Slide 10 — Production-Ready & On Alibaba Cloud
- FastAPI + Celery + Postgres + Qdrant + Redis, Alembic migrations, Prometheus metrics.
- Deployed on **Alibaba Cloud ECS** (`deploy/alibaba/`): compose + `deploy.sh` + guide.
Takeaway: *Deployable today, not a prototype.*

### Slide 11 — What's Next
Self-tuning preference weights · richer negotiation (Agent Society) · vector memory of lots
· Qwen model tiering (flash/max) for cost.
Takeaway: *A compounding, self-improving procurement autopilot.*

### Slide 12 — Team / Call to action
Repo link · demo video link · "Deploy in 3 commands with your Qwen key."
Takeaway: *SnabAgent: the autopilot enterprise procurement has been waiting for.*
