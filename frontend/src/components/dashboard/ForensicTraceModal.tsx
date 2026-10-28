'use client';

import React, { useEffect, useState } from 'react';
import { EventForensicTrace } from '@/lib/types';
import { api } from '@/lib/api';
import {
  X,
  ShieldAlert,
  Cpu,
  Copy,
  Check,
  Terminal,
  Activity,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Props {
  eventId: string | null;
  onClose: () => void;
}

export function ForensicTraceModal({ eventId, onClose }: Props) {
  const [trace, setTrace] = useState<EventForensicTrace | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!eventId) return;
    setLoading(true);
    api
      .traceEvent(eventId)
      .then((data) => setTrace(data))
      .catch((err) => {
        console.error('Failed to load forensic trace:', err);
      })
      .finally(() => setLoading(false));
  }, [eventId]);

  // Keyboard escape handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (eventId) {
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [eventId, onClose]);

  if (!eventId) return null;

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <AnimatePresence>
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        onClick={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          transition={{ duration: 0.25 }}
          className="relative w-full max-w-4xl max-h-[90vh] glass-card border border-slate-700/60 shadow-2xl flex flex-col overflow-hidden font-mono text-xs glow-violet-soft"
        >
          {/* Header */}
          <div className="px-6 py-4 bg-[#0F172A]/90 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-rose-500/15 text-rose-400 border border-rose-500/30">
                <ShieldAlert className="w-5 h-5" aria-hidden="true" />
              </div>
              <div>
                <h3 id="modal-title" className="text-sm font-bold text-white tracking-wide">
                  Forensic Root-Cause Trace
                </h3>
                <p className="text-[11px] text-slate-400">
                  Event ID: <code className="text-violet-400 font-semibold">{eventId}</code>
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-xl glass-card-sm text-slate-400 hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-violet-500"
              aria-label="Close dialog"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content Body */}
          <div className="p-6 overflow-y-auto space-y-5 flex-1">
            {loading ? (
              <div className="py-16 flex flex-col items-center justify-center gap-3 text-slate-500">
                <Activity className="w-8 h-8 animate-spin text-violet-400" />
                <span>Extracting forensic telemetry from analytical store...</span>
              </div>
            ) : !trace ? (
              <div className="py-12 text-center text-slate-500">
                Trace details could not be retrieved for this event.
              </div>
            ) : (
              <>
                {/* Score Breakdown Row */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="glass-card-sm p-3.5 border border-slate-700/40">
                    <div className="text-slate-500 text-[10px] uppercase tracking-wider font-semibold">
                      Client Reputation
                    </div>
                    <div className="text-lg font-bold text-white mt-1">
                      {trace.client_reputation.toFixed(0)}/100
                    </div>
                  </div>
                  <div className="glass-card-sm p-3.5 border border-slate-700/40">
                    <div className="text-slate-500 text-[10px] uppercase tracking-wider font-semibold">
                      Mitigation Decision
                    </div>
                    <div className="text-lg font-bold text-violet-400 mt-1 uppercase">
                      {trace.policy_decision?.action || 'ALLOW'}
                    </div>
                  </div>
                  <div className="glass-card-sm p-3.5 border border-slate-700/40">
                    <div className="text-slate-500 text-[10px] uppercase tracking-wider font-semibold">
                      Timestamp
                    </div>
                    <div className="text-xs font-semibold text-slate-300 mt-1.5">
                      {new Date(trace.timestamp).toLocaleString()}
                    </div>
                  </div>
                </div>

                {/* Detector Model Scores */}
                <div className="space-y-2">
                  <div className="text-slate-400 font-semibold flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-violet-400" />
                    <span>ML & Signature Detector Ensemble Scores</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                    {Object.entries(trace.detector_scores || {}).map(([det, score]) => (
                      <div
                        key={det}
                        className="p-3 glass-card-sm border border-slate-700/40 rounded-xl flex flex-col justify-between"
                      >
                        <span className="text-slate-500 text-[10px] uppercase truncate">{det}</span>
                        <span
                          className={`text-sm font-bold mt-1 ${
                            score > 70
                              ? 'text-rose-400'
                              : score > 40
                              ? 'text-amber-400'
                              : 'text-slate-200'
                          }`}
                        >
                          {score.toFixed(1)}/100
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Contributing Factors */}
                {trace.contributing_factors && trace.contributing_factors.length > 0 && (
                  <div className="space-y-2">
                    <div className="text-slate-400 font-semibold">Contributing Threat Indicators</div>
                    <div className="flex flex-wrap gap-2">
                      {trace.contributing_factors.map((f, i) => (
                        <span
                          key={i}
                          className="px-2.5 py-1 rounded-full bg-rose-500/15 border border-rose-500/30 text-rose-300 text-[11px] font-semibold"
                        >
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Raw Log Block */}
                {trace.raw_log && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400 font-semibold flex items-center gap-2">
                        <Terminal className="w-4 h-4 text-violet-400" /> Raw Access Log
                      </span>
                      <button
                        type="button"
                        onClick={() => handleCopy(trace.raw_log!)}
                        className="text-[11px] text-violet-400 hover:text-violet-300 flex items-center gap-1 transition-colors"
                      >
                        {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        {copied ? 'Copied' : 'Copy Log'}
                      </button>
                    </div>
                    <pre className="p-3.5 bg-[#080c14] border border-slate-800 rounded-xl overflow-x-auto text-slate-300 text-[11px] font-mono leading-relaxed">
                      {trace.raw_log}
                    </pre>
                  </div>
                )}
              </>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
