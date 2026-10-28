'use client';

import React, { useState } from 'react';
import { TrafficTimeseriesPoint } from '@/lib/types';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { Activity, Clock } from 'lucide-react';
import { motion } from 'framer-motion';

interface Props {
  data: TrafficTimeseriesPoint[];
}

export function TrafficVolumeChart({ data }: Props) {
  const [filterMode, setFilterMode] = useState<'stacked' | 'total'>('stacked');

  const formattedData = data.map((d) => {
    const rawTime = (d as any).bucket_time || (d as any).timestamp || new Date().toISOString();
    const timeStr = typeof rawTime === 'string' ? rawTime : new Date(rawTime).toISOString();
    const time = timeStr.includes('T') ? timeStr.split('T')[1].substring(0, 5) : timeStr.substring(11, 16) || timeStr;

    return {
      ...d, time,
      total_requests: d.total_requests ?? 0,
      status_2xx: d.status_2xx ?? Math.max(0, (d.total_requests ?? 0) - (d.status_4xx ?? 0) - (d.status_5xx ?? 0)),
      status_3xx: d.status_3xx ?? 0,
      status_4xx: d.status_4xx ?? 0,
      status_5xx: d.status_5xx ?? 0,
      avg_latency_ms: d.avg_latency_ms ?? 0,
      p95_latency_ms: d.p95_latency_ms ?? (d.avg_latency_ms ? d.avg_latency_ms * 1.3 : 0),
    };
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.1 }}
      className="glass-card p-5 flex flex-col h-full"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/20">
            <Activity className="w-4 h-4" aria-hidden="true" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white tracking-wide">
              Traffic Volume
            </h4>
            <p className="text-[11px] text-slate-500 mt-0.5">
              HTTP status distribution & latency
            </p>
          </div>
        </div>

        <div className="flex gap-0.5 p-0.5 glass-card-sm text-[11px] font-mono" role="radiogroup" aria-label="Chart view mode">
          <button
            onClick={() => setFilterMode('stacked')}
            role="radio"
            aria-checked={filterMode === 'stacked'}
            className={`px-3 py-1.5 rounded-lg transition-all duration-200 ${
              filterMode === 'stacked' ? 'pill-active' : 'pill-inactive'
            }`}
          >
            By Status
          </button>
          <button
            onClick={() => setFilterMode('total')}
            role="radio"
            aria-checked={filterMode === 'total'}
            className={`px-3 py-1.5 rounded-lg transition-all duration-200 ${
              filterMode === 'total' ? 'pill-active' : 'pill-inactive'
            }`}
          >
            Total
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-[260px] w-full">
        {formattedData.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-600 text-xs font-mono gap-2">
            <Clock className="w-8 h-8 stroke-1 text-slate-700" />
            <span>No traffic in current window</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={formattedData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="color2xx" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="color3xx" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="color4xx" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="color5xx" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#7C3AED" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#7C3AED" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.4)" vertical={false} />
              <XAxis dataKey="time" stroke="#475569" fontSize={10} tickLine={false} axisLine={false} />
              <YAxis stroke="#475569" fontSize={10} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15,23,42,0.95)',
                  backdropFilter: 'blur(12px)',
                  borderColor: 'rgba(124,58,237,0.3)',
                  borderRadius: '12px',
                  fontSize: '11px',
                  fontFamily: 'monospace',
                  boxShadow: '0 8px 30px rgba(0,0,0,0.4)',
                }}
              />
              <Legend wrapperStyle={{ fontSize: '10px', fontFamily: 'monospace', paddingTop: '10px' }} />

              {filterMode === 'stacked' ? (
                <>
                  <Area type="monotone" dataKey="status_2xx" name="2xx" stackId="1" stroke="#10b981" strokeWidth={1.5} fill="url(#color2xx)" />
                  <Area type="monotone" dataKey="status_3xx" name="3xx" stackId="1" stroke="#8B5CF6" strokeWidth={1.5} fill="url(#color3xx)" />
                  <Area type="monotone" dataKey="status_4xx" name="4xx" stackId="1" stroke="#f59e0b" strokeWidth={1.5} fill="url(#color4xx)" />
                  <Area type="monotone" dataKey="status_5xx" name="5xx" stackId="1" stroke="#ef4444" strokeWidth={1.5} fill="url(#color5xx)" />
                </>
              ) : (
                <Area type="monotone" dataKey="total_requests" name="Volume" stroke="#7C3AED" strokeWidth={2} fill="url(#colorTotal)" />
              )}
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </motion.div>
  );
}
