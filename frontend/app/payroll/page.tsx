"use client";

import { useEffect, useRef, useState } from "react";
import { api, fmtUsd, type Batch } from "@/lib/api";
import { PageHeader, StatCard, StatusPill } from "@/components/ui";

type Proposal = { chain: string; payment_count: number; total_usd: number; safe_tx_hash: string };

export default function PayrollPage() {
  const [batch, setBatch] = useState<Batch | null>(null);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState<number | null>(null);
  const [executedCount, setExecutedCount] = useState<number | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api
      .batches()
      .then((b) => b[0] && loadBatch(b[0].id))
      .catch(() => {});
  }, []);

  function reset() {
    setProposals([]);
    setElapsed(null);
    setExecutedCount(null);
    setError("");
  }

  async function loadBatch(id: number) {
    const b = await api.batch(id);
    setBatch(b);
    if (b.status !== "draft") {
      // best-effort: surface execution state
      setExecutedCount(b.payments.filter((p) => p.status === "executed").length || null);
    }
  }

  async function runSample() {
    reset();
    setBusy("sample");
    try {
      const b = await api.sampleBatch();
      setBatch(b);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy("");
    }
  }

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    reset();
    setBusy("upload");
    try {
      const b = await api.uploadPayroll(file.name.replace(/\.csv$/i, ""), file);
      setBatch(b);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy("");
    }
  }

  async function propose() {
    if (!batch) return;
    setBusy("propose");
    try {
      const r = await api.proposeBatch(batch.id);
      setProposals(r.proposals);
      await loadBatch(batch.id);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy("");
    }
  }

  async function execute() {
    if (!batch) return;
    setBusy("execute");
    const start = performance.now();
    try {
      const r = await api.executeBatch(batch.id);
      setElapsed((performance.now() - start) / 1000);
      setExecutedCount(r.executed_payments);
      await loadBatch(batch.id);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy("");
    }
  }

  const payable = batch?.payments.filter((p) => p.status !== "blocked_compliance") ?? [];
  const blocked = batch?.payments.filter((p) => p.status === "blocked_compliance") ?? [];
  const chains = Array.from(new Set(payable.map((p) => p.chain)));

  return (
    <div>
      <PageHeader
        title="Payroll & Global Payouts"
        subtitle="Import contractors, let the agent route each payee to the cheapest chain (or fiat off-ramp), screen compliance, then settle via multisig — with double-entry bookkeeping."
      >
        <div className="flex gap-2">
          <button className="btn-ghost" disabled={!!busy} onClick={runSample}>
            {busy === "sample" ? "Loading…" : "Run sample batch"}
          </button>
          <button className="btn-primary" disabled={!!busy} onClick={() => fileRef.current?.click()}>
            {busy === "upload" ? "Parsing…" : "Upload CSV"}
          </button>
          <input ref={fileRef} type="file" accept=".csv" hidden onChange={onUpload} />
        </div>
      </PageHeader>

      {error && (
        <div className="card mb-4 text-sm text-rose-300">
          <pre className="whitespace-pre-wrap text-xs">{error}</pre>
        </div>
      )}

      {executedCount !== null && (
        <div className="mb-4 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-emerald-200">
          <div className="text-lg font-semibold">
            Paid {executedCount} contractors{elapsed !== null ? ` in ${elapsed.toFixed(2)}s` : ""} ✦
          </div>
          <div className="text-sm text-emerald-300/80">
            Settled across {chains.length} networks · books reconciled · auditor report ready.
          </div>
        </div>
      )}

      {!batch && !busy && (
        <div className="card text-sm text-slate-400">
          Upload a payroll CSV or click <span className="text-white">Run sample batch</span> to load
          12 contractors across 10 countries.
        </div>
      )}

      {batch && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="Payees" value={String(batch.payment_count)} />
            <StatCard label="Payable total" value={fmtUsd(batch.total_usd)} accent="green" />
            <StatCard label="Network + rail fees" value={fmtUsd(batch.total_fees_usd, 2)} accent="amber" />
            <StatCard label="Settlement networks" value={String(chains.length)} accent="brand" />
          </div>

          <div className="card mt-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">
                {batch.name} · <StatusPill value={batch.status} />
              </h2>
              <div className="flex gap-2">
                <button className="btn-ghost" disabled={!!busy} onClick={propose}>
                  {busy === "propose" ? "Proposing…" : "Propose to multisig"}
                </button>
                <button className="btn-primary" disabled={!!busy} onClick={execute}>
                  {busy === "execute" ? "Settling…" : "Execute payouts"}
                </button>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="th">Payee</th>
                    <th className="th">Country</th>
                    <th className="th text-right">Amount</th>
                    <th className="th">Route</th>
                    <th className="th">Chain</th>
                    <th className="th text-right">Fee</th>
                    <th className="th">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {batch.payments.map((p) => (
                    <tr key={p.id} className="border-t border-white/5">
                      <td className="td font-medium text-white">{p.payee_name}</td>
                      <td className="td">{p.country || "—"}</td>
                      <td className="td text-right">{fmtUsd(p.amount_usd, 2)}</td>
                      <td className="td text-xs text-slate-400">{p.route}</td>
                      <td className="td capitalize">{p.chain}</td>
                      <td className="td text-right text-slate-400">{fmtUsd(p.fee_usd, 2)}</td>
                      <td className="td">
                        <StatusPill value={p.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {blocked.length > 0 && (
              <p className="mt-3 text-xs text-rose-300">
                {blocked.length} payment(s) blocked by compliance screening and excluded from the
                payable total.
              </p>
            )}
          </div>

          {proposals.length > 0 && (
            <div className="card mt-4">
              <h2 className="mb-3 text-sm font-semibold text-white">Multisig proposals</h2>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {proposals.map((p) => (
                  <div key={p.safe_tx_hash} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                    <div className="flex items-center justify-between">
                      <span className="font-medium capitalize text-white">{p.chain}</span>
                      <span className="text-xs text-slate-400">{p.payment_count} payments</span>
                    </div>
                    <div className="mt-1 text-sm text-slate-300">{fmtUsd(p.total_usd)}</div>
                    <div className="mt-2 truncate font-mono text-[11px] text-slate-500">
                      {p.safe_tx_hash}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
