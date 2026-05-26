import type { AlertEvent, DefectDetection, Severity } from "@/types/fabriguard";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
type ApiRecord = Record<string, unknown>;

const severityMap: Record<string, Severity> = {
  PASS: "normal",
  LOW: "normal",
  MONITOR: "advisory",
  MEDIUM: "warning",
  HIGH: "warning",
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

function asRecord(value: unknown): ApiRecord {
  return typeof value === "object" && value !== null ? value as ApiRecord : {};
}

function normalizeBbox(bboxValue: unknown, fallback: ReturnType<typeof fallbackBbox>, image?: { width?: number; height?: number }) {
  const bbox = asRecord(bboxValue);
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

export function normalizeDetection(payloadValue: unknown): DefectDetection {
  const payload = asRecord(payloadValue);
  const defects = Array.isArray(payload.defects) ? payload.defects.map(asRecord) : [];
  const prediction = asRecord(payload.prediction);
  const anomaly = asRecord(payload.anomaly);
  const severityPayload = asRecord(payload.severity);
  const rootCause = asRecord(payload.root_cause);
  const processing = asRecord(payload.processing);
  const image = asRecord(payload.image);
  const id = String(payload.id ?? payload.inspection_id ?? crypto.randomUUID());
  const visualDefect = defects[0]?.class ?? payload.defect_class ?? payload.defect;
  const predictionDefect = prediction.is_defect
    ? prediction.label ?? prediction.class
    : null;
  const anomalyOnly = anomaly.is_anomaly || severityPayload.defect === "sensor_anomaly";
  const defect = visualDefect ?? predictionDefect ?? (payload.status === "PASS" ? "normal" : anomalyOnly ? "sensor_anomaly" : "unknown_anomaly");
  const confidence = payload.confidence ?? defects[0]?.confidence ?? prediction.confidence ?? (payload.status === "PASS" ? 1 : 0);
  const severityName = String(severityPayload.name ?? payload.severity ?? payload.severity_name ?? payload.level_name ?? "MONITOR").toUpperCase();
  const bbox = payload.bbox ?? defects[0]?.bbox;
  const fallback = fallbackBbox(id);

  return {
    id,
    timestamp: String(payload.timestamp ?? new Date().toISOString()),
    line: String(payload.line ?? `Line ${String(payload.machine_id ?? payload.machine ?? "M-00").slice(-1)}`),
    machine: String(payload.machine ?? payload.machine_id ?? "M-00"),
    product: String(payload.product ?? "Live production batch"),
    defect: String(defect),
    confidence: boundedPercent(confidence, payload.status === "PASS" ? 1 : 0),
    inferenceMs: Number(payload.inference_ms ?? processing.latency_ms ?? 0),
    severity: severityMap[severityName] ?? "advisory",
    status: payload.status === "PASS" ? "approved" : "new",
    bbox: bbox ? normalizeBbox(bbox, fallback, { width: Number(image.width), height: Number(image.height) }) : { x: 0, y: 0, width: 0, height: 0 },
    imageUrl: String(payload.imageUrl ?? ""),
    explanation: String(payload.explanation ?? rootCause.cause ?? payload.root_cause ?? severityPayload.action ?? payload.action ?? "Live inspection event from backend."),
    operator: payload.operator ? String(payload.operator) : undefined,
  };
}

export function normalizeAlert(payloadValue: unknown): AlertEvent {
  const payload = asRecord(payloadValue);
  const id = String(payload.id ?? payload.alert_id ?? payload.inspection_id ?? crypto.randomUUID());
  const severityName = String(payload.severity ?? payload.level_name ?? payload.alert_name ?? "warning").toUpperCase();
  const severity = severityMap[severityName] === "normal" ? "advisory" : severityMap[severityName] ?? "warning";

  return {
    id,
    timestamp: String(payload.timestamp ?? new Date().toISOString()),
    title: String(payload.title ?? `${payload.defect ?? payload.defect_class ?? "Inspection"} alert`),
    message: String(payload.message ?? payload.action ?? payload.fix ?? "Operator review required."),
    severity: severity as AlertEvent["severity"],
    area: String(payload.area ?? payload.machine_id ?? payload.machine ?? "Production"),
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
    const rows = useMock ? [] : await getJson<unknown[]>("/inspections/recent?count=30", []);
    return rows.map(normalizeDetection);
  },
  alerts: async (useMock: boolean) => {
    const rows = useMock ? [] : await getJson<unknown[]>("/alerts/recent?count=20", []);
    return rows.map(normalizeAlert);
  },
  sensors: (useMock: boolean) => useMock ? Promise.resolve([]) : getJson("/machines/status", []),
  machines: (useMock: boolean) => useMock ? Promise.resolve([]) : getJson("/machines/status", []),
  modelStatus: (useMock: boolean) =>
    useMock ? Promise.resolve({ primary_model: "yolov8", weights_available: false, fallback: null, loaded: false }) : getJson(
      "/model/status",
      { primary_model: "yolov8", weights_available: false, fallback: null, loaded: false },
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
