# SnabAgent — 5-minute Demo Video Script

Goal: prove it's real, grounded, and Qwen-powered. Keep energy high; show the product more
than slides. Record at 1080p, browser + terminal. Total target: **4:45**.

## 0:00–0:30 — Hook + problem
On camera / voiceover over a messy email:
> "This is a real procurement request — misspelled items, no SKUs, a deadline. Normally a
> buyer spends about six hours turning this into three comparable quotes. SnabAgent does it
> automatically, on Qwen, and verifies its own work."

## 0:30–1:10 — What it is (1 slide)
Show architecture diagram (slide 4).
> "Eight agents on LangGraph: memory, planner, sourcer, communicator, negotiator, an
> **independent verifier**, reporter, and a memory writeback step. All reasoning runs on
> Qwen Cloud — `qwen-max` for reasoning, `qwen-plus` as an independent verifier."

## 1:10–2:40 — Live run (the core)
Terminal + Streamlit:
1. Paste the dirty TZ, create the lot.
2. Watch statuses advance: planned → sourcing → rfq_sent → negotiating → verified → report_ready.
3. Open the report: **Top-3 suppliers**, rationale, and **savings vs baseline (~10%)**.
> "Notice it never invented a catalog item — low-confidence lines escalate to a human."

## 2:40–3:20 — Trust: the audit tree + verifier
Open the audit view for the lot.
> "Every step is logged — prompt, model, tokens, confidence. Here's the verifier running on
> a *different* Qwen model, cross-checking the offer against the spec and the supplier's INN.
> That's our anti-hallucination guarantee."
Point to `model_name: qwen-max` and `qwen-plus` in the audit entries.

## 3:20–4:00 — Memory: it learns
> "SnabAgent remembers. Run a second lot for the same company —" (show it) "— and the
> Sourcer now boosts suppliers it has succeeded with before. Reliability scores update after
> every deal. That's the MemoryAgent loop."
Show `supplier_memory` growing (or the recall audit entry with known suppliers).

## 4:00–4:30 — Alibaba Cloud + production
> "It's deployed on Alibaba Cloud ECS with one script, and it's production-grade: Postgres,
> Qdrant, Redis, migrations, metrics, 196 tests green."
Show `deploy/alibaba/` and the running ECS `/docs` page.

## 4:30–4:45 — Close
> "SnabAgent — a verified, self-improving procurement autopilot, powered by Qwen. Trillion-
> dollar problem, measurable savings, ready to deploy. Thanks for watching."

## Shot checklist
- [ ] Dirty TZ visible and readable
- [ ] Full pipeline status progression
- [ ] Top-3 + savings %
- [ ] Audit tree with qwen-max / qwen-plus model names
- [ ] Second lot showing memory boost
- [ ] Alibaba Cloud ECS running (/docs or Streamlit on public IP)
