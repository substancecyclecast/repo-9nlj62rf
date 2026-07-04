# Deploying SnabAgent on Alibaba Cloud ECS (Qwen-powered)

This is the reference deployment used for the **Qwen Cloud Global AI Hackathon**.
SnabAgent runs on a single Alibaba Cloud **ECS** instance with Docker Compose, and
all agent reasoning + verification is served by **Qwen Cloud (DashScope)** — no other
LLM provider is required.

```
Alibaba Cloud
└── ECS instance (ecs.g7.large, Ubuntu 22.04, 2 vCPU / 4–8 GB)
    └── Docker Compose stack
        ├── api        (FastAPI)      :8000
        ├── streamlit  (demo UI)      :8501
        ├── worker     (Celery)
        ├── postgres   (state + memory)
        ├── qdrant     (vector store: NSI + suppliers)
        └── redis      (Celery broker)
        ▲
        │ HTTPS (OpenAI-compatible)
        ▼
    Qwen Cloud / DashScope  (qwen-max primary, qwen-plus verifier)
```

## 0. Prerequisites

- An Alibaba Cloud account with ECS access (hackathon credits are fine).
- A **Qwen Cloud / DashScope API key** (Model Studio → API-KEY). This funds `LLM_QWEN_API_KEY`.
- Optional: the [`aliyun` CLI](https://help.aliyun.com/document_detail/121541.html) configured
  with `aliyun configure` (Access Key + region, e.g. `ap-southeast-1` / Singapore).

## 1. Provision the ECS instance

### Option A — Console (fastest)
1. ECS → Instances → **Create Instance** (Pay-as-you-go).
2. Region: **Singapore (ap-southeast-1)** — closest to the `dashscope-intl` endpoint.
3. Instance type: `ecs.g7.large` (2 vCPU / 8 GB). Image: **Ubuntu 22.04 64-bit**.
4. Public IP: **Assign** (or bind an EIP). System disk ≥ 40 GB.
5. **Security Group**: allow inbound TCP `22`, `8000`, `8501` (add `443` if you put a
   reverse proxy in front). Restrict `22` to your IP.
6. Create and note the **public IP**.

### Option B — aliyun CLI
```bash
# Look up an Ubuntu 22.04 image id in your region first, then:
aliyun ecs RunInstances \
  --RegionId ap-southeast-1 \
  --InstanceType ecs.g7.large \
  --ImageId <ubuntu-22.04-image-id> \
  --InternetMaxBandwidthOut 5 \
  --SecurityGroupId <your-sg-id> \
  --VSwitchId <your-vswitch-id> \
  --InstanceChargeType PostPaid \
  --Amount 1
```
Open the ports on the security group:
```bash
for p in 22 8000 8501; do
  aliyun ecs AuthorizeSecurityGroup --RegionId ap-southeast-1 \
    --SecurityGroupId <your-sg-id> --IpProtocol tcp --PortRange ${p}/${p} \
    --SourceCidrIp 0.0.0.0/0
done
```

## 2. Deploy the stack

SSH into the instance and run:
```bash
ssh root@<ECS_PUBLIC_IP>

git clone <your-repo-url> snabagent && cd snabagent

# First run creates .env from the template and stops so you can add your key:
bash deploy/alibaba/deploy.sh

# Edit .env → set LLM_QWEN_API_KEY (and change SECRET_KEY / API_KEY / POSTGRES_PASSWORD)
nano .env

# Second run builds images, starts everything, seeds demo data:
bash deploy/alibaba/deploy.sh
```

The script installs Docker if needed, brings up the Compose stack
(`deploy/alibaba/docker-compose.alibaba.yml`), applies DB migrations, and seeds NSI /
suppliers.

## 3. Verify

```bash
# On the box:
docker compose -f deploy/alibaba/docker-compose.alibaba.yml ps
curl -s http://localhost:8000/healthz

# From your laptop:
open http://<ECS_PUBLIC_IP>:8000/docs      # FastAPI
open http://<ECS_PUBLIC_IP>:8501           # Streamlit demo UI
```

Confirm Qwen is actually being used — every LLM call is logged in the audit trail with
its `model_name` (`qwen-max` / `qwen-plus`). Check via the API:
```bash
curl -s "http://<ECS_PUBLIC_IP>:8000/api/v1/audit/<lot_id>" | jq '.[].model_name'
```

## 4. Proof of deployment (for submission)

Capture these for the Devpost submission:
- `docker compose ... ps` showing all services **healthy/up**.
- The `/docs` and Streamlit pages loading on the public ECS IP.
- An audit entry showing `model_name: "qwen-max"` / `"qwen-plus"` (proves Qwen + verifier).
- The ECS instance detail page (region = Singapore) in the Alibaba console.

Screenshots go under `submission_package/` and are referenced from the pitch deck.

## 5. Teardown

```bash
docker compose -f deploy/alibaba/docker-compose.alibaba.yml down -v
# then Stop/Release the ECS instance in the console (or `aliyun ecs DeleteInstance`).
```

## Cost note
`ecs.g7.large` PostPaid is a few cents/hour; Qwen usage during the demo is well within
the hackathon voucher. Stop the instance when not demoing to avoid charges.
