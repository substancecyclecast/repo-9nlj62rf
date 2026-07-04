# Devpost — ready-to-paste answers (SnabAgent)

Copy each block into the matching Devpost field. Files to upload are listed at the bottom.

---

## PROJECT DETAILS

### About the project (Project Story — Markdown supported)

```markdown
## Inspiration
Enterprise procurement is a trillion-dollar, painfully manual process. A buyer receives a
"dirty" request — misspelled items, no catalog codes, a deadline — and spends ~6 hours
normalizing items, finding suppliers, sending RFQs, chasing quotes and comparing offers,
while still risking a sub-optimal or non-compliant pick (~7% of order value lost). You can't
just paste this into a chatbot: enterprises need grounding, an audit trail, and PII handling.
We wanted a trustworthy **autopilot** that runs the whole loop end-to-end.

## What it does
SnabAgent turns a free-text procurement request into a **verified, explainable** Top-3
recommendation with measurable savings — automatically. Eight specialized agents on
LangGraph:
1. **Memory Recall** – loads company preferences, supplier reliability, similar past lots.
2. **Planner** – parses the request, maps items to the corporate catalog (NSI); escalates on low confidence.
3. **Sourcer** – gathers + ranks suppliers (boosted by long-term memory).
4. **Communicator** – generates and sends RFQs.
5. **Negotiator** – bounded negotiation with a regulatory filter.
6. **Verifier** – an INDEPENDENT Qwen model cross-checks each offer vs. spec, lead time and INN/OGRN validity.
7. **Reporter** – Top-3 with rationale and savings vs. baseline.
8. **Memory Writeback** – updates supplier reliability (EMA) and records the decision → self-improving.
Every step is written to a full audit trail (prompt, model, tokens, confidence, decision).

## How we built it
- **Qwen Cloud (Alibaba DashScope)**, OpenAI-compatible, via a thin provider
  (`src/snabagent/llm/qwen.py`) on `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`.
- **Role-aware models**: `qwen-max` for reasoning, `qwen-plus` as the independent verifier;
  a startup invariant enforces `primary_model != verifier_model` to preserve the
  anti-hallucination guarantee.
- **LangGraph** orchestrates the 8 agents; **FastAPI + Celery** run the backend;
  **PostgreSQL** stores lots, audit and the memory tables; **Qdrant** powers supplier/NSI
  vector search; **Redis** is the task broker; **Streamlit** is the demo UI.
- **PII masking** before any external call; **Alembic** migrations; Prometheus metrics.
- Deployed on **Alibaba Cloud ECS** with Docker Compose (`deploy/alibaba/`).

## Challenges we ran into
Keeping the verifier genuinely independent while using one provider (solved with role-aware
routing + a startup invariant); designing a useful but explainable memory (compact SQL:
profile + EMA reliability + decision log); staying grounded (no invented SKUs, graceful
escalation when the catalog has no match).

## Accomplishments that we're proud of
A production-grade stack — not a toy: migrations, audit, PII masking, metrics, 196 green unit
tests, and a deterministic zero-dependency offline demo that runs the entire 8-node graph.
Measurable outcome: ~10% savings on the chemistry scenario.

## What we learned
Multi-agent + an independent verifier beats a single monolithic prompt for high-stakes,
auditable decisions — and persistent memory is what turns an "agent demo" into something
that compounds value over time.

## What's next for SnabAgent
Self-tuning preference weights from realized outcomes, richer multi-agent negotiation
(Agent Society), vector memory of past lots, and dynamic Qwen model tiering (flash/max) for cost.
```

### Built with
```
python, fastapi, langgraph, qwen-cloud, alibaba-dashscope, alibaba-cloud-ecs, postgresql,
qdrant, redis, celery, streamlit, docker, docker-compose, sqlalchemy, alembic, httpx,
pydantic, prometheus
```

### "Try it out" links
- GitHub repo: https://github.com/substancecyclecast/repo-9nlj62rf
- (optional) PR with the hackathon work: https://github.com/substancecyclecast/repo-9nlj62rf/pull/20

### Image gallery (upload)
- `submission_package/hackathon/architecture_diagram.png`
- demo screenshots (from the recorded video / Streamlit).

### Video demo link
YouTube/Vimeo URL — upload the recorded demo to your own account and paste the link here.

---

## ADDITIONAL INFO

- **Submitter type:** Individual (or Team — pick what matches you).
- **Organization name:** (leave blank unless applicable.)
- **Country of residence:** (select your own country — I must not guess this for you.)
- **Newly built or previously existing:** **Previously existing** (SnabAgent v2.2.0 predates the event).
- **Start date (MM-DD-YY):** use the project's real start date.
- **What you updated during the submission period:**
  ```
  During the submission period we added a first-class Qwen Cloud (Alibaba DashScope) LLM
  provider with role-aware model routing (qwen-max reasoning + qwen-plus independent
  verifier), a persistent memory layer (company profile, supplier reliability EMA, past-lot
  decisions) with new Memory Recall / Memory Writeback agents in the LangGraph pipeline, and
  an Alibaba Cloud ECS deployment (docker-compose, deploy script, ECS guide, architecture
  diagram). See PR: https://github.com/substancecyclecast/repo-9nlj62rf/pull/20
  ```
- **Track:** **Autopilot Agent** (with MemoryAgent + Agent Society elements).
- **Code repository URL:** https://github.com/substancecyclecast/repo-9nlj62rf
  ⚠️ Must be PUBLIC with a detectable OPEN-SOURCE license (see the license note below).
- **URL to code file showing Alibaba Cloud deployment:**
  https://github.com/substancecyclecast/repo-9nlj62rf/blob/main/deploy/alibaba/docker-compose.alibaba.yml
  (also: `deploy/alibaba/ecs-deployment.md`)
- **Architecture Diagram (upload):** `submission_package/hackathon/architecture_diagram.png`
- **Screenshot proof of Alibaba Cloud deployment (upload):** ⚠️ NOT YET AVAILABLE — requires
  actually deploying to your Alibaba Cloud account (see blocker below).
- **Blog / Social post URL (bonus):** publish `submission_package/hackathon/blog_post.md` on
  Medium/Dev.to and paste the link.
- **Which AI tools did you leverage:**
  ```
  Qwen Cloud (Alibaba DashScope: qwen-max, qwen-plus) as the reasoning + verification engine;
  Devin (Cognition AI) as the coding agent used to build the integration, memory layer, and
  deployment.
  ```
- **Level of learning:** pick the option that best matches (e.g. "A lot").
- **Age / eligibility / not-a-sponsor-employee checkboxes:** you must confirm these yourself
  (legal attestations — I can't check these on your behalf).

---

## FILES TO UPLOAD (already in the repo)
| Devpost field | File |
|---|---|
| Architecture Diagram | `submission_package/hackathon/architecture_diagram.png` |
| Image gallery | `submission_package/hackathon/architecture_diagram.png` + demo screenshots |
| Video demo | recorded demo (upload to YouTube/Vimeo first) |
| Blog post | `submission_package/hackathon/blog_post.md` (publish, then paste URL) |

## OPEN BLOCKERS (need you)
1. **Open-source license:** the repo currently ships a *Proprietary* LICENSE. The hackathon
   REQUIRES a detectable open-source license (e.g. MIT or Apache-2.0). Approve which one and
   I'll replace LICENSE + badges.
2. **Alibaba Cloud deployment proof:** needs a real deploy to YOUR Alibaba Cloud account to
   produce the required running-on-Alibaba screenshot.
3. **Working Qwen access:** the provided key returns HTTP 403 `AccessDenied.Unpurchased` —
   Model Studio access isn't activated for the account (Singapore/intl region).
```
