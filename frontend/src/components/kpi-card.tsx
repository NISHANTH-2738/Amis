import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Kpi } from "@/types/fabriguard";

export function KpiCard({ kpi, large = false }: { kpi: Kpi; large?: boolean }) {
  const danger = kpi.severity === "critical";
  const warn = kpi.severity === "warning";
  return (
    <div className={cn("industrial-panel rounded-md p-4", large && "p-5")}>
      <div className="flex items-start justify-between gap-3">
        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">{kpi.label}</div>
        {danger || warn ? <ArrowUpRight className={cn("h-4 w-4", danger ? "text-red-300" : "text-amber-300")} /> : <ArrowDownRight className="h-4 w-4 text-emerald-300" />}
      </div>
      <div className={cn("mt-3 font-mono font-semibold tracking-tight text-slate-50", large ? "text-4xl" : "text-3xl")}>{kpi.value}</div>
      <div className="mt-2 flex items-center justify-between gap-3 text-xs">
        <span className={cn(danger ? "text-red-300" : warn ? "text-amber-200" : "text-emerald-200")}>{kpi.trend}</span>
        <span className="truncate text-slate-500">{kpi.helper}</span>
      </div>
    </div>
  );
}
