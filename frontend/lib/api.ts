// Lightweight typed API client for the Mandate backend.
// When NEXT_PUBLIC_API_BASE is set (production), calls go directly to the backend.
// Otherwise we hit the same origin and rely on Next.js rewrites to proxy
// /api/* to the FastAPI service (see next.config.mjs).

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";

export const ORG_ID = 1;

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// --- Types ---------------------------------------------------------------

export interface Overview {
  organization: { id: number; name: string; slug: string };
  nav_usd: number;
  liquid_usd: number;
  yield_usd: number;
  stablecoin_usd: number;
  volatile_usd: number;
  stablecoin_pct: number;
  by_chain: Record<string, number>;
  by_asset: Record<string, number>;
  projected_annual_yield_usd: number;
  policy: Record<string, number | string>;
  wallet_count: number;
}

export interface WalletAsset {
  asset: string;
  amount: number;
  usd_price: number;
  usd_value: number;
}
export interface Wallet {
  wallet_id: number;
  label: string;
  chain: string;
  address: string;
  kind: string;
  threshold: number;
  owners: number;
  assets: WalletAsset[];
  usd_value: number;
}

export interface Recommendation {
  kind: string;
  severity: string;
  title: string;
  detail: string;
  amount_usd: number;
  venue?: string;
  apy?: number;
}

export interface AgentStep {
  idx: number;
  kind: string;
  tool: string;
  message: string;
  arguments: Record<string, unknown>;
  observation: Record<string, unknown>;
}
export interface AgentRun {
  id: number;
  goal: string;
  status: string;
  provider: string;
  summary: string;
  steps: AgentStep[];
}

export interface Payment {
  id: number;
  payee_name: string;
  country: string;
  amount_usd: number;
  chain: string;
  asset: string;
  to_address: string;
  fee_usd: number;
  route: string;
  status: string;
  memo: string;
}
export interface Batch {
  id: number;
  name: string;
  status: string;
  total_usd: number;
  total_fees_usd: number;
  payment_count: number;
  created_at: string;
  payments: Payment[];
}

export interface TrialBalanceRow {
  code: string;
  name: string;
  type: string;
  debit: number;
  credit: number;
  balance: number;
}
export interface TrialBalance {
  rows: TrialBalanceRow[];
  total_debit: number;
  total_credit: number;
  balanced: boolean;
}

export interface JournalLine {
  account_code: string;
  account_name: string;
  debit: number;
  credit: number;
  memo: string;
}
export interface JournalEntry {
  id: number;
  date: string;
  memo: string;
  reference: string;
  source: string;
  balanced: boolean;
  total_debit: number;
  total_credit: number;
  lines: JournalLine[];
}

export interface YieldVenue {
  venue: string;
  asset: string;
  chain: string;
  apy: number;
  risk_tier: string;
}

export interface Transaction {
  id: number;
  tx_type: string;
  status: string;
  chain: string;
  asset: string;
  amount: number;
  usd_value: number;
  fee_usd: number;
  counterparty: string;
  category: string;
  memo: string;
  created_at: string;
}

export interface BillingSummary {
  currency: string;
  plan: string;
  take_rate_bps: number;
  platform_fee_usd: number;
  settled_volume_usd: number;
  payment_count: number;
  lifetime_take_rate_revenue_usd: number;
  mtd_volume_usd: number;
  mtd_take_rate_usd: number;
  estimated_mrr_usd: number;
  current_invoice_usd: number;
  fees_saved_vs_swift_usd: number;
  volume_by_month: Record<string, number>;
}
export interface InvoiceLine {
  description: string;
  quantity: number;
  unit_usd: number | null;
  amount_usd: number;
}
export interface Invoice {
  invoice_number: string;
  period: string;
  currency: string;
  line_items: InvoiceLine[];
  subtotal_usd: number;
  total_usd: number;
  status: string;
  issued_at: string;
}

export interface AuditEntry {
  id: number;
  actor: string;
  action: string;
  resource: string;
  status_code: number;
  detail: Record<string, unknown>;
  created_at: string | null;
}

export interface WebhookDelivery {
  id: number;
  event: string;
  channel: string;
  target: string;
  status: string;
  response_code: number;
  payload: Record<string, unknown>;
  created_at: string | null;
}

export interface Readiness {
  ready: boolean;
  version: string;
  environment: string;
  integration_mode: string;
  checks: Record<string, string>;
}

// --- Endpoints -----------------------------------------------------------

export const api = {
  overview: () => http<Overview>(`/orgs/${ORG_ID}/overview`),
  wallets: () => http<Wallet[]>(`/orgs/${ORG_ID}/wallets`),
  recommendations: () => http<Recommendation[]>(`/orgs/${ORG_ID}/recommendations`),
  transactions: () => http<Transaction[]>(`/orgs/${ORG_ID}/transactions?limit=100`),

  runAgent: (goal: string) =>
    http<AgentRun>(`/orgs/${ORG_ID}/agent/run`, {
      method: "POST",
      body: JSON.stringify({ goal }),
    }),
  agentRuns: () => http<AgentRun[]>(`/orgs/${ORG_ID}/agent/runs`),

  batches: () => http<Batch[]>(`/orgs/${ORG_ID}/payroll/batches`),
  sampleBatch: (name = "Sample payroll (12 contractors)") =>
    http<Batch>(`/orgs/${ORG_ID}/payroll/sample?name=${encodeURIComponent(name)}`, {
      method: "POST",
    }),
  batch: (id: number) => http<Batch>(`/orgs/${ORG_ID}/payroll/batches/${id}`),
  uploadPayroll: async (name: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(
      `${API_BASE}/api/v1/orgs/${ORG_ID}/payroll/upload?name=${encodeURIComponent(name)}`,
      { method: "POST", body: form }
    );
    if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
    return (await res.json()) as Batch;
  },
  proposeBatch: (id: number) =>
    http<{ proposals: { chain: string; payment_count: number; total_usd: number; safe_tx_hash: string }[] }>(
      `/orgs/${ORG_ID}/payroll/batches/${id}/propose`,
      { method: "POST" }
    ),
  executeBatch: (id: number) =>
    http<{ executed_payments: number; total_usd: number; total_fees_usd: number }>(
      `/orgs/${ORG_ID}/payroll/batches/${id}/execute`,
      { method: "POST" }
    ),

  trialBalance: () => http<TrialBalance>(`/orgs/${ORG_ID}/ledger/trial-balance`),
  journal: () => http<JournalEntry[]>(`/orgs/${ORG_ID}/ledger/journal`),
  yieldVenues: () => http<YieldVenue[]>(`/orgs/${ORG_ID}/yield/venues`),

  agentRun: (tool: string, args: Record<string, unknown>) =>
    http<{ ok: boolean; data: Record<string, unknown>; message: string }>(
      `/orgs/${ORG_ID}/agent/tool`,
      { method: "POST", body: JSON.stringify({ tool, arguments: args }) }
    ),

  billingSummary: () => http<BillingSummary>(`/orgs/${ORG_ID}/billing/summary`),
  invoice: () => http<Invoice>(`/orgs/${ORG_ID}/billing/invoice`),
  audit: (limit = 50) => http<AuditEntry[]>(`/orgs/${ORG_ID}/audit?limit=${limit}`),
  webhookDeliveries: (limit = 25) =>
    http<WebhookDelivery[]>(`/orgs/${ORG_ID}/webhooks/deliveries?limit=${limit}`),
  testWebhook: () =>
    http<{ delivered: WebhookDelivery[] }>(`/orgs/${ORG_ID}/webhooks/test`, { method: "POST" }),
  readiness: () => fetch(`${API_BASE}/readyz`).then((r) => r.json() as Promise<Readiness>),

  reportUrls: {
    auditorPdf: `${API_BASE}/api/v1/orgs/${ORG_ID}/reports/auditor.pdf`,
    quickbooksCsv: `${API_BASE}/api/v1/orgs/${ORG_ID}/reports/quickbooks.csv`,
    transactionsCsv: `${API_BASE}/api/v1/orgs/${ORG_ID}/reports/transactions.csv`,
  },
};

export function fmtUsd(n: number, max = 0): string {
  return n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: max,
  });
}
export function fmtPct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}
