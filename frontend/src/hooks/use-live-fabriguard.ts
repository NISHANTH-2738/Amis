"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  fabriGuardApi,
  normalizeAlert,
  normalizeDetection,
} from "@/lib/api";

import type {
  AlertEvent,
  DefectDetection,
} from "@/types/fabriguard";

const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ??
  "ws://127.0.0.1:8000/ws/dashboard";

export function useLiveFabriGuard(useMock: boolean) {
  const [socketState, setSocketState] = useState<
    "connecting" | "live" | "offline"
  >("connecting");

  const [liveDetections, setLiveDetections] = useState<
    DefectDetection[]
  >([]);

  const [liveAlerts, setLiveAlerts] = useState<
    AlertEvent[]
  >([]);

  // -----------------------------------------
  // Reconnect Timer
  // -----------------------------------------

  const reconnectRef = useRef<NodeJS.Timeout | null>(
    null,
  );

  // -----------------------------------------
  // React Query Fallback APIs
  // -----------------------------------------

  const detectionsQuery = useQuery({
    queryKey: ["detections", useMock],

    queryFn: () =>
      fabriGuardApi.detections(useMock),

    refetchInterval: useMock ? 30_000 : 60_000,
  });

  const alertsQuery = useQuery({
    queryKey: ["alerts", useMock],

    queryFn: () =>
      fabriGuardApi.alerts(useMock),

    refetchInterval: useMock ? 30_000 : 60_000,
  });

  // -----------------------------------------
  // WebSocket Logic
  // -----------------------------------------

  useEffect(() => {
    let ws: WebSocket;
    let shouldReconnect = true;

    const connectWebSocket = () => {
      console.log(
        "Connecting to WebSocket:",
        WS_URL,
      );

      setSocketState("connecting");

      ws = new WebSocket(WS_URL);

      // -------------------------------------
      // Connected
      // -------------------------------------

      ws.onopen = () => {
        console.log(
          "WebSocket connected successfully",
        );

        setSocketState("live");
      };

      // -------------------------------------
      // Messages
      // -------------------------------------

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          const body = payload.payload ?? payload;

          // -------------------------------
          // Inspection Events
          // -------------------------------

          if (payload.type === "inspection") {
            setLiveDetections((current) =>
              [
                normalizeDetection(body),
                ...current,
              ].slice(0, 50),
            );
          }

          // -------------------------------
          // Alert Events
          // -------------------------------

          if (payload.type === "alert") {
            setLiveAlerts((current) =>
              [
                normalizeAlert(body),
                ...current,
              ].slice(0, 50),
            );
          }
        } catch (err) {
          console.warn(
            "WebSocket parse error:",
            err,
          );

          setSocketState("offline");
        }
      };

      // -------------------------------------
      // Errors
      // -------------------------------------

      ws.onerror = (err) => {
        console.warn(
          "WebSocket connection error:",
          err,
        );

        setSocketState("offline");
      };

      // -------------------------------------
      // Closed
      // -------------------------------------

      ws.onclose = () => {
        if (!shouldReconnect) return;

        setSocketState("offline");

        reconnectRef.current = setTimeout(() => {
          connectWebSocket();
        }, 3000);
      };
    };

    // Initial Connection
    connectWebSocket();

    // -----------------------------------------
    // Cleanup
    // -----------------------------------------

    return () => {
      console.log(
        "Cleaning up WebSocket connection",
      );

      shouldReconnect = false;

      if (reconnectRef.current) {
        clearTimeout(reconnectRef.current);
      }

      if (ws) {
        ws.close();
      }
    };
  }, []);

  // -----------------------------------------
  // Final Combined Data
  // -----------------------------------------

  return useMemo(
    () => ({
      socketState,

      detections: [
        ...liveDetections,
        ...(detectionsQuery.data ?? []),
      ],

      alerts: [
        ...liveAlerts,
        ...(alertsQuery.data ?? []),
      ],

      isLoading:
        detectionsQuery.isLoading ||
        alertsQuery.isLoading,
    }),

    [
      alertsQuery.data,
      alertsQuery.isLoading,
      detectionsQuery.data,
      detectionsQuery.isLoading,
      liveAlerts,
      liveDetections,
      socketState,
    ],
  );
}
