import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Kpi } from "@/types/fabriguard";

export function KpiCard({ kpi, large = false }: { kpi: Kpi; large?: boolean }) {
  const danger = kpi.severity === "critical";
  const warn = kpi.severity === "warning";
  return (
    <div className={cn("industrial-panel min-w-0 rounded-md p-3 xl:p-4", large && "xl:p-5")}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 text-[10px] font-semibold uppercase text-slate-500 xl:text-[11px]">{kpi.label}</div>
        {danger || warn ? <ArrowUpRight className={cn("h-3.5 w-3.5 shrink-0 xl:h-4 xl:w-4", danger ? "text-red-300" : "text-amber-300")} /> : <ArrowDownRight className="h-3.5 w-3.5 shrink-0 text-emerald-300 xl:h-4 xl:w-4" />}
      </div>
      <div className={cn("mt-3 font-mono font-semibold tracking-tight text-slate-50", large ? "text-2xl xl:text-4xl" : "text-2xl xl:text-3xl")}>{kpi.value}</div>
      <div className="mt-2 flex items-center justify-between gap-2 text-[11px] xl:text-xs">
        <span className={cn(danger ? "text-red-300" : warn ? "text-amber-200" : "text-emerald-200")}>{kpi.trend}</span>
        <span className="hidden truncate text-slate-500 2xl:block">{kpi.helper}</span>
      </div>
    </div>
  );
}
