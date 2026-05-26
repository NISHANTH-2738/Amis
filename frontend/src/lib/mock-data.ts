import type { AlertEvent, DefectDetection, Kpi, MachineHealth, SensorReading, TrendPoint } from "@/types/fabriguard";

export const operatorKpis: Kpi[] = [
  { label: "Current Defects", value: "7", trend: "+2 in 15m", severity: "warning", helper: "Line A2 active review" },
  { label: "AI Status", value: "LIVE", trend: "YOLOv8 96ms", severity: "normal", helper: "Model confidence stable" },
  { label: "Throughput", value: "1,284", trend: "pcs/hr", severity: "normal", helper: "Target 1,250 pcs/hr" },
  { label: "Stop Count", value: "2", trend: "last hour", severity: "critical", helper: "Both needle-line related" },
  { label: "Prod Health", value: "91%", trend: "-3%", severity: "warning", helper: "Vibration rising on M-04" },
];

export const supervisorKpis: Kpi[] = [
  { label: "Shift Yield", value: "97.8%", trend: "+1.1%", severity: "normal", helper: "Across 6 active lines" },
  { label: "Review Queue", value: "18", trend: "6 critical", severity: "warning", helper: "Oldest waiting 11m" },
  { label: "Anomaly Rate", value: "2.6%", trend: "+0.4%", severity: "warning", helper: "Driven by Line B" },
  { label: "Downtime", value: "24m", trend: "-8m", severity: "normal", helper: "Compared with prior shift" },
];

export const executiveKpis: Kpi[] = [
  { label: "Weekly FPY", value: "96.4%", trend: "+2.3%", severity: "normal", helper: "Plant-wide first pass yield" },
  { label: "Scrap Avoided", value: "$42.8k", trend: "this month", severity: "normal", helper: "AI-assisted isolation impact" },
  { label: "Downtime Cost", value: "$8.1k", trend: "-18%", severity: "warning", helper: "Needle maintenance still dominant" },
  { label: "Defect Reduction", value: "31%", trend: "90 days", severity: "normal", helper: "After model rollout" },
];

export const detections: DefectDetection[] = [
  {
    id: "FG-10482",
    timestamp: new Date(Date.now() - 48_000).toISOString(),
    line: "Line A2",
    machine: "M-04",
    product: "Rib knit batch 22-K",
    defect: "needle_line",
    confidence: 0.94,
    inferenceMs: 84,
    severity: "critical",
    status: "new",
    bbox: { x: 46, y: 28, width: 18, height: 31 },
    imageUrl: "",
    explanation: "High-confidence vertical thread disruption aligned with tool-age threshold breach.",
    operator: "Nisha",
  },
  {
    id: "FG-10481",
    timestamp: new Date(Date.now() - 180_000).toISOString(),
    line: "Line B1",
    machine: "M-02",
    product: "Jersey roll 18-C",
    defect: "drop_stitch",
    confidence: 0.87,
    inferenceMs: 91,
    severity: "warning",
    status: "reviewing",
    bbox: { x: 22, y: 38, width: 12, height: 16 },
    imageUrl: "",
    explanation: "Localized loop discontinuity; tension sensor exceeded baseline during frame capture.",
    operator: "Arun",
  },
  {
    id: "FG-10477",
    timestamp: new Date(Date.now() - 420_000).toISOString(),
    line: "Line C3",
    machine: "M-06",
    product: "Interlock panel 07-A",
    defect: "stain",
    confidence: 0.79,
    inferenceMs: 78,
    severity: "advisory",
    status: "approved",
    bbox: { x: 60, y: 55, width: 14, height: 11 },
    imageUrl: "",
    explanation: "Low-area chromatic anomaly with stable machine state; sample flagged for audit trail.",
  },
];

export const sensors: SensorReading[] = [
  { id: "temp", machine: "M-04", metric: "Temperature", value: 65, unit: "C", threshold: 63, status: "warning" },
  { id: "vibration", machine: "M-04", metric: "Vibration", value: 1.82, unit: "mm/s", threshold: 1.5, status: "critical" },
  { id: "pressure", machine: "M-02", metric: "Pressure", value: 6.2, unit: "bar", threshold: 7.1, status: "normal" },
  { id: "humidity", machine: "Zone 2", metric: "Humidity", value: 54, unit: "%", threshold: 65, status: "normal" },
  { id: "rpm", machine: "M-06", metric: "RPM", value: 1180, unit: "rpm", threshold: 1300, status: "normal" },
  { id: "load", machine: "M-04", metric: "Machine Load", value: 84, unit: "%", threshold: 82, status: "warning" },
  { id: "energy", machine: "Line A", metric: "Energy Usage", value: 42.1, unit: "kWh", threshold: 45, status: "normal" },
];

export const machines: MachineHealth[] = [
  { id: "M-01", name: "Circular Knit 01", line: "Line A1", health: 94, state: "running", oee: 0.89, defectRate: 0.018, nextService: "18h" },
  { id: "M-02", name: "Circular Knit 02", line: "Line B1", health: 76, state: "warning", oee: 0.81, defectRate: 0.035, nextService: "6h" },
  { id: "M-04", name: "Rib Knit 04", line: "Line A2", health: 58, state: "warning", oee: 0.73, defectRate: 0.062, nextService: "Now" },
  { id: "M-06", name: "Interlock 06", line: "Line C3", health: 88, state: "running", oee: 0.86, defectRate: 0.021, nextService: "22h" },
];

export const alerts: AlertEvent[] = [
  { id: "AL-9001", timestamp: new Date(Date.now() - 60_000).toISOString(), title: "Critical needle-line cluster", message: "M-04 produced 3 high-confidence needle-line defects in 7 minutes.", severity: "critical", area: "Line A2", acknowledged: false },
  { id: "AL-8998", timestamp: new Date(Date.now() - 540_000).toISOString(), title: "Vibration threshold breach", message: "M-02 vibration exceeded warning threshold during batch 18-C.", severity: "warning", area: "Line B1", acknowledged: false },
  { id: "AL-8994", timestamp: new Date(Date.now() - 1_200_000).toISOString(), title: "Few-shot profile stale", message: "PatchCore reference set for product 22-K has not been refreshed this shift.", severity: "advisory", area: "AI Training", acknowledged: true },
];

export const trends: TrendPoint[] = [
  { time: "06:00", defects: 8, throughput: 1120, confidence: 91, anomaly: 2.1 },
  { time: "07:00", defects: 5, throughput: 1210, confidence: 94, anomaly: 1.8 },
  { time: "08:00", defects: 11, throughput: 1284, confidence: 93, anomaly: 2.6 },
  { time: "09:00", defects: 16, throughput: 1198, confidence: 90, anomaly: 3.1 },
  { time: "10:00", defects: 7, throughput: 1304, confidence: 95, anomaly: 1.9 },
  { time: "11:00", defects: 9, throughput: 1268, confidence: 96, anomaly: 2.2 },
];
