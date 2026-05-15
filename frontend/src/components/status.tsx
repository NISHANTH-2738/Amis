import { Activity, AlertTriangle, CheckCircle2, CircleAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Severity } from "@/types/fabriguard";

const severityMap = {
  critical: "border-red-500/50 bg-red-500/10 text-red-300",
  warning: "border-amber-500/50 bg-amber-500/10 text-amber-200",
  advisory: "border-sky-500/50 bg-sky-500/10 text-sky-200",
  normal: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200",
};

export function StatusPill({ severity, label }: { severity: Severity; label: string }) {
  const Icon = severity === "critical" ? CircleAlert : severity === "warning" ? AlertTriangle : severity === "normal" ? CheckCircle2 : Activity;
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-[11px] font-semibold uppercase tracking-wide", severityMap[severity])}>
      <Icon className="h-3.5 w-3.5" />
      {label}
    </span>
  );
}

export function SectionTitle({ eyebrow, title, right }: { eyebrow: string; title: string; right?: React.ReactNode }) {
  return (
    <div className="mb-3 flex items-end justify-between gap-3">
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{eyebrow}</div>
        <h2 className="mt-1 text-lg font-semibold text-slate-100">{title}</h2>
      </div>
      {right}
    </div>
  );
}
