import type { AlertEvent, DefectDetection, Severity } from "@/types/fabriguard";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const severityMap: Record<string, Severity> = {
  PASS: "normal",
  MONITOR: "advisory",
  REVIEW: "warning",
  ALERT: "warning",
  WARNING: "warning",
  ISOLATE: "critical",
  CRITICAL: "critical",
  STOP: "critical",
  REJECT: "critical",
  EMERGENCY: "critical",
};

function boundedPercent(value: unknown, fallback: number) {
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  return Math.max(0.05, Math.min(0.98, Math.abs(numeric)));
}

function fallbackBbox(seed: string) {
  const total = [...seed].reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return {
    x: 12 + (total % 54),
    y: 16 + (total % 42),
    width: 10 + (total % 14),
    height: 10 + (total % 18),
  };
}

function toPercent(value: unknown, fallback: number) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  if (numeric >= 0 && numeric <= 1) return Math.round(numeric * 10000) / 100;
  return numeric;
}

function normalizeBbox(bbox: any, fallback: ReturnType<typeof fallbackBbox>, image?: { width?: number; height?: number }) {
  if (Array.isArray(bbox) && bbox.length === 4) {
    const [x1, y1, x2, y2] = bbox.map(Number);
    if ([x1, y1, x2, y2].every(Number.isFinite)) {
      const imageWidth = Number(image?.width);
      const imageHeight = Number(image?.height);
      if (imageWidth > 0 && imageHeight > 0) {
        return {
          x: (x1 / imageWidth) * 100,
          y: (y1 / imageHeight) * 100,
          width: (Math.max(0, x2 - x1) / imageWidth) * 100,
          height: (Math.max(0, y2 - y1) / imageHeight) * 100,
        };
      }
      return {
        x: x1,
        y: y1,
        width: Math.max(0, x2 - x1),
        height: Math.max(0, y2 - y1),
      };
    }
  }
  return {
    x: toPercent(bbox?.x ?? bbox?.left, fallback.x),
    y: toPercent(bbox?.y ?? bbox?.top, fallback.y),
    width: toPercent(bbox?.width ?? bbox?.w, fallback.width),
    height: toPercent(bbox?.height ?? bbox?.h, fallback.height),
  };
}

export function normalizeDetection(payload: any): DefectDetection {
  const id = String(payload.id ?? payload.inspection_id ?? crypto.randomUUID());
  const defect = payload.defect ?? payload.defect_class ?? payload.prediction?.label ?? payload.prediction?.class ?? payload.defects?.[0]?.class ?? "sensor_anomaly";
  const severityName = String(payload.severity?.name ?? payload.severity ?? payload.severity_name ?? payload.level_name ?? "MONITOR").toUpperCase();
  const bbox = payload.bbox ?? payload.defects?.[0]?.bbox ?? fallbackBbox(id);
  const fallback = fallbackBbox(id);

  return {
    id,
    timestamp: payload.timestamp ?? new Date().toISOString(),
    line: payload.line ?? `Line ${String(payload.machine_id ?? payload.machine ?? "M-00").slice(-1)}`,
    machine: payload.machine ?? payload.machine_id ?? "M-00",
    product: payload.product ?? "Live production batch",
    defect,
    confidence: boundedPercent(payload.confidence ?? payload.defects?.[0]?.confidence, 0.72),
    severity: severityMap[severityName] ?? "advisory",
    status: payload.status === "PASS" ? "approved" : "new",
    bbox: normalizeBbox(bbox, fallback, payload.image),
    imageUrl: payload.imageUrl ?? "",
    explanation: payload.explanation ?? payload.root_cause?.cause ?? payload.root_cause ?? payload.severity?.action ?? payload.action ?? "Live inspection event from FabriGuard backend.",
    operator: payload.operator,
  };
}

export function normalizeAlert(payload: any): AlertEvent {
  const id = String(payload.id ?? payload.alert_id ?? payload.inspection_id ?? crypto.randomUUID());
  const severityName = String(payload.severity ?? payload.level_name ?? payload.alert_name ?? "warning").toUpperCase();
  const severity = severityMap[severityName] === "normal" ? "advisory" : severityMap[severityName] ?? "warning";

  return {
    id,
    timestamp: payload.timestamp ?? new Date().toISOString(),
    title: payload.title ?? `${payload.defect ?? payload.defect_class ?? "Inspection"} alert`,
    message: payload.message ?? payload.action ?? payload.fix ?? "Operator review required.",
    severity: severity as AlertEvent["severity"],
    area: payload.area ?? payload.machine_id ?? payload.machine ?? "Production",
    acknowledged: Boolean(payload.acknowledged),
  };
}

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export const fabriGuardApi = {
  detections: async (useMock: boolean) => {
    const rows = useMock ? [] : await getJson<any[]>("/inspections/recent?count=30", []);
    return rows.map(normalizeDetection);
  },
  alerts: async (useMock: boolean) => {
    const rows = useMock ? [] : await getJson<any[]>("/alerts/recent?count=20", []);
    return rows.map(normalizeAlert);
  },
  sensors: (useMock: boolean) => useMock ? Promise.resolve([]) : getJson("/machines/status", []),
  machines: (useMock: boolean) => useMock ? Promise.resolve([]) : getJson("/machines/status", []),
  modelStatus: (useMock: boolean) =>
    useMock ? Promise.resolve({ primary_model: "roboflow_workflow", weights_available: false, fallback: "hosted_inference", loaded: false }) : getJson(
      "/model/status",
      { primary_model: "roboflow_workflow", weights_available: false, fallback: "hosted_inference", loaded: false },
    ),
  inspectImage: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${API_BASE}/inspect-image`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      throw new Error(`Inspection failed with HTTP ${response.status}`);
    }
    return response.json();
  },
  trends: async () => [],
};
