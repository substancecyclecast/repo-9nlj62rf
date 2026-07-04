# Monitoring Guide

## SLO Definitions

| SLO | Target | Measurement |
|-----|--------|-------------|
| Availability | 99.5% monthly | `up` metric in Prometheus |
| API Latency (p95) | < 3 seconds | `http_request_duration_seconds` histogram |
| Error Rate | < 1% | `http_requests_total{status=~"5.."}` / total |
| LLM Response Time (p95) | < 30 seconds | `snabagent_lot_run_latency_seconds` |
| Lot Processing Success Rate | > 95% | `snabagent_lot_finished_total{status!="failed"}` / total |

## Prometheus Metrics

SnabAgent exposes metrics at `GET /metrics` (Prometheus format).

### Application Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `snabagent_lot_created_total` | Counter | Lots created (by customer_id) |
| `snabagent_lot_finished_total` | Counter | Lots finished (by status) |
| `snabagent_lot_run_latency_seconds` | Histogram | End-to-end lot processing time |
| `http_requests_total` | Counter | HTTP requests (by method, path, status) |
| `http_request_duration_seconds` | Histogram | HTTP request duration |

### Infrastructure Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `process_cpu_seconds_total` | Counter | CPU usage |
| `process_resident_memory_bytes` | Gauge | Memory usage |
| `python_gc_objects_collected_total` | Counter | GC activity |

## Grafana Dashboard

Import `docs/grafana/snabagent-dashboard.json` into Grafana.

### Panels
1. **Request Rate** — requests/sec by endpoint
2. **Error Rate** — 5xx errors as percentage
3. **Latency Distribution** — p50/p95/p99 histograms
4. **Lot Processing** — created vs finished over time
5. **LLM Latency** — per-agent LLM call times
6. **Active Lots** — gauge of lots in processing states
7. **Top Errors** — most common error types
8. **Database Connections** — pool utilization
9. **Redis Operations** — pub/sub throughput
10. **Memory & CPU** — resource utilization
11. **SLO Compliance** — burn rate and error budget

## Alerting Rules

### Critical (PagerDuty)

```yaml
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Error rate > 5% for 5 minutes"

- alert: APIDown
  expr: up{job="snabagent"} == 0
  for: 1m
  labels:
    severity: critical

- alert: DatabaseConnectionExhausted
  expr: snabagent_db_pool_checked_out / snabagent_db_pool_size > 0.9
  for: 5m
  labels:
    severity: critical
```

### Warning (Slack)

```yaml
- alert: HighLatency
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 3
  for: 10m
  labels:
    severity: warning

- alert: LotProcessingFailure
  expr: rate(snabagent_lot_finished_total{status="failed"}[1h]) > 0.1
  for: 15m
  labels:
    severity: warning
```

## Logging

### Structured Logging (structlog)

All logs are structured JSON via `structlog`:

```json
{
  "event": "lot_finished",
  "lot_id": "abc-123",
  "status": "report_ready",
  "duration_sec": 12.5,
  "level": "info",
  "timestamp": "2026-06-04T10:00:00Z"
}
```

### Log Levels
- `ERROR` — unrecoverable failures
- `WARNING` — degraded functionality, circuit breaker events
- `INFO` — lot lifecycle, auth events
- `DEBUG` — LLM prompts, SQL queries (dev only)

## Runbook

### Scenario 1: High Error Rate (>5%)

1. Check `/health/ready` for component failures
2. Review logs: `docker compose logs api --tail=100`
3. Check LLM circuit breaker: look for "Circuit breaker: OPEN" in logs
4. If DB-related: check connection pool metrics
5. Escalation: restart API → `docker compose restart api`

### Scenario 2: LLM Timeout

1. Check circuit breaker status in logs
2. Verify LLM provider status (YandexGPT / OpenAI status pages)
3. Switch to fallback LLM: update `LLM_PRIMARY` in `.env`
4. Restart: `docker compose restart api`

### Scenario 3: Database Connection Exhaustion

1. Check `pool_size` in metrics
2. Review slow queries: enable `SQLALCHEMY_ECHO=true`
3. Increase pool: `DB_POOL_SIZE=30` in `.env`
4. Restart API

### Scenario 4: Memory Leak

1. Check `process_resident_memory_bytes` trend
2. Force GC: `import gc; gc.collect()`
3. Restart API with memory limit: `mem_limit: 2g` in docker-compose
4. Profile with `tracemalloc` if recurring

### Scenario 5: Lot Stuck in Processing

1. Find lot: `GET /api/v1/lots/{lot_id}`
2. Check audit log: `GET /api/v1/lots/{lot_id}/audit`
3. Verify LLM health: check circuit breaker
4. Manual escalation: `POST /api/v1/lots/{lot_id}/reject`
5. Re-run if needed: create new lot with same request
