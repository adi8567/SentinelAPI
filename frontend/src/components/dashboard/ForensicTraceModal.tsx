'use client';

import React, { useEffect, useState } from 'react';
import { EventForensicTrace } from '@/lib/types';
import { api } from '@/lib/api';
import {
  X,
  ShieldAlert,
  Cpu,
  Fingerprint,
  Copy,
  Terminal,
} from 'lucide-react';

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

  if (!eventId) return null;

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl flex flex-col overflow-hidden font-mono text-xs">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-rose-500/20 text-rose-400 border border-rose-500/30">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                Forensic Root-Cause Trace & Attack Inspection
              </h3>
              <p className="text-[11px] text-slate-400">
                Correlated Telemetry • Event ID: <code className="text-cyan-400">{eventId}</code>
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {loading ? (
            <div className="py-16 text-center text-slate-400 animate-pulse">
              Reconstructing full forensic trace from persistent analytical storage...
            </div>
          ) : !trace ? (
            <div className="py-16 text-center text-slate-500">
              Trace details could not be loaded for event ID: {eventId}.
            </div>
          ) : (
            <>
              {/* Event Overview Badges */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase">HTTP Interaction</div>
                  <div className="text-slate-200 font-bold mt-1">
                    {trace.normalized_event.http_method} {trace.normalized_event.path}
                  </div>
                </div>
                <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase">Client Origin IP</div>
                  <div className="text-cyan-400 font-bold mt-1">
                    {trace.normalized_event.client_ip}
                  </div>
                </div>
                <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase">Response Status / Latency</div>
                  <div className="text-slate-200 font-bold mt-1">
                    {trace.normalized_event.status_code} • {trace.normalized_event.latency_ms}ms
                  </div>
                </div>
                <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase">Client Reputation</div>
                  <div
                    className={`font-bold mt-1 ${
                      trace.client_reputation >= 80
                        ? 'text-emerald-400'
                        : trace.client_reputation >= 50
                        ? 'text-amber-400'
                        : 'text-rose-400'
                    }`}
                  >
                    {trace.client_reputation.toFixed(1)} / 100
                  </div>
                </div>
              </div>

              {/* Verbatim Raw Log */}
              {trace.raw_log && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-slate-300 font-semibold">
                    <span className="flex items-center gap-1.5">
                      <Terminal className="w-4 h-4 text-cyan-400" />
                      Verbatim Ingested Raw Log (Exact Payload from Ingestion Engine)
                    </span>
                    <button
                      onClick={() => handleCopy(trace.raw_log || '')}
                      className="text-[11px] text-slate-400 hover:text-cyan-400 flex items-center gap-1"
                    >
                      <Copy className="w-3 h-3" />
                      {copied ? 'Copied' : 'Copy Log'}
                    </button>
                  </div>
                  <pre className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 text-[11px] text-slate-300 overflow-x-auto leading-relaxed">
                    {trace.raw_log}
                  </pre>
                </div>
              )}

              {/* Ensemble Detector Scoring Breakdown */}
              <div className="space-y-2">
                <div className="text-slate-300 font-semibold flex items-center gap-1.5">
                  <Cpu className="w-4 h-4 text-purple-400" />
                  Ensemble Anomaly Engine Contributions
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {Object.entries(trace.detector_scores || {}).map(([detector, score]) => (
                    <div
                      key={detector}
                      className="p-3 bg-slate-950/60 rounded-xl border border-slate-800/80 flex items-center justify-between"
                    >
                      <span className="capitalize text-slate-300">
                        {detector.replace('_', ' ')}:
                      </span>
                      <span
                        className={`font-bold px-2 py-0.5 rounded text-[11px] border ${
                          score >= 80
                            ? 'bg-rose-500/20 text-rose-400 border-rose-500/40'
                            : score >= 50
                            ? 'bg-amber-500/20 text-amber-400 border-amber-500/40'
                            : 'bg-cyan-500/10 text-cyan-300 border-cyan-500/20'
                        }`}
                      >
                        {score.toFixed(1)} / 100
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Contributing Factors & Attack Signatures */}
              {trace.contributing_factors && trace.contributing_factors.length > 0 && (
                <div className="space-y-2">
                  <div className="text-slate-300 font-semibold flex items-center gap-1.5">
                    <Fingerprint className="w-4 h-4 text-rose-400" />
                    Identified Explainability Vectors & Trigger Signatures
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {trace.contributing_factors.map((factor, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-1 rounded-lg bg-rose-500/15 text-rose-300 border border-rose-500/30 font-medium"
                      >
                        {factor}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Closed-Loop Adaptive Policy Action Rendered */}
              {trace.policy_decision && (
                <div className="p-4 bg-slate-950/80 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-200">
                      Adaptive Policy Decision Executed
                    </span>
                    <span className="px-2.5 py-0.5 rounded text-[11px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40 uppercase">
                      Action: {trace.policy_decision.action_taken}
                    </span>
                  </div>
                  <div className="text-slate-400 text-[11px]">
                    Matched Policy: <span className="text-slate-200 font-semibold">{trace.policy_decision.matched_policy_name}</span>
                  </div>
                  <div className="text-slate-400 text-[11px]">
                    Reason: <span className="text-slate-300">{trace.policy_decision.reason}</span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-950 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition-colors font-medium text-xs"
          >
            Close Trace
          </button>
        </div>
      </div>
    </div>
  );
}
