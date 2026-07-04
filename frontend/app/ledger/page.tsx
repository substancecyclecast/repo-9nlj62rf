"use client";

import { useEffect, useState } from "react";
import {
  api,
  fmtUsd,
  type JournalEntry,
  type TrialBalance,
  type Transaction,
} from "@/lib/api";
import { PageHeader, Spinner, StatusPill } from "@/components/ui";

type Tab = "trial" | "journal" | "transactions";

export default function LedgerPage() {
  const [tab, setTab] = useState<Tab>("trial");
  const [tb, setTb] = useState<TrialBalance | null>(null);
  const [journal, setJournal] = useState<JournalEntry[]>([]);
  const [txs, setTxs] = useState<Transaction[]>([]);

  const refresh = () => {
    api.trialBalance().then(setTb).catch(() => {});
    api.journal().then(setJournal).catch(() => {});
    api.transactions().then(setTxs).catch(() => {});
  };
  useEffect(refresh, []);

  return (
    <div>
      <PageHeader
        title="Ledger & Auditor Reports"
        subtitle="Double-entry books generated automatically from on-chain activity. Export QuickBooks CSV or a PDF working paper for your auditor."
      >
        <div className="flex flex-wrap gap-2">
          <a className="btn-primary" href={api.reportUrls.auditorPdf} target="_blank" rel="noreferrer">
            Auditor PDF
          </a>
          <a className="btn-ghost" href={api.reportUrls.quickbooksCsv} target="_blank" rel="noreferrer">
            QuickBooks CSV
          </a>
          <a className="btn-ghost" href={api.reportUrls.transactionsCsv} target="_blank" rel="noreferrer">
            Transactions CSV
          </a>
        </div>
      </PageHeader>

      {tb && (
        <div className="mb-4 flex items-center gap-3 text-sm">
          <span
            className={`pill ${tb.balanced ? "bg-emerald-500/15 text-emerald-300" : "bg-rose-500/15 text-rose-300"}`}
          >
            {tb.balanced ? "Books balanced" : "OUT OF BALANCE"}
          </span>
          <span className="text-slate-400">
            Σ debit {fmtUsd(tb.total_debit)} = Σ credit {fmtUsd(tb.total_credit)}
          </span>
        </div>
      )}

      <div className="mb-4 flex gap-1 rounded-lg border border-white/10 bg-white/[0.02] p-1 text-sm">
        {(
          [
            ["trial", "Trial balance"],
            ["journal", "General journal"],
            ["transactions", "Transactions"],
          ] as [Tab, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`rounded-md px-3 py-1.5 ${
              tab === key ? "bg-brand text-white" : "text-slate-300 hover:bg-white/5"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "trial" && (
        <div className="card overflow-x-auto">
          {!tb ? (
            <Spinner />
          ) : (
            <table className="w-full">
              <thead>
                <tr>
                  <th className="th">Code</th>
                  <th className="th">Account</th>
                  <th className="th">Type</th>
                  <th className="th text-right">Debit</th>
                  <th className="th text-right">Credit</th>
                  <th className="th text-right">Balance</th>
                </tr>
              </thead>
              <tbody>
                {tb.rows.map((r) => (
                  <tr key={r.code} className="border-t border-white/5">
                    <td className="td font-mono text-xs text-slate-400">{r.code}</td>
                    <td className="td text-white">{r.name}</td>
                    <td className="td capitalize text-slate-400">{r.type}</td>
                    <td className="td text-right">{r.debit ? fmtUsd(r.debit) : "—"}</td>
                    <td className="td text-right">{r.credit ? fmtUsd(r.credit) : "—"}</td>
                    <td className="td text-right font-medium">{fmtUsd(r.balance)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "journal" && (
        <div className="space-y-3">
          {journal.map((e) => (
            <div key={e.id} className="card">
              <div className="mb-2 flex items-center justify-between">
                <div className="text-sm font-medium text-white">
                  #{e.id} · {e.memo}
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <span>{e.date.slice(0, 10)}</span>
                  <StatusPill value={e.source} />
                </div>
              </div>
              <table className="w-full">
                <tbody>
                  {e.lines.map((l, i) => (
                    <tr key={i} className="border-t border-white/5">
                      <td className="td">
                        <span className="font-mono text-xs text-slate-500">{l.account_code}</span>{" "}
                        {l.account_name}
                      </td>
                      <td className="td text-right text-emerald-300">
                        {l.debit ? fmtUsd(l.debit) : ""}
                      </td>
                      <td className="td text-right text-sky-300">
                        {l.credit ? fmtUsd(l.credit) : ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      {tab === "transactions" && (
        <div className="card overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                <th className="th">Date</th>
                <th className="th">Type</th>
                <th className="th">Counterparty</th>
                <th className="th">Category</th>
                <th className="th">Chain</th>
                <th className="th text-right">USD</th>
                <th className="th">Status</th>
              </tr>
            </thead>
            <tbody>
              {txs.map((t) => (
                <tr key={t.id} className="border-t border-white/5">
                  <td className="td text-xs text-slate-400">{t.created_at.slice(0, 16).replace("T", " ")}</td>
                  <td className="td capitalize">{t.tx_type}</td>
                  <td className="td text-white">{t.counterparty || "—"}</td>
                  <td className="td">
                    <span className="pill bg-white/5 text-slate-300">{t.category}</span>
                  </td>
                  <td className="td capitalize">{t.chain}</td>
                  <td className="td text-right">{fmtUsd(t.usd_value, 2)}</td>
                  <td className="td">
                    <StatusPill value={t.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
