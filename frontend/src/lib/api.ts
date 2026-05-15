import { alerts, detections, machines, sensors, trends } from "@/lib/mock-data";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function getJson<T>(path: string, fallback: T, useMock: boolean): Promise<T> {
  if (useMock) return fallback;
  try {
    const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export const fabriGuardApi = {
  detections: (useMock: boolean) => getJson("/inspections/recent?count=30", detections, useMock),
  alerts: (useMock: boolean) => getJson("/alerts/recent?count=20", alerts, useMock),
  sensors: (useMock: boolean) => getJson("/machines/status", sensors, useMock),
  machines: (useMock: boolean) => getJson("/machines/status", machines, useMock),
  modelStatus: (useMock: boolean) =>
    getJson(
      "/model/status",
      { primary_model: "yolov8", weights_available: false, fallback: "mock_detector", loaded: false },
      useMock,
    ),
  trends: async () => trends,
};
