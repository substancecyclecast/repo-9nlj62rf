"use client";

import { useEffect, useState } from "react";
import {
  api,
  fmtPct,
  fmtUsd,
  type Overview,
  type Recommendation,
  type Wallet,
} from "@/lib/api";
import { AllocationBar, PageHeader, Spinner, StatCard, StatusPill } from "@/components/ui";

export default function DashboardPage() {
  const [ov, setOv] = useState<Overview | null>(null);
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.overview(), api.wallets(), api.recommendations()])
      .then(([o, w, r]) => {
        setOv(o);
        setWallets(w);
        setRecs(r);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (error)
    return (
      <div className="card text-rose-300">
        Could not reach the API. Is the backend running on :8000?
        <pre className="mt-2 text-xs text-slate-400">{error}</pre>
      </div>
    );
  if (!ov) return <Spinner label="Loading treasury…" />;

  return (
    <div>
      <PageHeader
        title="Treasury Dashboard"
        subtitle={`${ov.organization.name} · ${ov.wallet_count} multisig wallets across ${
          Object.keys(ov.by_chain).length
        } chains`}
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Net Asset Value" value={fmtUsd(ov.nav_usd)} sub="liquid + deployed" />
        <StatCard
          label="Liquid (wallets)"
          value={fmtUsd(ov.liquid_usd)}
          sub={`${fmtPct(ov.stablecoin_pct)} stablecoins`}
          accent="green"
        />
        <StatCard
          label="Deployed in yield"
          value={fmtUsd(ov.yield_usd)}
          sub={`~${fmtUsd(ov.projected_annual_yield_usd)}/yr projected`}
          accent="brand"
        />
        <StatCard
          label="Volatile exposure"
          value={fmtUsd(ov.volatile_usd)}
          sub="ETH / BTC / SOL / XLM"
          accent="amber"
        />
      </div>

      {/* Stellar & RWA summary */}
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="card border-l-2 border-l-blue-400">
          <h2 className="mb-2 text-sm font-semibold text-blue-300">Stellar Treasury</h2>
          <p className="text-2xl font-bold text-white">
            {fmtUsd(
              Object.entries(ov.by_chain)
                .filter(([k]) => k === "stellar")
                .reduce((sum, [, v]) => sum + v, 0)
            )}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            EMEA payroll + RWA positions on Stellar/Soroban
          </p>
        </div>
        <div className="card border-l-2 border-l-emerald-400">
          <h2 className="mb-2 text-sm font-semibold text-emerald-300">RWA (Tokenized T-Bills)</h2>
          <p className="text-2xl font-bold text-white">
            {fmtUsd(ov.yield_usd * 0.44)}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            US T-Bills + EMEA MMF on Stellar &middot; MiCA-compliant
          </p>
        </div>
        <div className="card border-l-2 border-l-purple-400">
          <h2 className="mb-2 text-sm font-semibold text-purple-300">EMEA Payroll Savings</h2>
          <p className="text-2xl font-bold text-white">~67%</p>
          <p className="mt-1 text-xs text-slate-400">
            Cost reduction via Stellar vs traditional rails (SWIFT/SEPA)
          </p>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="card">
          <h2 className="mb-4 text-sm font-semibold text-white">Allocation by chain</h2>
          <AllocationBar data={ov.by_chain} />
        </div>
        <div className="card">
          <h2 className="mb-4 text-sm font-semibold text-white">Allocation by asset</h2>
          <AllocationBar data={ov.by_asset} />
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-5">
        <div className="card lg:col-span-3">
          <h2 className="mb-3 text-sm font-semibold text-white">Multisig wallets</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="th">Wallet</th>
                  <th className="th">Chain</th>
                  <th className="th">Signers</th>
                  <th className="th text-right">Value</th>
                </tr>
              </thead>
              <tbody>
                {wallets.map((w) => (
                  <tr key={w.wallet_id} className="border-t border-white/5">
                    <td className="td">
                      <div className="font-medium text-white">{w.label}</div>
                      <div className="font-mono text-[11px] text-slate-500">
                        {w.address.slice(0, 10)}…{w.address.slice(-6)}
                      </div>
                    </td>
                    <td className="td capitalize">{w.chain}</td>
                    <td className="td">
                      {w.threshold}/{w.owners} · {w.kind}
                    </td>
                    <td className="td text-right font-medium">{fmtUsd(w.usd_value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold text-white">Agent recommendations</h2>
          {recs.length === 0 && (
            <p className="text-sm text-slate-400">Treasury is within policy. No actions needed.</p>
          )}
          <div className="space-y-3">
            {recs.map((r, i) => (
              <div key={i} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                <div className="mb-1 flex items-center justify-between gap-2">
                  <StatusPill value={r.severity} />
                  <span className="text-xs text-slate-400">{fmtUsd(r.amount_usd)}</span>
                </div>
                <div className="text-sm font-medium text-white">{r.title}</div>
                <div className="mt-1 text-xs text-slate-400">{r.detail}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
