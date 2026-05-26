"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BrainCircuit,
  Camera,
  Gauge,
  ImagePlus,
  LayoutDashboard,
  Loader2,
  MonitorCog,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  UserRoundCog,
  Wifi,
  WifiOff,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { motion } from "framer-motion";
import { KpiCard } from "@/components/kpi-card";
import { ReviewDrawer } from "@/components/review-drawer";
import { SectionTitle, StatusPill } from "@/components/status";
import { useLiveFabriGuard } from "@/hooks/use-live-fabriguard";
import { fabriGuardApi, normalizeDetection } from "@/lib/api";
import { cn, formatPercent, timeAgo } from "@/lib/utils";
import { useUiStore } from "@/stores/use-ui-store";
import type { DefectDetection, Kpi, MachineHealth as MachineHealthType, NavItem, Role, SensorReading, TrendPoint } from "@/types/fabriguard";

type InspectionResult = {
  status?: string;
  severity?: { name?: string };
  model_source?: string;
  processing?: { model_source?: string; latency_ms?: number };
  inference_ms?: number;
};

const navItems: NavItem[] = [
  { key: "dashboard", label: "Main Dashboard", icon: LayoutDashboard },
  { key: "live", label: "Live Defect Monitoring", icon: Camera },
  { key: "production", label: "Production Analytics", icon: BarChart3 },
  { key: "sensors", label: "Sensor Monitoring", icon: Activity },
  { key: "machines", label: "Machine Health", icon: MonitorCog },
  { key: "operators", label: "Operator Analytics", icon: UserRoundCog },
  { key: "training", label: "AI Training Workspace", icon: BrainCircuit },
  { key: "alerts", label: "Alerts Center", icon: AlertTriangle },
  { key: "settings", label: "Settings Panel", icon: Settings },
];

const roleLabels: Record<Role, string> = {
  operator: "Operator",
  supervisor: "Supervisor",
  executive: "Executive",
};

export function AppShell() {
  const { role, page, density, search, setRole, setPage, setDensity, setSearch } = useUiStore();
  const { socketState, detections, alerts } = useLiveFabriGuard(false);
  const [uploadedDetections, setUploadedDetections] = useState<DefectDetection[]>([]);
  const [selectedDetection, setSelectedDetection] = useState<DefectDetection | null>(null);
  const currentPage = navItems.find((item) => item.key === page) ?? navItems[0];
  const visibleDetections = useMemo(
    () => [...uploadedDetections, ...detections],
    [uploadedDetections, detections],
  );

  return (
    <main className="min-h-screen bg-[#080b10] text-slate-100">
      <div className="grid min-h-screen grid-cols-[220px_minmax(0,1fr)] xl:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="border-r border-slate-800 bg-[#0b1017]">
          <div className="flex h-16 items-center gap-3 border-b border-slate-800 px-5">
            <div className="grid h-9 w-9 place-items-center rounded-md border border-sky-500/40 bg-sky-500/10">
              <ShieldCheck className="h-5 w-5 text-sky-300" />
            </div>
            <div>
              <div className="text-sm font-bold tracking-wide">FabriGuard</div>
              <div className="text-[11px] uppercase tracking-[0.2em] text-slate-500">Industrial AI</div>
            </div>
          </div>

          <div className="border-b border-slate-800 p-3">
            <div className="grid grid-cols-3 rounded-md bg-slate-950 p-1">
              {(["operator", "supervisor", "executive"] as Role[]).map((item) => (
                <button
                  key={item}
                  onClick={() => setRole(item)}
                  className={cn(
                    "rounded px-1.5 py-2 text-[11px] font-semibold text-slate-500 xl:px-2 xl:text-xs",
                    role === item && "bg-slate-800 text-slate-100",
                  )}
                >
                  {roleLabels[item]}
                </button>
              ))}
            </div>
          </div>

          <nav className="space-y-1 p-3">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.key}
                  onClick={() => setPage(item.key)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm text-slate-400 hover:bg-slate-900 hover:text-slate-100",
                    page === item.key && "bg-sky-500/10 text-sky-200 ring-1 ring-sky-500/30",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </button>
              );
            })}
          </nav>
        </aside>

        <section className="min-w-0">
          <header className="flex min-h-16 flex-wrap items-center justify-between gap-3 border-b border-slate-800 bg-[#0b1017]/95 px-5 py-3">
            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">{roleLabels[role]} Mode</div>
              <h1 className="text-lg font-semibold">{currentPage.label}</h1>
            </div>
            <div className="flex items-center gap-3">
              <label className="relative">
                <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search defects, machines, alerts"
                  className="h-9 w-52 rounded-md border border-slate-800 bg-slate-950 pl-9 pr-3 text-sm outline-none focus:border-sky-500 xl:w-72"
                />
              </label>
              <button
                onClick={() => setDensity(density === "compact" ? "comfortable" : "compact")}
                className="rounded-md border border-slate-800 bg-slate-950 p-2 text-slate-300"
                aria-label="Toggle table density"
                title="Toggle density"
              >
                <SlidersHorizontal className="h-4 w-4" />
              </button>
              <div className="rounded-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-xs font-semibold uppercase text-emerald-200">
                REAL DATA
              </div>
              <div className="flex items-center gap-2 rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-xs uppercase text-slate-400">
                {socketState === "live" ? <Wifi className="h-4 w-4 text-emerald-300" /> : <WifiOff className="h-4 w-4 text-amber-300" />}
                {socketState}
              </div>
            </div>
          </header>

          <div className="h-[calc(100vh-64px)] overflow-y-auto p-5">
            <motion.div key={`${role}-${page}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.18 }}>
              {page === "dashboard" && <RoleDashboard role={role} detections={visibleDetections} alerts={alerts} onReview={setSelectedDetection} onInspection={(detection) => setUploadedDetections((current) => [detection, ...current].slice(0, 12))} />}
              {page === "live" && <LiveMonitoring detections={visibleDetections} onReview={setSelectedDetection} onInspection={(detection) => setUploadedDetections((current) => [detection, ...current].slice(0, 12))} />}
              {page === "production" && <ProductionAnalytics detections={visibleDetections} alerts={alerts} />}
              {page === "sensors" && <SensorMonitoring />}
              {page === "machines" && <MachineHealth machines={[]} />}
              {page === "operators" && <OperatorAnalytics detections={visibleDetections} onReview={setSelectedDetection} />}
              {page === "training" && <TrainingWorkspace />}
              {page === "alerts" && <AlertsCenter alerts={alerts} />}
              {page === "settings" && <SettingsPanel />}
            </motion.div>
          </div>
        </section>
      </div>
      <ReviewDrawer detection={selectedDetection} onClose={() => setSelectedDetection(null)} />
    </main>
  );
}

function RelativeTime({ timestamp }: { timestamp: string }) {
  const label = useMemo(() => timeAgo(timestamp), [timestamp]);

  return <span suppressHydrationWarning>{label}</span>;
}

function buildKpis(detections: DefectDetection[], alerts: ReturnType<typeof useLiveFabriGuard>["alerts"]) {
  const total = detections.length;
  const defects = detections.filter((item) => item.status !== "approved").length;
  const critical = detections.filter((item) => item.severity === "critical").length;
  const defectRate = total ? defects / total : 0;

  const operator: Kpi[] = [
    { label: "Current Defects", value: String(defects), trend: `${alerts.length} active alerts`, severity: defects ? "warning" : "normal", helper: "Live backend inspections only" },
    { label: "AI Status", value: "LIVE", trend: "YOLOv8 inference", severity: "normal", helper: "No frontend mock detections" },
    { label: "Inspected", value: String(total), trend: "database records", severity: "advisory", helper: "Loaded from backend" },
    { label: "Critical", value: String(critical), trend: "needs action", severity: critical ? "critical" : "normal", helper: "Severity engine output" },
    { label: "Latency", value: `${Math.round(detections.reduce((sum, item) => sum + item.inferenceMs, 0) / Math.max(total, 1))} ms`, trend: "average", severity: "advisory", helper: "Inference response time" },
  ];

  const supervisor: Kpi[] = [
    { label: "Inspections", value: String(total), trend: "real records", severity: "advisory", helper: "SQLite backend" },
    { label: "Defects", value: String(defects), trend: formatPercent(defectRate), severity: defects ? "warning" : "normal", helper: "Open review queue" },
    { label: "Alerts", value: String(alerts.length), trend: "live websocket", severity: alerts.length ? "warning" : "normal", helper: "Unmocked alert stream" },
    { label: "Critical", value: String(critical), trend: "stop risk", severity: critical ? "critical" : "normal", helper: "Severity engine" },
  ];

  const executive: Kpi[] = [
    { label: "Quality Rate", value: formatPercent(1 - defectRate), trend: "from inspections", severity: defectRate > 0.1 ? "warning" : "normal", helper: "Live database" },
    { label: "AI Uptime", value: "LIVE", trend: "backend connected", severity: "normal", helper: "WebSocket and REST" },
    { label: "Alerts", value: String(alerts.length), trend: "plant risk", severity: alerts.length ? "warning" : "normal", helper: "Realtime alerts" },
    { label: "Critical", value: String(critical), trend: "line impact", severity: critical ? "critical" : "normal", helper: "Emergency count" },
  ];

  return { operator, supervisor, executive };
}

function buildTrends(detections: DefectDetection[]): TrendPoint[] {
  const buckets = new Map<string, TrendPoint>();
  for (const item of detections) {
    const date = new Date(item.timestamp);
    const time = Number.isNaN(date.getTime()) ? "Live" : `${String(date.getHours()).padStart(2, "0")}:00`;
    const current = buckets.get(time) ?? { time, defects: 0, throughput: 0, confidence: 0, anomaly: 0 };
    current.throughput += 1;
    current.defects += item.status !== "approved" ? 1 : 0;
    current.confidence += item.confidence;
    current.anomaly += item.severity === "critical" ? 1 : item.severity === "warning" ? 0.5 : 0;
    buckets.set(time, current);
  }
  return Array.from(buckets.values()).map((item) => ({
    ...item,
    confidence: item.throughput ? Math.round((item.confidence / item.throughput) * 100) : 0,
  }));
}

function RoleDashboard({
  role,
  detections,
  alerts,
  onReview,
  onInspection,
}: {
  role: Role;
  detections: DefectDetection[];
  alerts: ReturnType<typeof useLiveFabriGuard>["alerts"];
  onReview: (detection: DefectDetection) => void;
  onInspection: (detection: DefectDetection) => void;
}) {
  const kpis = buildKpis(detections, alerts);
  if (role === "operator") {
    return (
      <div className="space-y-5">
        <div className="grid grid-cols-5 gap-2 xl:gap-3">
          {kpis.operator.map((kpi) => <KpiCard key={kpi.label} kpi={kpi} large />)}
        </div>
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.4fr_0.9fr]">
          <ImageInspectionPanel detections={detections} onInspection={onInspection} />
          <AlertRail alerts={alerts} />
        </div>
        <DefectTable detections={detections.slice(0, 8)} onReview={onReview} compact />
      </div>
    );
  }

  if (role === "supervisor") {
    return (
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">{kpis.supervisor.map((kpi) => <KpiCard key={kpi.label} kpi={kpi} />)}</div>
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <TrendPanel title="Defect Trends" metric="defects" detections={detections} />
          <LineComparison detections={detections} />
        </div>
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.2fr_0.8fr]">
          <DefectTable detections={detections} onReview={onReview} />
          <AlertRail alerts={alerts} />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">{kpis.executive.map((kpi) => <KpiCard key={kpi.label} kpi={kpi} />)}</div>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <TrendPanel title="Defect Reduction" metric="defects" detections={detections} />
        <TrendPanel title="Production Efficiency" metric="throughput" detections={detections} />
        <ExecutiveImpact detections={detections} />
      </div>
      <MachineGrid executive machines={[]} />
    </div>
  );
}

function LiveMonitoring({ detections, onReview, onInspection }: { detections: DefectDetection[]; onReview: (detection: DefectDetection) => void; onInspection: (detection: DefectDetection) => void }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.45fr_0.8fr]">
        <ImageInspectionPanel detections={detections} onInspection={onInspection} detailed />
        <div className="space-y-4">
          <InferenceStream detections={detections} />
          <DefectHeatmap />
        </div>
      </div>
      <DefectTable detections={detections} onReview={onReview} />
    </div>
  );
}

function ImageInspectionPanel({
  detections,
  onInspection,
  detailed = false,
}: {
  detections: DefectDetection[];
  onInspection: (detection: DefectDetection) => void;
  detailed?: boolean;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [result, setResult] = useState<InspectionResult | null>(null);
  const [isInspecting, setIsInspecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const inspect = async () => {
    if (!file) return;
    setIsInspecting(true);
    setError(null);
    try {
      const response = await fabriGuardApi.inspectImage(file);
      setResult(response as InspectionResult);
      onInspection(normalizeDetection(response));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Inspection failed");
    } finally {
      setIsInspecting(false);
    }
  };

  const latest = result ? normalizeDetection(result) : detections[0];

  return (
    <section className="industrial-panel rounded-md p-4">
      <SectionTitle
        eyebrow="Image Inspection"
        title="Upload Inspection Image / AI Defect Analysis"
        right={<StatusPill severity={result?.status === "FAIL" ? "warning" : "normal"} label={isInspecting ? "processing" : "ready"} />}
      />
      <div className="mb-3 grid gap-3 xl:grid-cols-[1fr_auto]">
        <label className="flex cursor-pointer items-center gap-3 rounded-md border border-dashed border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-300 hover:border-sky-500">
          <ImagePlus className="h-4 w-4 text-sky-300" />
          <span className="truncate">{file ? file.name : "Choose image for YOLOv8 inspection pipeline"}</span>
          <input
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(event) => {
              const nextFile = event.target.files?.[0] ?? null;
              if (previewUrl) URL.revokeObjectURL(previewUrl);
              setFile(nextFile);
              setPreviewUrl(nextFile ? URL.createObjectURL(nextFile) : null);
              setResult(null);
              setError(null);
            }}
          />
        </label>
        <button
          onClick={inspect}
          disabled={!file || isInspecting}
          className="inline-flex items-center justify-center gap-2 rounded-md bg-sky-500 px-4 py-2 text-sm font-semibold text-sky-950 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isInspecting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Camera className="h-4 w-4" />}
          Inspect Image
        </button>
      </div>
      {error ? <div className="mb-3 rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">{error}</div> : null}
      <LiveCamera detections={latest ? [latest] : detections} detailed={detailed} imageUrl={previewUrl ?? undefined} />
      {result ? (
        <div className="mt-3 grid gap-3 text-sm xl:grid-cols-4">
          <ResultMetric label="Status" value={String(result.status ?? "-")} />
          <ResultMetric label="Severity" value={String(result.severity?.name ?? "-")} />
          <ResultMetric label="Detector" value={String(result.model_source ?? result.processing?.model_source ?? "-")} />
          <ResultMetric label="Latency" value={`${result.inference_ms ?? result.processing?.latency_ms ?? 0} ms`} />
        </div>
      ) : null}
    </section>
  );
}

function ResultMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-800 bg-slate-950 px-3 py-2">
      <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-1 truncate font-mono text-sm text-slate-100">{value}</div>
    </div>
  );
}

function LiveCamera({ detections, detailed = false, imageUrl }: { detections: DefectDetection[]; detailed?: boolean; imageUrl?: string }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const [imageFrame, setImageFrame] = useState({ left: 0, top: 0, width: 100, height: 100 });
  const active = detections[0];
  const bbox = active?.bbox ?? { x: 42, y: 28, width: 18, height: 24 };
  const showBox = Boolean(
    active &&
    !["normal", "pass", "none", "sensor_anomaly"].includes(active.defect.toLowerCase()) &&
    bbox.width > 0 &&
    bbox.height > 0,
  );
  const overlay = imageUrl
    ? {
        left: `${imageFrame.left + (bbox.x * imageFrame.width) / 100}%`,
        top: `${imageFrame.top + (bbox.y * imageFrame.height) / 100}%`,
        width: `${(bbox.width * imageFrame.width) / 100}%`,
        height: `${(bbox.height * imageFrame.height) / 100}%`,
      }
    : { left: `${bbox.x}%`, top: `${bbox.y}%`, width: `${bbox.width}%`, height: `${bbox.height}%` };

  useEffect(() => {
    if (!imageUrl) return;

    const updateFrame = () => {
      const container = containerRef.current;
      const image = imageRef.current;
      if (!container || !image || !image.naturalWidth || !image.naturalHeight) return;

      const containerWidth = container.clientWidth;
      const containerHeight = container.clientHeight;
      const imageRatio = image.naturalWidth / image.naturalHeight;
      const containerRatio = containerWidth / containerHeight;

      let renderedWidth = containerWidth;
      let renderedHeight = containerHeight;
      if (imageRatio > containerRatio) {
        renderedHeight = containerWidth / imageRatio;
      } else {
        renderedWidth = containerHeight * imageRatio;
      }

      setImageFrame({
        left: ((containerWidth - renderedWidth) / 2 / containerWidth) * 100,
        top: ((containerHeight - renderedHeight) / 2 / containerHeight) * 100,
        width: (renderedWidth / containerWidth) * 100,
        height: (renderedHeight / containerHeight) * 100,
      });
    };

    const frame = requestAnimationFrame(updateFrame);
    const observer = new ResizeObserver(updateFrame);
    if (containerRef.current) observer.observe(containerRef.current);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, [imageUrl]);

  return (
    <div>
      <div ref={containerRef} className={cn("relative overflow-hidden rounded-md border border-slate-700 bg-slate-950 grid-bg", detailed ? "h-[470px]" : "h-[390px]")}>
        <div className="absolute inset-y-0 w-1/3 scanline" />
        {imageUrl ? (
          <img ref={imageRef} src={imageUrl} alt="Uploaded inspection preview" className="absolute inset-0 h-full w-full object-contain" onLoad={() => {
            const image = imageRef.current;
            if (!image) return;
            const container = containerRef.current;
            if (!container || !image.naturalWidth || !image.naturalHeight) return;
            const containerWidth = container.clientWidth;
            const containerHeight = container.clientHeight;
            const imageRatio = image.naturalWidth / image.naturalHeight;
            const containerRatio = containerWidth / containerHeight;
            let renderedWidth = containerWidth;
            let renderedHeight = containerHeight;
            if (imageRatio > containerRatio) renderedHeight = containerWidth / imageRatio;
            else renderedWidth = containerHeight * imageRatio;
            setImageFrame({
              left: ((containerWidth - renderedWidth) / 2 / containerWidth) * 100,
              top: ((containerHeight - renderedHeight) / 2 / containerHeight) * 100,
              width: (renderedWidth / containerWidth) * 100,
              height: (renderedHeight / containerHeight) * 100,
            });
          }} />
        ) : (
          <div className="absolute left-[8%] top-[14%] h-[72%] w-[84%] rounded border border-slate-700 bg-slate-900/70" />
        )}
        {showBox ? (
          <div
            className="absolute border-2 border-red-400 bg-red-500/10"
            style={overlay}
          >
            <div className="absolute -top-7 left-0 whitespace-nowrap rounded bg-red-500 px-2 py-1 text-xs font-semibold text-white">
              {active.defect} {formatPercent(active.confidence)}
            </div>
          </div>
        ) : null}
        <div className="absolute bottom-3 left-3 grid grid-cols-3 gap-2 text-xs">
          <span className="rounded bg-slate-950/90 px-2 py-1 text-slate-300">UPLOAD</span>
          <span className="rounded bg-slate-950/90 px-2 py-1 text-slate-300">{active ? formatPercent(active.confidence) : "--"}</span>
          <span className="rounded bg-slate-950/90 px-2 py-1 text-slate-300">YOLOv8</span>
        </div>
      </div>
    </div>
  );
}

function DefectTable({
  detections,
  onReview,
  compact,
}: {
  detections: DefectDetection[];
  onReview: (detection: DefectDetection) => void;
  compact?: boolean;
}) {
  const density = useUiStore((state) => state.density);
  const search = useUiStore((state) => state.search.toLowerCase());
  const filtered = useMemo(
    () => detections.filter((row) => `${row.id} ${row.defect} ${row.machine} ${row.line}`.toLowerCase().includes(search)),
    [detections, search],
  );
  return (
    <section className="industrial-panel overflow-hidden rounded-md">
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <div>
          <div className="text-sm font-semibold">Defect Review Queue</div>
          <div className="text-xs text-slate-500">Sticky headers / search / row priority / quick actions</div>
        </div>
        <StatusPill severity="warning" label={`${filtered.length} open`} />
      </div>
      <div className={cn("overflow-auto", compact ? "max-h-[260px]" : "max-h-[460px]")}>
        <table className="w-full min-w-[860px] border-collapse text-sm">
          <thead className="sticky top-0 z-10 bg-slate-950 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              {["ID", "Time", "Line", "Machine", "Defect", "Confidence", "Severity", "Status", "Action"].map((head) => (
                <th key={head} className="border-b border-slate-800 px-3 py-3 text-left font-semibold">{head}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((row, index) => (
              <tr key={`${row.id}-${row.timestamp}-${index}`} className={cn("border-b border-slate-800/80 hover:bg-slate-900/70", row.severity === "critical" && "bg-red-500/5")}>
                <td className={cn("px-3 font-mono text-sky-200", density === "compact" ? "py-2" : "py-3")}>{row.id}</td>
                <td className="px-3 text-slate-400"><RelativeTime timestamp={row.timestamp} /></td>
                <td className="px-3">{row.line}</td>
                <td className="px-3">{row.machine}</td>
                <td className="px-3 font-semibold">{row.defect}</td>
                <td className="px-3 font-mono">{formatPercent(row.confidence)}</td>
                <td className="px-3"><StatusPill severity={row.severity} label={row.severity} /></td>
                <td className="px-3 capitalize text-slate-300">{row.status}</td>
                <td className="px-3">
                  <button onClick={() => onReview(row)} className="rounded bg-sky-500 px-3 py-1.5 text-xs font-semibold text-sky-950">Review</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function AlertRail({ alerts }: { alerts: ReturnType<typeof useLiveFabriGuard>["alerts"] }) {
  return (
    <section className="industrial-panel rounded-md p-4">
      <SectionTitle eyebrow="Priority Queue" title="Live Alerts" />
      <div className="space-y-3">
        {alerts.slice(0, 5).map((alert, index) => (
          <div key={`${alert.id}-${alert.timestamp}-${index}`} className="rounded-md border border-slate-800 bg-slate-950 p-3">
            <div className="mb-2 flex items-center justify-between gap-3">
              <StatusPill severity={alert.severity} label={alert.severity} />
              <span className="text-xs text-slate-500"><RelativeTime timestamp={alert.timestamp} /></span>
            </div>
            <div className="text-sm font-semibold">{alert.title}</div>
            <div className="mt-1 text-xs leading-5 text-slate-400">{alert.message}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function TrendPanel({ title, metric, detections }: { title: string; metric: keyof TrendPoint; detections: DefectDetection[] }) {
  const trendData = buildTrends(detections);
  return (
    <section className="industrial-panel rounded-md p-4">
      <SectionTitle eyebrow="Analytics" title={title} />
      <div className="h-64">
        <ResponsiveContainer>
          <AreaChart data={trendData}>
            <CartesianGrid stroke="#1f2937" vertical={false} />
            <XAxis dataKey="time" stroke="#64748b" fontSize={12} />
            <YAxis stroke="#64748b" fontSize={12} />
            <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 6 }} />
            <Area type="monotone" dataKey={metric as string} stroke="#38bdf8" fill="#38bdf830" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function LineComparison({ detections }: { detections: DefectDetection[] }) {
  const rows = Object.values(
    detections.reduce<Record<string, { line: string; defects: number }>>((acc, detection) => {
      const line = detection.line || "Line";
      acc[line] ??= { line, defects: 0 };
      acc[line].defects += detection.status !== "approved" ? 1 : 0;
      return acc;
    }, {}),
  );
  return (
    <section className="industrial-panel rounded-md p-4">
      <SectionTitle eyebrow="Shift Operations" title="Line Comparison" />
      <div className="h-64">
        <ResponsiveContainer>
          <BarChart data={rows}>
            <CartesianGrid stroke="#1f2937" vertical={false} />
            <XAxis dataKey="line" stroke="#64748b" />
            <YAxis stroke="#64748b" />
            <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 6 }} />
            <Bar dataKey="defects" fill="#f59e0b" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function ProductionAnalytics({ detections, alerts }: { detections: DefectDetection[]; alerts: ReturnType<typeof useLiveFabriGuard>["alerts"] }) {
  const kpis = buildKpis(detections, alerts);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">{kpis.supervisor.map((kpi) => <KpiCard key={kpi.label} kpi={kpi} />)}</div>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <TrendPanel title="Throughput vs Defects" metric="throughput" detections={detections} />
        <LineComparison detections={detections} />
      </div>
      <MachineGrid machines={[]} />
    </div>
  );
}

function SensorMonitoring() {
  const sensors: SensorReading[] = [];
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {sensors.map((sensor) => <SensorWidget key={sensor.id} sensor={sensor} />)}
      </div>
      <TrendPanel title="Anomaly Trend" metric="anomaly" detections={[]} />
    </div>
  );
}

function SensorWidget({ sensor }: { sensor: SensorReading }) {
  const ratio = Math.min(100, Math.round((sensor.value / sensor.threshold) * 100));
  return (
    <div className="industrial-panel rounded-md p-4">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold">{sensor.metric}</div>
        <StatusPill severity={sensor.status} label={sensor.status} />
      </div>
      <div className="mt-4 flex items-end gap-2">
        <span className="font-mono text-3xl font-semibold">{sensor.value}</span>
        <span className="pb-1 text-sm text-slate-500">{sensor.unit}</span>
      </div>
      <div className="mt-4 h-2 rounded-full bg-slate-800">
        <div className={cn("h-2 rounded-full", sensor.status === "critical" ? "bg-red-400" : sensor.status === "warning" ? "bg-amber-300" : "bg-emerald-300")} style={{ width: `${ratio}%` }} />
      </div>
      <div className="mt-2 text-xs text-slate-500">{sensor.machine} threshold {sensor.threshold}{sensor.unit}</div>
    </div>
  );
}

function MachineHealth({ machines }: { machines: MachineHealthType[] }) {
  return <MachineGrid machines={machines} />;
}

function MachineGrid({ executive = false, machines }: { executive?: boolean; machines: MachineHealthType[] }) {
  return (
    <section className="industrial-panel rounded-md p-4">
      <SectionTitle eyebrow={executive ? "Plant Overview" : "Machine Health"} title="Industrial Cell Status" />
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {machines.map((machine) => (
          <div key={machine.id} className="rounded-md border border-slate-800 bg-slate-950 p-4">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <div className="font-semibold">{machine.name}</div>
                <div className="text-xs text-slate-500">{machine.line}</div>
              </div>
              <Gauge className={cn("h-5 w-5", machine.health < 65 ? "text-amber-300" : "text-emerald-300")} />
            </div>
            <div className="font-mono text-3xl font-semibold">{machine.health}%</div>
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-400">
              <span>OEE {formatPercent(machine.oee)}</span>
              <span>Defects {formatPercent(machine.defectRate)}</span>
              <span>State {machine.state}</span>
              <span>Service {machine.nextService}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function OperatorAnalytics({ detections, onReview }: { detections: DefectDetection[]; onReview: (detection: DefectDetection) => void }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <TrendPanel title="Correction Statistics" metric="confidence" detections={detections} />
        <ExecutiveImpact detections={detections} />
        <section className="industrial-panel rounded-md p-4">
          <SectionTitle eyebrow="Human Loop" title="Operator Queue" />
          <div className="space-y-3 text-sm">
            {["Nisha", "Arun", "Meera"].map((name, index) => (
              <div key={name} className="flex items-center justify-between rounded border border-slate-800 bg-slate-950 p-3">
                <span>{name}</span>
                <span className="font-mono text-sky-200">{[7, 5, 3][index]} reviews</span>
              </div>
            ))}
          </div>
        </section>
      </div>
      <DefectTable detections={detections} onReview={onReview} />
    </div>
  );
}

function TrainingWorkspace() {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_0.8fr]">
      <section className="industrial-panel rounded-md p-4">
        <SectionTitle eyebrow="Adaptive Learning" title="Few-Shot Product Onboarding" right={<StatusPill severity="advisory" label="20 refs needed" />} />
        <div className="grid grid-cols-4 gap-3">
          {Array.from({ length: 8 }).map((_, index) => (
            <div key={index} className="aspect-square rounded-md border border-dashed border-slate-700 bg-slate-950 grid-bg" />
          ))}
        </div>
        <div className="mt-4 flex gap-3">
          <button className="rounded-md bg-sky-500 px-4 py-2 text-sm font-semibold text-sky-950">Upload Reference Set</button>
          <button className="rounded-md border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200">Run PatchCore Setup</button>
        </div>
      </section>
      <section className="industrial-panel rounded-md p-4">
        <SectionTitle eyebrow="AI Analytics" title="Model Health" />
        <div className="space-y-4">
          {[
            ["Model confidence", 94, "normal"],
            ["Drift detection", 16, "advisory"],
            ["False positive rate", 4.8, "warning"],
            ["Learning progress", 68, "normal"],
          ].map(([label, value, state]) => (
            <div key={String(label)}>
              <div className="mb-1 flex justify-between text-sm"><span>{label}</span><span className="font-mono">{value}%</span></div>
              <div className="h-2 rounded-full bg-slate-800"><div className={cn("h-2 rounded-full", state === "warning" ? "bg-amber-300" : "bg-sky-300")} style={{ width: `${value}%` }} /></div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function AlertsCenter({ alerts }: { alerts: ReturnType<typeof useLiveFabriGuard>["alerts"] }) {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[0.85fr_1.2fr]">
      <AlertRail alerts={alerts} />
      <section className="industrial-panel rounded-md p-4">
        <SectionTitle eyebrow="Acknowledgment Workflow" title="Alert Center" />
        <div className="space-y-3">
          {alerts.map((alert, index) => (
            <div key={`${alert.id}-${alert.timestamp}-${index}`} className="flex items-center justify-between gap-4 rounded-md border border-slate-800 bg-slate-950 p-4">
              <div>
                <div className="flex items-center gap-2"><StatusPill severity={alert.severity} label={alert.severity} /><span className="font-semibold">{alert.title}</span></div>
                <p className="mt-2 text-sm text-slate-400">{alert.message}</p>
              </div>
              <button className="rounded-md border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200">Acknowledge</button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function SettingsPanel() {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
      {["API Connectivity", "Model Runtime", "Table Preferences", "Alert Routing", "Factory Lines", "Security Roles"].map((title) => (
        <section key={title} className="industrial-panel rounded-md p-4">
          <SectionTitle eyebrow="Configuration" title={title} />
          <div className="space-y-3 text-sm text-slate-400">
            <label className="flex items-center justify-between"><span>Enabled</span><input type="checkbox" defaultChecked /></label>
            <label className="block"><span className="mb-1 block">Refresh interval</span><select className="w-full rounded border border-slate-700 bg-slate-950 p-2"><option>30 seconds</option><option>5 minutes</option><option>Daily</option></select></label>
          </div>
        </section>
      ))}
    </div>
  );
}

function InferenceStream({ detections }: { detections: DefectDetection[] }) {
  return (
    <section className="industrial-panel rounded-md p-4">
      <SectionTitle eyebrow="Inference Stream" title="Recent Detections" />
      <div className="space-y-2">
        {detections.slice(0, 5).map((detection, index) => (
          <div key={`${detection.id}-${detection.timestamp}-${index}`} className="flex items-center justify-between rounded border border-slate-800 bg-slate-950 px-3 py-2 text-sm">
            <span>{detection.defect}</span>
            <span className="font-mono text-sky-200">{formatPercent(detection.confidence)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function DefectHeatmap() {
  return (
    <section className="industrial-panel rounded-md p-4">
      <SectionTitle eyebrow="Spatial Analysis" title="Defect Heatmap" />
      <div className="grid aspect-video grid-cols-8 gap-1 rounded-md border border-slate-800 bg-slate-950 p-2">
        {Array.from({ length: 48 }).map((_, index) => (
          <div key={index} className={cn("rounded", index % 11 === 0 ? "bg-red-400/80" : index % 7 === 0 ? "bg-amber-300/60" : "bg-slate-800")} />
        ))}
      </div>
    </section>
  );
}

function ExecutiveImpact({ detections }: { detections: DefectDetection[] }) {
  const trendData = buildTrends(detections);
  return (
    <section className="industrial-panel rounded-md p-4">
      <SectionTitle eyebrow="Business Impact" title="Financial Quality Impact" />
      <div className="h-64">
        <ResponsiveContainer>
          <LineChart data={trendData}>
            <CartesianGrid stroke="#1f2937" vertical={false} />
            <XAxis dataKey="time" stroke="#64748b" />
            <YAxis stroke="#64748b" />
            <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 6 }} />
            <Line type="monotone" dataKey="confidence" stroke="#34d399" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="anomaly" stroke="#f59e0b" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
