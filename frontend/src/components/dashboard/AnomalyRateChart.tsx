'use client';

import React from 'react';
import { AnomalyTimeseriesPoint } from '@/lib/types';
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { ShieldAlert, TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';

interface Props {
  data: AnomalyTimeseriesPoint[];
}

export function AnomalyRateChart({ data }: Props) {
  const formattedData = data.map((d) => {
    const rawTime = (d as any).bucket_time || (d as any).timestamp || new Date().toISOString();
    const timeStr = typeof rawTime === 'string' ? rawTime : new Date(rawTime).toISOString();
    const time = timeStr.includes('T') ? timeStr.split('T')[1].substring(0, 5) : timeStr.substring(11, 16) || timeStr;

    return {
      ...d, time,
      critical_count: d.critical_count ?? (d as any).critical ?? 0,
      high_count: d.high_count ?? (d as any).high ?? 0,
      medium_count: d.medium_count ?? (d as any).medium ?? 0,
      low_count: d.low_count ?? (d as any).low ?? 0,
      total_anomalies: d.total_anomalies ?? (d as any).total ?? 0,
      avg_risk_score: d.avg_risk_score ?? 0,
    };
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.15 }}
      className="glass-card p-5 flex flex-col h-full"
    >
      <div className="flex items-center gap-3 mb-5">
        <div className="p-2.5 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <ShieldAlert className="w-4 h-4" aria-hidden="true" />
        </div>
        <div>
          <h4 className="text-sm font-semibold text-white tracking-wide">
            Anomaly Severity
          </h4>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Severity stacks & avg risk score trend
          </p>
        </div>
      </div>

      <div className="flex-1 min-h-[260px] w-full">
        {formattedData.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-600 text-xs font-mono gap-2">
            <TrendingUp className="w-8 h-8 stroke-1 text-slate-700" />
            <span>No anomalies in current window</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={formattedData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.4)" vertical={false} />
              <XAxis dataKey="time" stroke="#475569" fontSize={10} tickLine={false} axisLine={false} />
              <YAxis yAxisId="left" stroke="#475569" fontSize={10} tickLine={false} axisLine={false} />
              <YAxis yAxisId="right" orientation="right" domain={[0, 100]} stroke="rgba(239,68,68,0.4)" fontSize={10} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15,23,42,0.95)',
                  backdropFilter: 'blur(12px)',
                  borderColor: 'rgba(239,68,68,0.3)',
                  borderRadius: '12px',
                  fontSize: '11px',
                  fontFamily: 'monospace',
                  boxShadow: '0 8px 30px rgba(0,0,0,0.4)',
                }}
              />
              <Legend wrapperStyle={{ fontSize: '10px', fontFamily: 'monospace', paddingTop: '10px' }} />

              <Bar yAxisId="left" dataKey="critical_count" name="Critical" stackId="sev" fill="#ef4444" radius={[0,0,0,0]} />
              <Bar yAxisId="left" dataKey="high_count" name="High" stackId="sev" fill="#f97316" radius={[0,0,0,0]} />
              <Bar yAxisId="left" dataKey="medium_count" name="Medium" stackId="sev" fill="#eab308" radius={[0,0,0,0]} />
              <Bar yAxisId="left" dataKey="low_count" name="Low" stackId="sev" fill="#8B5CF6" radius={[4,4,0,0]} />

              <Line
                yAxisId="right" type="monotone" dataKey="avg_risk_score" name="Avg Risk"
                stroke="#ef4444" strokeWidth={2} strokeDasharray="4 2"
                dot={{ r: 3, fill: '#ef4444', stroke: '#0F172A', strokeWidth: 2 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </motion.div>
  );
}
