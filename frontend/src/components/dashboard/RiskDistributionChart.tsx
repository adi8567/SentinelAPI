'use client';

import React from 'react';
import { RiskDistributionData } from '@/lib/types';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { BarChart3, Sliders } from 'lucide-react';

interface Props {
  data: RiskDistributionData | null;
}

export function RiskDistributionChart({ data }: Props) {
  if (!data || !data.histogram) {
    return (
      <div className="p-5 bg-slate-900/70 backdrop-blur-md rounded-xl border border-slate-800 flex items-center justify-center min-h-[260px] text-slate-500 text-xs font-mono">
        Loading risk score distribution telemetry...
      </div>
    );
  }

  // Safely normalize histogram to an array regardless of whether backend returned an object or array
  let histogramList: Array<{ bucket_label: string; count: number; percentage: number }> = [];
  if (Array.isArray(data.histogram)) {
    histogramList = data.histogram;
  } else if (typeof data.histogram === 'object') {
    const totalCount = Object.values(data.histogram).reduce((sum: number, c: any) => sum + (Number(c) || 0), 0) || 1;
    histogramList = Object.entries(data.histogram).map(([label, count]: [string, any]) => {
      const c = Number(count) || 0;
      return {
        bucket_label: label,
        count: c,
        percentage: (c / totalCount) * 100,
      };
    });
  }

  if (histogramList.length === 0) {
    return (
      <div className="p-5 bg-slate-900/70 backdrop-blur-md rounded-xl border border-slate-800 flex items-center justify-center min-h-[260px] text-slate-500 text-xs font-mono">
        No risk distribution events recorded yet.
      </div>
    );
  }

  const p25 = data.p25 ?? 0;
  const p50 = data.p50 ?? 0;
  const p75 = data.p75 ?? 0;
  const p90 = data.p90 ?? 0;
  const p95 = data.p95 ?? 0;
  const p99 = data.p99 ?? 0;
  const meanVal = data.mean ?? p50;

  const getBucketColor = (label: string) => {
    if (label.includes('80-100') || label.includes('Critical')) return '#f43f5e';
    if (label.includes('60-80') || label.includes('High')) return '#fb923c';
    if (label.includes('40-60') || label.includes('Medium')) return '#facc15';
    if (label.includes('20-40') || label.includes('Low')) return '#38bdf8';
    return '#10b981';
  };

  return (
    <div className="p-5 bg-slate-900/70 backdrop-blur-md rounded-xl border border-slate-800 flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <BarChart3 className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-mono">
              Risk Score Distribution & Box Plot Quantiles
            </h4>
            <p className="text-xs text-slate-400">
              Interactive 0–100 risk scoring histogram & percentiles (Real Ingested Data)
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-center">
        {/* Histogram Chart (2 cols) */}
        <div className="lg:col-span-2 min-h-[220px]">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={histogramList} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis dataKey="bucket_label" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '0.5rem',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                }}
                formatter={(val: any, name: any, item: any) => {
                  const pct = item?.payload?.percentage != null ? item.payload.percentage.toFixed(1) : '0.0';
                  return [`${val} events (${pct}%)`, 'Count'];
                }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {histogramList.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getBucketColor(entry.bucket_label)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Statistical Box Plot / Quantiles Card (1 col) */}
        <div className="p-4 bg-slate-800/40 border border-slate-700/60 rounded-xl space-y-3 font-mono text-xs">
          <div className="flex items-center gap-2 text-slate-300 font-semibold border-b border-slate-700/60 pb-2">
            <Sliders className="w-4 h-4 text-cyan-400" />
            <span>Statistical Quantile Profile</span>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Mean Risk Score:</span>
              <span className="text-slate-100 font-bold">{meanVal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Median (P50):</span>
              <span className="text-emerald-400 font-bold">{p50.toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">25th Percentile (P25):</span>
              <span className="text-slate-300">{p25.toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">75th Percentile (P75):</span>
              <span className="text-amber-400">{p75.toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">90th Percentile (P90):</span>
              <span className="text-orange-400 font-semibold">{p90.toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">95th Percentile (P95):</span>
              <span className="text-rose-400 font-bold">{p95.toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">99th Percentile (P99):</span>
              <span className="text-rose-500 font-extrabold">{p99.toFixed(2)}</span>
            </div>
          </div>

          {/* Box plot visual bar */}
          <div className="pt-2">
            <div className="relative w-full h-3 bg-slate-900 rounded-full overflow-hidden border border-slate-700">
              <div
                className="absolute top-0 bottom-0 bg-cyan-500/30"
                style={{
                  left: `${Math.min(100, Math.max(0, p25))}%`,
                  width: `${Math.max(0, Math.min(100, p75 - p25))}%`,
                }}
              />
              <div
                className="absolute top-0 bottom-0 w-1 bg-rose-400 z-10"
                style={{ left: `${Math.min(99, Math.max(0, p50))}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-slate-500 mt-1">
              <span>0</span>
              <span className="text-rose-400">P50</span>
              <span>100</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
