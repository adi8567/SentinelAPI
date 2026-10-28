'use client';

import React from 'react';
import { RiskDistributionData } from '@/lib/types';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { BarChart3, Sliders } from 'lucide-react';
import { motion } from 'framer-motion';

interface Props {
  data: RiskDistributionData | null;
}

export function RiskDistributionChart({ data }: Props) {
  if (!data || !data.histogram) {
    return (
      <div className="glass-card flex items-center justify-center min-h-[300px] text-slate-600 text-xs font-mono">
        <div className="animate-shimmer w-full h-full rounded-2xl" />
      </div>
    );
  }

  let histogramList: Array<{ bucket_label: string; count: number; percentage: number }> = [];
  if (Array.isArray(data.histogram)) {
    histogramList = data.histogram;
  } else if (typeof data.histogram === 'object') {
    const totalCount = Object.values(data.histogram).reduce((sum: number, c: any) => sum + (Number(c) || 0), 0) || 1;
    histogramList = Object.entries(data.histogram).map(([label, count]: [string, any]) => {
      const c = Number(count) || 0;
      return { bucket_label: label, count: c, percentage: (c / totalCount) * 100 };
    });
  }

  if (histogramList.length === 0) {
    return (
      <div className="glass-card p-5 flex items-center justify-center min-h-[300px] text-slate-600 text-xs font-mono">
        No risk events recorded yet.
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
    if (label.includes('80-100') || label.includes('Critical')) return '#ef4444';
    if (label.includes('60-80') || label.includes('High')) return '#f97316';
    if (label.includes('40-60') || label.includes('Medium')) return '#eab308';
    if (label.includes('20-40') || label.includes('Low')) return '#8B5CF6';
    return '#10b981';
  };

  const quantiles = [
    { label: 'Mean', value: meanVal, color: 'text-slate-200' },
    { label: 'P50', value: p50, color: 'text-emerald-400' },
    { label: 'P75', value: p75, color: 'text-amber-400' },
    { label: 'P90', value: p90, color: 'text-orange-400' },
    { label: 'P95', value: p95, color: 'text-rose-400' },
    { label: 'P99', value: p99, color: 'text-red-400' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.2 }}
      className="glass-card p-5 flex flex-col h-full"
    >
      <div className="flex items-center gap-3 mb-5">
        <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <BarChart3 className="w-4 h-4" aria-hidden="true" />
        </div>
        <div>
          <h4 className="text-sm font-semibold text-white tracking-wide">
            Risk Distribution
          </h4>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Score histogram & statistical quantiles
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start flex-1">
        {/* Chart */}
        <div className="lg:col-span-2 min-h-[220px]">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={histogramList} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.4)" vertical={false} />
              <XAxis dataKey="bucket_label" stroke="#475569" fontSize={10} tickLine={false} axisLine={false} />
              <YAxis stroke="#475569" fontSize={10} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15,23,42,0.95)',
                  backdropFilter: 'blur(12px)',
                  borderColor: 'rgba(124,58,237,0.3)',
                  borderRadius: '12px',
                  fontSize: '11px',
                  fontFamily: 'monospace',
                }}
                formatter={(val: any, _name: any, item: any) => {
                  const pct = item?.payload?.percentage != null ? item.payload.percentage.toFixed(1) : '0.0';
                  return [`${val} events (${pct}%)`, 'Count'];
                }}
              />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {histogramList.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getBucketColor(entry.bucket_label)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Quantile Panel */}
        <div className="glass-card-sm p-4 space-y-3 text-xs font-mono">
          <div className="flex items-center gap-2 text-slate-300 font-semibold border-b border-slate-700/40 pb-2">
            <Sliders className="w-3.5 h-3.5 text-violet-400" />
            <span>Quantile Profile</span>
          </div>

          <div className="space-y-2">
            {quantiles.map((q) => (
              <div key={q.label} className="flex justify-between items-center">
                <span className="text-slate-500">{q.label}:</span>
                <span className={`font-bold ${q.color}`}>{q.value.toFixed(1)}</span>
              </div>
            ))}
          </div>

          {/* Mini box plot */}
          <div className="pt-2">
            <div className="relative w-full h-2.5 bg-slate-800/60 rounded-full overflow-hidden border border-slate-700/30">
              <div
                className="absolute top-0 bottom-0 bg-violet-500/25"
                style={{ left: `${Math.min(100, Math.max(0, p25))}%`, width: `${Math.max(0, Math.min(100, p75 - p25))}%` }}
              />
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-rose-400"
                style={{ left: `${Math.min(99, Math.max(0, p50))}%` }}
              />
            </div>
            <div className="flex justify-between text-[9px] text-slate-600 mt-1">
              <span>0</span>
              <span className="text-rose-400">P50</span>
              <span>100</span>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
