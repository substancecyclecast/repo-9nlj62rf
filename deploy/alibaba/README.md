# deploy/alibaba — Qwen Cloud Global AI Hackathon deployment

Everything needed to run SnabAgent on **Alibaba Cloud** with **Qwen Cloud** as the LLM.

| File | Purpose |
|---|---|
| [`architecture.md`](./architecture.md) | Architecture + Mermaid diagram (Qwen → agents → DB) and the winning-criteria mapping. |
| [`ecs-deployment.md`](./ecs-deployment.md) | Step-by-step Alibaba Cloud ECS deployment (console + `aliyun` CLI). |
| [`docker-compose.alibaba.yml`](./docker-compose.alibaba.yml) | Single-node Compose stack (api + worker + streamlit + postgres + qdrant + redis). |
| [`deploy.sh`](./deploy.sh) | One-shot bootstrap script to run on the ECS box. |
| [`.env.alibaba.example`](./.env.alibaba.example) | Environment template pre-wired for Qwen. |

## TL;DR

```bash
# on a fresh Ubuntu 22.04 ECS instance
git clone <repo> snabagent && cd snabagent
bash deploy/alibaba/deploy.sh         # creates .env, then stops
nano .env                             # set LLM_QWEN_API_KEY
bash deploy/alibaba/deploy.sh         # builds + starts + seeds
# → http://<ECS_IP>:8000/docs  and  http://<ECS_IP>:8501
```

The only required secret is `LLM_QWEN_API_KEY` (your DashScope key). All agent reasoning
and the independent verifier run on Qwen models.
