'use client';

import React from 'react';
import { EndpointHealthMetric } from '@/lib/types';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { ScatterChart as ScatterIcon } from 'lucide-react';
import { motion } from 'framer-motion';

interface Props {
  data: EndpointHealthMetric[];
  onSelectEndpoint?: (endpointId: string) => void;
}

export function LatencyVsErrorScatter({ data, onSelectEndpoint }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="glass-card p-5 flex items-center justify-center min-h-[280px] text-slate-500 text-xs font-mono">
        <ScatterIcon className="w-5 h-5 mr-2 text-slate-600" />
        No endpoint performance telemetry available yet.
      </div>
    );
  }

  const chartData = data.map((ep) => ({
    x: ep.avg_latency_ms,
    y: ep.error_rate_percent,
    z: Math.max(20, Math.min(200, ep.total_requests * 10)),
    name: `${ep.http_method} ${ep.path_template}`,
    endpoint_id: ep.endpoint_id,
    health: ep.health_status,
    calls: ep.total_requests,
  }));

  const getColor = (health: string) => {
    if (health === 'critical') return '#ef4444';
    if (health === 'degraded') return '#f59e0b';
    return '#10b981';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.15 }}
      className="glass-card p-5 flex flex-col h-full"
    >
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/20 shadow-sm shadow-violet-500/10">
            <ScatterIcon className="w-4 h-4" aria-hidden="true" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white tracking-wide">
              Latency vs Error Rate Distribution
            </h4>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Multi-dimensional endpoint performance clustering (Bubble size = call volume)
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-[260px] w-full">
        <ResponsiveContainer width="100%" height={260}>
          <ScatterChart margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.4)" />
            <XAxis
              type="number"
              dataKey="x"
              name="Avg Latency"
              unit="ms"
              stroke="#475569"
              fontSize={10}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Error Rate"
              unit="%"
              stroke="#475569"
              fontSize={10}
              tickLine={false}
              axisLine={false}
            />
            <ZAxis type="number" dataKey="z" range={[50, 400]} />
            <Tooltip
              cursor={{ strokeDasharray: '3 3', stroke: 'rgba(124,58,237,0.3)' }}
              contentStyle={{
                backgroundColor: 'rgba(15,23,42,0.95)',
                backdropFilter: 'blur(12px)',
                borderColor: 'rgba(124,58,237,0.3)',
                borderRadius: '12px',
                fontSize: '11px',
                fontFamily: 'monospace',
                boxShadow: '0 8px 30px rgba(0,0,0,0.4)',
              }}
              formatter={(value: any, name: any) => [
                name === 'Avg Latency' ? `${Number(value).toFixed(1)}ms` : `${Number(value).toFixed(1)}%`,
                name,
              ]}
            />
            <Scatter
              name="Endpoints"
              data={chartData}
              onClick={(node: any) => {
                const epId = node?.endpoint_id || node?.payload?.endpoint_id;
                if (onSelectEndpoint && epId) onSelectEndpoint(epId);
              }}
              className="cursor-pointer"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getColor(entry.health)} fillOpacity={0.8} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 pt-3 border-t border-slate-700/30">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500" /> Healthy
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-500" /> Degraded
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-rose-500" /> Critical
          </span>
        </div>
        <span className="text-violet-400">Click node to inspect</span>
      </div>
    </motion.div>
  );
}
