"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fabriGuardApi } from "@/lib/api";
import { alerts as mockAlerts, detections as mockDetections } from "@/lib/mock-data";
import type { AlertEvent, DefectDetection } from "@/types/fabriguard";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/dashboard";

export function useLiveFabriGuard(useMock: boolean) {
  const [socketState, setSocketState] = useState<"mock" | "connecting" | "live" | "offline">(
    useMock ? "mock" : "connecting",
  );
  const [liveDetections, setLiveDetections] = useState<DefectDetection[]>([]);
  const [liveAlerts, setLiveAlerts] = useState<AlertEvent[]>([]);

  const detectionsQuery = useQuery({
    queryKey: ["detections", useMock],
    queryFn: () => fabriGuardApi.detections(useMock),
    refetchInterval: useMock ? 30_000 : 60_000,
  });

  const alertsQuery = useQuery({
    queryKey: ["alerts", useMock],
    queryFn: () => fabriGuardApi.alerts(useMock),
    refetchInterval: useMock ? 30_000 : 60_000,
  });

  useEffect(() => {
    if (useMock) {
      setSocketState("mock");
      return;
    }
    setSocketState("connecting");
    const ws = new WebSocket(WS_URL);
    ws.onopen = () => setSocketState("live");
    ws.onerror = () => setSocketState("offline");
    ws.onclose = () => setSocketState("offline");
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "inspection") {
          setLiveDetections((current) => [payload as DefectDetection, ...current].slice(0, 50));
        }
        if (payload.type === "alert") {
          setLiveAlerts((current) => [payload as AlertEvent, ...current].slice(0, 50));
        }
      } catch {
        setSocketState("offline");
      }
    };
    return () => ws.close();
  }, [useMock]);

  return useMemo(
    () => ({
      socketState,
      detections: [...liveDetections, ...(detectionsQuery.data ?? mockDetections)],
      alerts: [...liveAlerts, ...(alertsQuery.data ?? mockAlerts)],
      isLoading: detectionsQuery.isLoading || alertsQuery.isLoading,
    }),
    [alertsQuery.data, alertsQuery.isLoading, detectionsQuery.data, detectionsQuery.isLoading, liveAlerts, liveDetections, socketState],
  );
}
