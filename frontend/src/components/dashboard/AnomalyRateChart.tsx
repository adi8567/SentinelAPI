'use client';

import React from 'react';
import { AnomalyTimeseriesPoint } from '@/lib/types';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { ShieldAlert, TrendingUp } from 'lucide-react';

interface Props {
  data: AnomalyTimeseriesPoint[];
}

export function AnomalyRateChart({ data }: Props) {
  const formattedData = data.map((d) => ({
    ...d,
    time: d.bucket_time.includes('T')
      ? d.bucket_time.split('T')[1].substring(0, 5)
      : d.bucket_time.substring(11, 16) || d.bucket_time,
  }));

  return (
    <div className="p-5 bg-slate-900/70 backdrop-blur-md rounded-xl border border-slate-800 flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-mono">
              Anomaly Rate & Threat Severity Over Time
            </h4>
            <p className="text-xs text-slate-400">
              Severity distribution (Bars) vs Avg Risk Score 0–100 (Line)
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-[260px] w-full">
        {formattedData.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs font-mono">
            <TrendingUp className="w-6 h-6 mb-2 stroke-1" />
            No anomalies recorded in current time window. Nominal API behavior.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={formattedData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis yAxisId="left" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis
                yAxisId="right"
                orientation="right"
                domain={[0, 100]}
                stroke="#f43f5e"
                fontSize={11}
                tickLine={false}
              />
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

              <Bar
                yAxisId="left"
                dataKey="critical_count"
                name="Critical Severity"
                stackId="sev"
                fill="#f43f5e"
                radius={[0, 0, 0, 0]}
              />
              <Bar
                yAxisId="left"
                dataKey="high_count"
                name="High Severity"
                stackId="sev"
                fill="#fb923c"
                radius={[0, 0, 0, 0]}
              />
              <Bar
                yAxisId="left"
                dataKey="medium_count"
                name="Medium Severity"
                stackId="sev"
                fill="#facc15"
                radius={[0, 0, 0, 0]}
              />
              <Bar
                yAxisId="left"
                dataKey="low_count"
                name="Low Severity"
                stackId="sev"
                fill="#38bdf8"
                radius={[4, 4, 0, 0]}
              />

              <Line
                yAxisId="right"
                type="monotone"
                dataKey="avg_risk_score"
                name="Avg Risk Score"
                stroke="#ec4899"
                strokeWidth={2.5}
                dot={{ r: 3, fill: '#ec4899' }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
