'use client';

import React, { useState } from 'react';
import { TrafficTimeseriesPoint } from '@/lib/types';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Activity, Clock } from 'lucide-react';

interface Props {
  data: TrafficTimeseriesPoint[];
}

export function TrafficVolumeChart({ data }: Props) {
  const [filterMode, setFilterMode] = useState<'stacked' | 'total'>('stacked');

  const formattedData = data.map((d) => ({
    ...d,
    time: d.bucket_time.includes('T')
      ? d.bucket_time.split('T')[1].substring(0, 5)
      : d.bucket_time.substring(11, 16) || d.bucket_time,
  }));

  return (
    <div className="p-5 bg-slate-900/70 backdrop-blur-md rounded-xl border border-slate-800 flex flex-col h-full">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-mono">
              Live API Ingested Traffic Volume
            </h4>
            <p className="text-xs text-slate-400">
              Stacked distribution by HTTP status code & P95 latency (Real Data)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex bg-slate-800/80 p-0.5 rounded-lg border border-slate-700 text-xs font-mono">
            <button
              onClick={() => setFilterMode('stacked')}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                filterMode === 'stacked'
                  ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Status Codes
            </button>
            <button
              onClick={() => setFilterMode('total')}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                filterMode === 'total'
                  ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Total Volume
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-[260px] w-full">
        {formattedData.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs font-mono">
            <Clock className="w-6 h-6 mb-2 stroke-1" />
            No traffic events in current time window. Ingest real logs below to observe live stream.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={formattedData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="color2xx" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="color3xx" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="color4xx" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="color5xx" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '0.5rem',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: '11px', fontFamily: 'monospace', paddingTop: '8px' }}
              />

              {filterMode === 'stacked' ? (
                <>
                  <Area
                    type="monotone"
                    dataKey="status_2xx"
                    name="2xx Success"
                    stackId="1"
                    stroke="#10b981"
                    fill="url(#color2xx)"
                  />
                  <Area
                    type="monotone"
                    dataKey="status_3xx"
                    name="3xx Redirect"
                    stackId="1"
                    stroke="#38bdf8"
                    fill="url(#color3xx)"
                  />
                  <Area
                    type="monotone"
                    dataKey="status_4xx"
                    name="4xx Client Error"
                    stackId="1"
                    stroke="#f59e0b"
                    fill="url(#color4xx)"
                  />
                  <Area
                    type="monotone"
                    dataKey="status_5xx"
                    name="5xx Server Fault"
                    stackId="1"
                    stroke="#f43f5e"
                    fill="url(#color5xx)"
                  />
                </>
              ) : (
                <Area
                  type="monotone"
                  dataKey="total_requests"
                  name="Total Ingested Volume"
                  stroke="#06b6d4"
                  fill="url(#colorTotal)"
                />
              )}
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
