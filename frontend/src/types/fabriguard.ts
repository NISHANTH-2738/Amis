import type { LucideIcon } from "lucide-react";

export type Role = "operator" | "supervisor" | "executive";
export type PageKey =
  | "dashboard"
  | "live"
  | "production"
  | "sensors"
  | "machines"
  | "operators"
  | "training"
  | "alerts"
  | "settings";

export type Severity = "critical" | "warning" | "advisory" | "normal";
export type Density = "comfortable" | "compact";

export interface NavItem {
  key: PageKey;
  label: string;
  icon: LucideIcon;
}

export interface Kpi {
  label: string;
  value: string;
  trend: string;
  severity: Severity;
  helper: string;
}

export interface DefectDetection {
  id: string;
  timestamp: string;
  line: string;
  machine: string;
  product: string;
  defect: string;
  confidence: number;
  inferenceMs: number;
  severity: Severity;
  status: "new" | "reviewing" | "approved" | "rejected";
  bbox: { x: number; y: number; width: number; height: number };
  imageUrl: string;
  explanation: string;
  operator?: string;
}

export interface SensorReading {
  id: string;
  machine: string;
  metric: string;
  value: number;
  unit: string;
  threshold: number;
  status: Severity;
}

export interface AlertEvent {
  id: string;
  timestamp: string;
  title: string;
  message: string;
  severity: Exclude<Severity, "normal">;
  area: string;
  acknowledged: boolean;
}

export interface MachineHealth {
  id: string;
  name: string;
  line: string;
  health: number;
  state: "running" | "warning" | "stopped" | "maintenance";
  oee: number;
  defectRate: number;
  nextService: string;
}

export interface TrendPoint {
  time: string;
  defects: number;
  throughput: number;
  confidence: number;
  anomaly: number;
}
