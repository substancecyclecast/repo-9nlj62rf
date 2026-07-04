"use client";

import { useEffect, useState } from "react";
import { api, type AgentRun } from "@/lib/api";
import { PageHeader, Spinner } from "@/components/ui";

const SUGGESTIONS = [
  "Give me a full treasury overview and recommend actions",
  "Deploy $250,000 idle USDC into the highest-yield venue",
  "Rebalance $100k of volatile assets into USDC",
  "Categorize all uncategorized transactions for the books",
];

export default function AgentPage() {
  const [goal, setGoal] = useState("");
  const [run, setRun] = useState<AgentRun | null>(null);
  const [history, setHistory] = useState<AgentRun[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const loadHistory = () => api.agentRuns().then(setHistory).catch(() => {});
  useEffect(() => {
    loadHistory();
  }, []);

  async function submit(g?: string) {
    const text = (g ?? goal).trim();
    if (!text) return;
    setBusy(true);
    setError("");
    setRun(null);
    try {
      const result = await api.runAgent(text);
      setRun(result);
      setGoal("");
      loadHistory();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Autonomous CFO Agent"
        subtitle="Describe a treasury goal in plain English. The agent plans tool calls, executes them under policy, and logs an auditable trace."
      />

      <div className="card">
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            placeholder="e.g. Review the treasury and deploy idle cash to yield"
            className="flex-1 rounded-lg border border-white/15 bg-black/30 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-brand focus:outline-none"
          />
          <button className="btn-primary" disabled={busy} onClick={() => submit()}>
            {busy ? "Running…" : "Run agent"}
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => submit(s)}
              disabled={busy}
              className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs text-slate-300 hover:bg-white/10"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="card mt-4 text-sm text-rose-300">
          <pre className="whitespace-pre-wrap text-xs">{error}</pre>
        </div>
      )}
      {busy && (
        <div className="mt-4">
          <Spinner label="Agent is planning and executing…" />
        </div>
      )}

      {run && (
        <div className="card mt-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">
              Run #{run.id} · <span className="text-slate-400">{run.goal}</span>
            </h2>
            <span className="pill bg-emerald-500/15 text-emerald-300">
              {run.status} · {run.provider}
            </span>
          </div>
          <ol className="relative space-y-3 border-l border-white/10 pl-5">
            {run.steps.map((s, i) => (
              <li key={i} className="relative">
                <span
                  className={`absolute -left-[26px] top-1 h-3 w-3 rounded-full ${
                    s.kind === "tool" ? "bg-brand" : "bg-slate-500"
                  }`}
                />
                {s.kind === "tool" ? (
                  <div>
                    <div className="font-mono text-xs text-brand">{s.tool}()</div>
                    <div className="text-sm text-slate-200">{s.message}</div>
                  </div>
                ) : (
                  <div className="text-xs italic text-slate-400">{s.message}</div>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}

      {history.length > 0 && (
        <div className="card mt-6">
          <h2 className="mb-3 text-sm font-semibold text-white">Recent runs</h2>
          <div className="space-y-2">
            {history.slice(0, 8).map((r) => (
              <button
                key={r.id}
                onClick={() => setRun(r)}
                className="flex w-full items-center justify-between rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2 text-left text-sm hover:bg-white/5"
              >
                <span className="truncate text-slate-200">
                  #{r.id} · {r.goal}
                </span>
                <span className="ml-3 shrink-0 text-xs text-slate-500">
                  {r.steps.filter((s) => s.kind === "tool").length} tools
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
