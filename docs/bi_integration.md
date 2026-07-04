# BI Integration Guide

## Overview

SnabAgent provides data export endpoints for Business Intelligence tools:
- **CSV** for Excel, PowerBI, Tableau
- **JSON Lines** for DataLens, custom pipelines
- **Prometheus metrics** for Grafana

## Export Endpoints

### CSV Export

```bash
GET /api/v1/export/lots.csv
```

Returns all lots as CSV file. Requires `admin` role.

Headers: `Content-Type: text/csv`, `Content-Disposition: attachment; filename=lots_export.csv`

Fields: `id, status, category, phase, customer_id, total_estimated_rub, created_at, updated_at, closed_at, requires_human, escalation_reason`

### JSON Export

```bash
GET /api/v1/export/lots.json
```

Returns all lots as JSON Lines (NDJSON). Requires `admin` role.

### Usage with BI Tools

#### PowerBI
1. Open PowerBI Desktop
2. Get Data → Web
3. Enter URL: `https://your-domain/api/v1/export/lots.csv`
4. Add header: `X-API-Key: <your-key>`
5. Transform data as needed

#### Tableau
1. Connect → Web Data Connector or Text File
2. Point to exported CSV
3. Schedule refresh via Tableau Server

#### Yandex DataLens
1. Create Connection → CSV/File
2. Upload exported CSV
3. Create Dataset → Dashboard

## Analytics Dashboard

SnabAgent includes a built-in analytics page (Streamlit → 📈 Аналитика) with:

1. **KPI Cards**: Total lots, ready for review, approved, escalated, errors
2. **Trend Chart**: Lots processed over time
3. **Status Funnel**: Processing pipeline visualization
4. **Category Distribution**: Pie chart by procurement category

## Metrics for Grafana

Import `docs/grafana/snabagent-dashboard.json` for pre-built panels.

See `docs/monitoring.md` for full metrics reference.
