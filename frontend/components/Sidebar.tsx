"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Dashboard", icon: "◎" },
  { href: "/agent", label: "CFO Agent", icon: "✦" },
  { href: "/payroll", label: "Payroll & Payouts", icon: "⇄" },
  { href: "/stellar", label: "Stellar & RWA", icon: "✧" },
  { href: "/ledger", label: "Ledger & Reports", icon: "▤" },
  { href: "/billing", label: "Billing & Revenue", icon: "◇" },
  { href: "/settings", label: "Settings & Admin", icon: "⚙" },
];

export function Sidebar() {
  const path = usePathname();
  return (
    <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-white/10 bg-black/30 p-5 md:flex">
      <div className="mb-8 flex items-center gap-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand text-lg font-bold text-white">
          M
        </div>
        <div>
          <div className="text-lg font-semibold leading-none">Mandate</div>
          <div className="text-[11px] text-slate-400">Autonomous CFO</div>
        </div>
      </div>

      <nav className="flex flex-col gap-1">
        {NAV.map((item) => {
          const active = path === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                active
                  ? "bg-brand/20 text-white ring-1 ring-brand/40"
                  : "text-slate-300 hover:bg-white/5 hover:text-white"
              }`}
            >
              <span className="w-4 text-center text-slate-400">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto rounded-xl border border-white/10 bg-white/[0.02] p-3 text-xs text-slate-400">
        <div className="font-medium text-slate-200">Helios Labs DAO</div>
        <div>Demo organization · sandbox mode</div>
      </div>
    </aside>
  );
}
