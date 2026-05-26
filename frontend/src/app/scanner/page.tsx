"use client";

import { useEffect, useRef, useState } from "react";
import {
  Camera,
  Loader2,
  RefreshCcw,
  ShieldCheck,
  Upload,
  Wifi,
} from "lucide-react";

import { fabriGuardApi, normalizeDetection } from "@/lib/api";
import { cn, formatPercent } from "@/lib/utils";
import type { DefectDetection } from "@/types/fabriguard";


export default function ScannerPage() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [captureUrl, setCaptureUrl] = useState<string | null>(null);
  const [result, setResult] = useState<DefectDetection | null>(null);
  const [rawStatus, setRawStatus] = useState<string>("READY");
  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    let activeStream: MediaStream | null = null;

    async function startCamera() {
      try {
        const nextStream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: "environment" },
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        });
        if (!mounted) {
          nextStream.getTracks().forEach((track) => track.stop());
          return;
        }
        activeStream = nextStream;
        setStream(nextStream);
        if (videoRef.current) {
          videoRef.current.srcObject = nextStream;
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Camera access failed");
      }
    }

    startCamera();

    return () => {
      mounted = false;
      activeStream?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  useEffect(() => {
    return () => {
      if (captureUrl) URL.revokeObjectURL(captureUrl);
    };
  }, [captureUrl]);

  const captureAndInspect = async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    const width = video.videoWidth || 1280;
    const height = video.videoHeight || 720;
    canvas.width = width;
    canvas.height = height;

    const context = canvas.getContext("2d");
    if (!context) return;
    context.drawImage(video, 0, 0, width, height);

    setIsScanning(true);
    setError(null);
    setRawStatus("SCANNING");

    try {
      const blob = await new Promise<Blob | null>((resolve) =>
        canvas.toBlob(resolve, "image/jpeg", 0.9),
      );
      if (!blob) throw new Error("Capture failed");

      if (captureUrl) URL.revokeObjectURL(captureUrl);
      const nextUrl = URL.createObjectURL(blob);
      setCaptureUrl(nextUrl);

      const file = new File([blob], `scanner-${Date.now()}.jpg`, {
        type: "image/jpeg",
      });
      const response = await fabriGuardApi.inspectImage(file);
      setRawStatus(response.status ?? "DONE");
      setResult(normalizeDetection(response));
    } catch (err) {
      setRawStatus("ERROR");
      setError(err instanceof Error ? err.message : "Inspection failed");
    } finally {
      setIsScanning(false);
    }
  };

  const bbox = result?.bbox;
  const showBox = Boolean(
    result &&
      bbox &&
      result.defect !== "normal" &&
      bbox.width > 0 &&
      bbox.height > 0,
  );

  return (
    <main className="min-h-screen bg-[#070b10] text-slate-100">
      <section className="mx-auto flex min-h-screen w-full max-w-xl flex-col px-4 py-4">
        <header className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-md border border-sky-500/40 bg-sky-500/10">
              <ShieldCheck className="h-5 w-5 text-sky-300" />
            </div>
            <div>
              <h1 className="text-base font-semibold">Edge Inspection Terminal</h1>
              <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Mobile Scanner</p>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-2 text-xs font-semibold text-emerald-200">
            <Wifi className="h-4 w-4" />
            LIVE
          </div>
        </header>

        <div className="relative min-h-[56vh] overflow-hidden rounded-md border border-slate-800 bg-slate-950">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className={cn(
              "absolute inset-0 h-full w-full object-cover",
              captureUrl && "opacity-0",
            )}
          />
          {captureUrl ? (
            <img
              src={captureUrl}
              alt="Captured inspection frame"
              className="absolute inset-0 h-full w-full object-cover"
            />
          ) : null}
          <div className="pointer-events-none absolute inset-y-0 left-0 w-1/3 bg-sky-300/5" />
          <div className="pointer-events-none absolute inset-x-6 top-6 bottom-6 rounded border border-sky-300/30" />
          {showBox && bbox ? (
            <div
              className="absolute border-2 border-red-400 bg-red-500/10"
              style={{
                left: `${bbox.x}%`,
                top: `${bbox.y}%`,
                width: `${bbox.width}%`,
                height: `${bbox.height}%`,
              }}
            >
              <span className="absolute -top-7 left-0 whitespace-nowrap rounded bg-red-500 px-2 py-1 text-xs font-semibold text-white">
                {result?.defect} {formatPercent(result?.confidence ?? 0)}
              </span>
            </div>
          ) : null}
          <div className="absolute bottom-3 left-3 right-3 grid grid-cols-3 gap-2 text-center text-xs font-semibold">
            <span className="rounded bg-slate-950/90 px-2 py-2 text-slate-300">{rawStatus}</span>
            <span className="rounded bg-slate-950/90 px-2 py-2 text-slate-300">
              {result ? `${result.inferenceMs} ms` : "-- ms"}
            </span>
            <span className="rounded bg-slate-950/90 px-2 py-2 text-slate-300">YOLOv8</span>
          </div>
        </div>

        <canvas ref={canvasRef} className="hidden" />

        {error ? (
          <div className="mt-4 rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {error}
          </div>
        ) : null}

        <section className="mt-4 grid grid-cols-3 gap-3">
          <Metric label="Status" value={rawStatus} tone={rawStatus === "FAIL" ? "bad" : "good"} />
          <Metric label="Defect" value={result?.defect ?? "none"} />
          <Metric label="Confidence" value={result ? formatPercent(result.confidence) : "--"} />
        </section>

        <div className="mt-auto grid grid-cols-[1fr_auto] gap-3 pt-5">
          <button
            onClick={captureAndInspect}
            disabled={isScanning || !stream}
            className="inline-flex h-14 items-center justify-center gap-2 rounded-md bg-sky-400 text-sm font-bold text-sky-950 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isScanning ? <Loader2 className="h-5 w-5 animate-spin" /> : <Camera className="h-5 w-5" />}
            Capture Inspect
          </button>
          <button
            onClick={() => {
              setCaptureUrl(null);
              setResult(null);
              setRawStatus("READY");
              setError(null);
            }}
            className="grid h-14 w-14 place-items-center rounded-md border border-slate-700 bg-slate-950 text-slate-200"
            aria-label="Reset capture"
            title="Reset capture"
          >
            {captureUrl ? <RefreshCcw className="h-5 w-5" /> : <Upload className="h-5 w-5" />}
          </button>
        </div>
      </section>
    </main>
  );
}


function Metric({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "good" | "bad";
}) {
  return (
    <div className="rounded-md border border-slate-800 bg-slate-950 px-3 py-3">
      <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">{label}</div>
      <div
        className={cn(
          "mt-1 truncate font-mono text-sm font-semibold",
          tone === "good" && "text-emerald-300",
          tone === "bad" && "text-red-300",
          tone === "neutral" && "text-slate-100",
        )}
      >
        {value}
      </div>
    </div>
  );
}
