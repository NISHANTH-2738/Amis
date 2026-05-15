"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Check, X, XCircle } from "lucide-react";
import { StatusPill } from "@/components/status";
import { formatPercent } from "@/lib/utils";
import type { DefectDetection } from "@/types/fabriguard";

export function ReviewDrawer({
  detection,
  onClose,
}: {
  detection: DefectDetection | null;
  onClose: () => void;
}) {
  return (
    <AnimatePresence>
      {detection ? (
        <motion.aside
          initial={{ x: 420, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 420, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed right-0 top-0 z-50 h-screen w-full max-w-[420px] border-l border-slate-700 bg-[#0d121a] shadow-2xl"
          aria-label="Defect review drawer"
        >
          <div className="flex h-14 items-center justify-between border-b border-slate-800 px-5">
            <div>
              <div className="text-sm font-semibold text-slate-100">Review {detection.id}</div>
              <div className="text-xs text-slate-500">{detection.line} / {detection.machine}</div>
            </div>
            <button className="rounded-md p-2 text-slate-400 hover:bg-slate-800 hover:text-slate-100" onClick={onClose} aria-label="Close review drawer">
              <XCircle className="h-5 w-5" />
            </button>
          </div>
          <div className="space-y-5 overflow-y-auto p-5">
            <div className="relative aspect-video overflow-hidden rounded-md border border-slate-700 bg-slate-950 grid-bg">
              <div className="absolute inset-0 opacity-80" />
              <div
                className="absolute border-2 border-red-400 bg-red-500/10"
                style={{
                  left: `${detection.bbox.x}%`,
                  top: `${detection.bbox.y}%`,
                  width: `${detection.bbox.width}%`,
                  height: `${detection.bbox.height}%`,
                }}
              />
              <div className="absolute left-3 top-3 rounded bg-red-500/90 px-2 py-1 text-xs font-semibold text-white">
                {detection.defect} / {formatPercent(detection.confidence)}
              </div>
            </div>
            <div className="industrial-panel rounded-md p-4">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-sm font-semibold">AI Explanation</span>
                <StatusPill severity={detection.severity} label={detection.severity} />
              </div>
              <p className="text-sm leading-6 text-slate-300">{detection.explanation}</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button className="inline-flex items-center justify-center gap-2 rounded-md bg-emerald-500 px-4 py-3 text-sm font-semibold text-emerald-950">
                <Check className="h-4 w-4" /> Approve AI
              </button>
              <button className="inline-flex items-center justify-center gap-2 rounded-md bg-red-500 px-4 py-3 text-sm font-semibold text-white">
                <X className="h-4 w-4" /> Reject
              </button>
            </div>
            <textarea
              className="min-h-28 w-full rounded-md border border-slate-700 bg-slate-950 p-3 text-sm text-slate-200 outline-none focus:border-sky-500"
              placeholder="Operator feedback, replacement action, or false-positive note"
            />
          </div>
        </motion.aside>
      ) : null}
    </AnimatePresence>
  );
}
