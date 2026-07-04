import { fmtUsd } from "@/lib/api";

export function PageHeader({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-white">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

export function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: "brand" | "green" | "amber" | "blue";
}) {
  const ring =
    accent === "green"
      ? "ring-emerald-500/30"
      : accent === "amber"
        ? "ring-amber-500/30"
        : accent === "blue"
          ? "ring-blue-500/30"
          : "ring-brand/30";
  return (
    <div className={`card ring-1 ${ring}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="mt-1 text-xs text-slate-400">{sub}</div>}
    </div>
  );
}

const CHAIN_COLORS: Record<string, string> = {
  base: "bg-blue-500",
  ethereum: "bg-indigo-400",
  arbitrum: "bg-sky-500",
  optimism: "bg-rose-500",
  polygon: "bg-violet-500",
  solana: "bg-emerald-400",
  "off-ramp": "bg-amber-500",
};

export function AllocationBar({ data }: { data: Record<string, number> }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-white/5">
        {entries.map(([k, v]) => (
          <div
            key={k}
            className={`${CHAIN_COLORS[k] || "bg-slate-500"} h-full`}
            style={{ width: `${(v / total) * 100}%` }}
            title={`${k}: ${fmtUsd(v)}`}
          />
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs">
        {entries.map(([k, v]) => (
          <span key={k} className="flex items-center gap-1.5 text-slate-300">
            <span className={`h-2 w-2 rounded-full ${CHAIN_COLORS[k] || "bg-slate-500"}`} />
            {k} · {fmtUsd(v)}
          </span>
        ))}
      </div>
    </div>
  );
}

const STATUS_STYLES: Record<string, string> = {
  executed: "bg-emerald-500/15 text-emerald-300",
  planned: "bg-sky-500/15 text-sky-300",
  proposed: "bg-indigo-500/15 text-indigo-300",
  awaiting_signatures: "bg-amber-500/15 text-amber-300",
  blocked_compliance: "bg-rose-500/15 text-rose-300",
  cleared: "bg-emerald-500/15 text-emerald-300",
  pending: "bg-slate-500/15 text-slate-300",
  flagged: "bg-rose-500/15 text-rose-300",
  opportunity: "bg-emerald-500/15 text-emerald-300",
  risk: "bg-amber-500/15 text-amber-300",
  critical: "bg-rose-500/15 text-rose-300",
};

export function StatusPill({ value }: { value: string }) {
  const style = STATUS_STYLES[value] || "bg-slate-500/15 text-slate-300";
  return <span className={`pill ${style}`}>{value.replace(/_/g, " ")}</span>;
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-sm text-slate-400">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-brand" />
      {label || "Loading…"}
    </div>
  );
}
