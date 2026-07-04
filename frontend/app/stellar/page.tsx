"use client";

import { useEffect, useState } from "react";
import { api, fmtUsd } from "@/lib/api";
import { PageHeader, Spinner, StatCard } from "@/components/ui";

interface StellarRWAVenue {
  venue: string;
  asset: string;
  chain: string;
  apy: number;
  risk_tier: string;
  rwa_metadata?: {
    name: string;
    issuer: string;
    asset_code: string;
    soroban_contract: string;
    maturity: string;
    min_investment_usd: number;
    regulatory: string;
  };
}

interface CrossBorderQuote {
  quote: {
    provider: string;
    protocol: string;
    rail: string;
    country: string;
    amount_usd: number;
    fee_usd: number;
    net_usd: number;
    eta: string;
  };
  vs_traditional: {
    stellar_fee_usd: number;
    traditional_fee_usd: number;
    savings_usd: number;
    savings_pct: number;
    stellar_eta: string;
  };
}

export default function StellarPage() {
  const [rwaVenues, setRwaVenues] = useState<StellarRWAVenue[]>([]);
  const [quote, setQuote] = useState<CrossBorderQuote | null>(null);
  const [loading, setLoading] = useState(true);
  const [quoteCountry, setQuoteCountry] = useState("NG");
  const [quoteAmount, setQuoteAmount] = useState(5000);

  useEffect(() => {
    api
      .agentRun("list_stellar_rwa_venues", {})
      .then((res) => {
        setRwaVenues((res.data?.venues as StellarRWAVenue[]) || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const getQuote = () => {
    api
      .agentRun("stellar_cross_border_quote", {
        amount_usd: quoteAmount,
        country: quoteCountry,
      })
      .then((res) => setQuote(res.data as unknown as CrossBorderQuote))
      .catch(console.error);
  };

  if (loading) return <Spinner label="Loading Stellar data…" />;

  return (
    <div>
      <PageHeader
        title="Stellar Integration"
        subtitle="Cross-border payments (EMEA/Africa) · RWA tokenized assets · Soroban policy engine"
      />

      {/* Key metrics */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Tx Cost" value="$0.00001" sub="~100 stroops per tx" accent="green" />
        <StatCard label="Finality" value="5 sec" sub="Stellar consensus" accent="brand" />
        <StatCard label="EMEA Countries" value="45+" sub="Anchor coverage" accent="blue" />
        <StatCard label="Cost Savings" value="~67%" sub="vs SWIFT/SEPA" accent="amber" />
      </div>

      {/* Cross-border quote tool */}
      <div className="card mt-6">
        <h2 className="mb-4 text-sm font-semibold text-white">
          Cross-Border Payment Calculator (Stellar vs Traditional)
        </h2>
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Amount (USD)</label>
            <input
              type="number"
              value={quoteAmount}
              onChange={(e) => setQuoteAmount(Number(e.target.value))}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-white text-sm w-32"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Country</label>
            <select
              value={quoteCountry}
              onChange={(e) => setQuoteCountry(e.target.value)}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-white text-sm"
            >
              <option value="NG">Nigeria</option>
              <option value="KE">Kenya</option>
              <option value="GH">Ghana</option>
              <option value="ZA">South Africa</option>
              <option value="AE">UAE</option>
              <option value="DE">Germany</option>
              <option value="FR">France</option>
              <option value="GB">UK</option>
              <option value="TR">Turkey</option>
              <option value="SN">Senegal</option>
            </select>
          </div>
          <button
            onClick={getQuote}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
          >
            Get Quote
          </button>
        </div>

        {quote && (
          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
              <h3 className="text-sm font-semibold text-blue-300 mb-2">Stellar Anchor</h3>
              <p className="text-lg font-bold text-white">{fmtUsd(quote.quote.fee_usd)} fee</p>
              <p className="text-xs text-slate-400">
                via {quote.quote.rail} · {quote.quote.eta} · SEP-31
              </p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <h3 className="text-sm font-semibold text-slate-300 mb-2">Traditional (SWIFT/Bridge)</h3>
              <p className="text-lg font-bold text-white">
                {fmtUsd(quote.vs_traditional.traditional_fee_usd)} fee
              </p>
              <p className="text-xs text-emerald-400">
                You save {fmtUsd(quote.vs_traditional.savings_usd)} ({quote.vs_traditional.savings_pct}% cheaper with Stellar)
              </p>
            </div>
          </div>
        )}
      </div>

      {/* RWA Venues */}
      <div className="card mt-6">
        <h2 className="mb-4 text-sm font-semibold text-white">
          Stellar RWA Yield Venues (Tokenized Real-World Assets)
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                <th className="th">Venue</th>
                <th className="th">Asset</th>
                <th className="th">APY</th>
                <th className="th">Risk</th>
                <th className="th">Regulatory</th>
              </tr>
            </thead>
            <tbody>
              {rwaVenues.map((v) => (
                <tr key={v.venue} className="border-t border-white/5">
                  <td className="td">
                    <div className="font-medium text-white">{v.rwa_metadata?.name || v.venue}</div>
                    <div className="font-mono text-[11px] text-slate-500">
                      {v.rwa_metadata?.soroban_contract?.slice(0, 12)}…
                    </div>
                  </td>
                  <td className="td">{v.asset}</td>
                  <td className="td text-emerald-400 font-medium">{(v.apy * 100).toFixed(2)}%</td>
                  <td className="td capitalize">{v.risk_tier}</td>
                  <td className="td text-xs text-slate-400">{v.rwa_metadata?.regulatory || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Soroban Policy Engine */}
      <div className="card mt-6">
        <h2 className="mb-4 text-sm font-semibold text-white">Soroban Policy Engine</h2>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="rounded-xl border border-white/10 p-4">
            <h3 className="text-sm font-semibold text-emerald-300">On-chain Spending Limits</h3>
            <p className="mt-2 text-xs text-slate-400">
              Soroban smart contract enforces per-tx and daily spending caps directly on Stellar.
              Transfers above $25k require additional co-signers.
            </p>
          </div>
          <div className="rounded-xl border border-white/10 p-4">
            <h3 className="text-sm font-semibold text-blue-300">Compliance Allowlist</h3>
            <p className="mt-2 text-xs text-slate-400">
              On-chain allowlist contract ensures only KYC-cleared addresses can receive payments.
              47 addresses currently allowlisted.
            </p>
          </div>
          <div className="rounded-xl border border-white/10 p-4">
            <h3 className="text-sm font-semibold text-purple-300">Time-locked Withdrawals</h3>
            <p className="mt-2 text-xs text-slate-400">
              Large withdrawals (&gt;$100k) have mandatory 24h timelock enforced by Soroban.
              Board can expedite via multi-auth override.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
