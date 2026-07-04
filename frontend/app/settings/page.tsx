"use client";

import { useEffect, useState } from "react";
import {
  api,
  type AuditEntry,
  type Readiness,
  type WebhookDelivery,
} from "@/lib/api";
import { PageHeader, Spinner, StatusPill } from "@/components/ui";

const ROLES = [
  { role: "Owner", perms: "Full access incl. billing & destructive actions" },
  { role: "Admin", perms: "Treasury, payroll, agent, ledger, reports, invites" },
  { role: "Member", perms: "Read + propose payroll, run agent, export reports" },
  { role: "Viewer", perms: "Read-only across treasury, payroll, ledger" },
  { role: "Agent", perms: "Autonomous service role bounded by on-chain policy" },
];

function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString();
}

export default function SettingsPage() {
  const [ready, setReady] = useState<Readiness | null>(null);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [hooks, setHooks] = useState<WebhookDelivery[]>([]);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");

  async function refresh() {
    const [a, w] = await Promise.all([api.audit(25), api.webhookDeliveries(15)]);
    setAudit(a);
    setHooks(w);
  }

  useEffect(() => {
    api.readiness().then(setReady).catch(() => {});
    refresh().catch(() => {});
  }, []);

  async function sendTest() {
    setBusy(true);
    setToast("");
    try {
      await api.testWebhook();
      await refresh();
      setToast("Test notification emitted to the outbox.");
    } catch (e) {
      setToast(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Settings & Admin"
        subtitle="Multi-tenant controls: system health, RBAC, immutable audit trail, and event notifications — the operational surface an acquirer audits."
      >
        <button className="btn-ghost" disabled={busy} onClick={sendTest}>
          {busy ? "Sending…" : "Send test notification"}
        </button>
      </PageHeader>

      {toast && (
        <div className="mb-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-200">
          {toast}
        </div>
      )}

      {/* System status */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="card">
          <h2 className="mb-3 text-sm font-semibold text-white">System status</h2>
          {!ready ? (
            <Spinner label="Probing /readyz…" />
          ) : (
            <div className="space-y-2 text-sm">
              <Row k="Readiness" v={ready.ready ? "ready" : "degraded"} good={ready.ready} />
              <Row k="Version" v={ready.version} />
              <Row k="Environment" v={ready.environment} />
              <Row k="Integration mode" v={ready.integration_mode} />
              {Object.entries(ready.checks).map(([k, v]) => (
                <Row key={k} k={`Check · ${k}`} v={v} good={v === "ok"} />
              ))}
            </div>
          )}
        </div>

        <div className="card lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold text-white">Roles & permissions (RBAC)</h2>
          <table className="w-full">
            <thead>
              <tr>
                <th className="th">Role</th>
                <th className="th">Permissions</th>
              </tr>
            </thead>
            <tbody>
              {ROLES.map((r) => (
                <tr key={r.role} className="border-t border-white/5">
                  <td className="td font-medium text-white">{r.role}</td>
                  <td className="td text-slate-300">{r.perms}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Audit log */}
      <div className="mt-6 card">
        <h2 className="mb-3 text-sm font-semibold text-white">Audit trail</h2>
        {audit.length === 0 ? (
          <p className="text-sm text-slate-500">No activity yet. Run the agent or a payroll batch.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="th">When</th>
                  <th className="th">Actor</th>
                  <th className="th">Action</th>
                  <th className="th">Resource</th>
                </tr>
              </thead>
              <tbody>
                {audit.map((e) => (
                  <tr key={e.id} className="border-t border-white/5">
                    <td className="td text-slate-400">{timeAgo(e.created_at)}</td>
                    <td className="td">{e.actor}</td>
                    <td className="td">
                      <StatusPill value={e.action.replace(/\./g, "_")} />
                    </td>
                    <td className="td font-mono text-xs text-slate-400">{e.resource || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Webhook deliveries */}
      <div className="mt-6 card">
        <h2 className="mb-1 text-sm font-semibold text-white">Event notifications (Slack / Telegram)</h2>
        <p className="mb-3 text-xs text-slate-400">
          Deliveries are persisted to a durable outbox. Configure <code>MANDATE_SLACK_WEBHOOK_URL</code> to send live.
        </p>
        {hooks.length === 0 ? (
          <p className="text-sm text-slate-500">No deliveries yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="th">When</th>
                  <th className="th">Event</th>
                  <th className="th">Channel</th>
                  <th className="th">Status</th>
                </tr>
              </thead>
              <tbody>
                {hooks.map((h) => (
                  <tr key={h.id} className="border-t border-white/5">
                    <td className="td text-slate-400">{timeAgo(h.created_at)}</td>
                    <td className="td">{h.event}</td>
                    <td className="td">{h.channel}</td>
                    <td className="td">
                      <StatusPill value={h.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ k, v, good }: { k: string; v: string; good?: boolean }) {
  return (
    <div className="flex items-center justify-between border-b border-white/5 pb-2 last:border-0">
      <span className="text-slate-400">{k}</span>
      <span className={good === undefined ? "text-slate-200" : good ? "text-emerald-300" : "text-rose-300"}>
        {v}
      </span>
    </div>
  );
}
