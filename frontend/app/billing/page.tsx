"use client";

import { useEffect, useState } from "react";
import { api, fmtUsd, type BillingSummary, type Invoice } from "@/lib/api";
import { PageHeader, Spinner, StatCard } from "@/components/ui";

export default function BillingPage() {
  const [summary, setSummary] = useState<BillingSummary | null>(null);
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.billingSummary(), api.invoice()])
      .then(([s, i]) => {
        setSummary(s);
        setInvoice(i);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (error)
    return (
      <div className="card text-rose-300">
        Could not load billing.
        <pre className="mt-2 text-xs text-slate-400">{error}</pre>
      </div>
    );
  if (!summary || !invoice) return <Spinner label="Loading billing…" />;

  const months = Object.entries(summary.volume_by_month);
  const maxVol = Math.max(1, ...months.map(([, v]) => v));

  return (
    <div>
      <PageHeader
        title="Billing & Revenue"
        subtitle={`Mandate monetizes via a ${summary.take_rate_bps} bps take-rate on settled payment volume plus a flat platform fee — usage-based SaaS economics.`}
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Estimated MRR" value={fmtUsd(summary.estimated_mrr_usd)} accent="brand" sub="platform fee + take-rate" />
        <StatCard label="Settled volume" value={fmtUsd(summary.settled_volume_usd)} accent="green" sub={`${summary.payment_count} payments`} />
        <StatCard label="Take-rate revenue (lifetime)" value={fmtUsd(summary.lifetime_take_rate_revenue_usd, 2)} />
        <StatCard label="Saved vs SWIFT" value={fmtUsd(summary.fees_saved_vs_swift_usd, 2)} accent="amber" sub="delivered to customer" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-5">
        {/* Current invoice */}
        <div className="card lg:col-span-3">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-white">Current invoice</h2>
              <p className="text-xs text-slate-400">
                {invoice.invoice_number} · {invoice.period}
              </p>
            </div>
            <span className="pill bg-amber-500/15 text-amber-300">{invoice.status}</span>
          </div>
          <table className="w-full">
            <thead>
              <tr>
                <th className="th">Description</th>
                <th className="th text-right">Qty</th>
                <th className="th text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {invoice.line_items.map((li, idx) => (
                <tr key={idx} className="border-t border-white/5">
                  <td className="td">{li.description}</td>
                  <td className="td text-right">{li.quantity}</td>
                  <td className="td text-right font-medium text-white">{fmtUsd(li.amount_usd, 2)}</td>
                </tr>
              ))}
              <tr className="border-t border-white/10">
                <td className="td font-semibold text-white" colSpan={2}>
                  Total due
                </td>
                <td className="td text-right text-lg font-bold text-white">
                  {fmtUsd(invoice.total_usd, 2)}
                </td>
              </tr>
            </tbody>
          </table>
          <p className="mt-3 text-xs text-slate-500">
            Settled in USDC or via ACH/SEPA. Stripe + crypto rails supported in production.
          </p>
        </div>

        {/* Plan + volume chart */}
        <div className="card lg:col-span-2">
          <h2 className="mb-1 text-sm font-semibold text-white">{summary.plan} plan</h2>
          <p className="text-xs text-slate-400">
            {summary.take_rate_bps} bps · {fmtUsd(summary.platform_fee_usd)}/mo platform fee
          </p>
          <div className="mt-4 space-y-2">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-400">
              Settled volume by month
            </div>
            {months.length === 0 && (
              <div className="text-sm text-slate-500">No settled volume yet — run a payroll batch.</div>
            )}
            {months.map(([m, v]) => (
              <div key={m} className="flex items-center gap-3">
                <span className="w-16 text-xs text-slate-400">{m}</span>
                <div className="h-3 flex-1 overflow-hidden rounded-full bg-white/5">
                  <div className="h-full bg-brand" style={{ width: `${(v / maxVol) * 100}%` }} />
                </div>
                <span className="w-24 text-right text-xs text-slate-300">{fmtUsd(v)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
