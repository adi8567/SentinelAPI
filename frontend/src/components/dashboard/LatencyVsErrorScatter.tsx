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

interface Props {
  data: EndpointHealthMetric[];
  onSelectEndpoint?: (endpointId: string) => void;
}

export function LatencyVsErrorScatter({ data, onSelectEndpoint }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="p-5 bg-slate-900/70 backdrop-blur-md rounded-xl border border-slate-800 flex items-center justify-center min-h-[260px] text-slate-500 text-xs font-mono">
        <ScatterIcon className="w-5 h-5 mr-2 opacity-50" />
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
    if (health === 'critical') return '#f43f5e';
    if (health === 'degraded') return '#f59e0b';
    return '#10b981';
  };

  return (
    <div className="p-5 bg-slate-900/70 backdrop-blur-md rounded-xl border border-slate-800 flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20">
            <ScatterIcon className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-mono">
              Latency vs Error Rate Scatter Plot
            </h4>
            <p className="text-xs text-slate-400">
              X: Avg Latency (ms) • Y: Error Rate (%) • Bubble size: Call Volume
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-[260px] w-full">
        <ResponsiveContainer width="100%" height={260}>
          <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              type="number"
              dataKey="x"
              name="Avg Latency"
              unit="ms"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Error Rate"
              unit="%"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              domain={[0, 'auto']}
            />
            <ZAxis type="number" dataKey="z" range={[50, 400]} />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const d = payload[0].payload;
                  return (
                    <div className="p-3 bg-slate-900 border border-slate-700 rounded-lg shadow-xl font-mono text-xs space-y-1">
                      <div className="text-cyan-400 font-bold">{d.name}</div>
                      <div className="text-slate-300">
                        Avg Latency: <span className="font-semibold text-white">{d.x.toFixed(1)}ms</span>
                      </div>
                      <div className="text-slate-300">
                        Error Rate: <span className="font-semibold text-rose-400">{d.y.toFixed(1)}%</span>
                      </div>
                      <div className="text-slate-400">Total Calls: {d.calls.toLocaleString()}</div>
                      <div className="text-slate-400 capitalize">Health: {d.health}</div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Scatter
              name="Endpoints"
              data={chartData}
              onClick={(node: any) => onSelectEndpoint && onSelectEndpoint(node?.payload?.endpoint_id || node?.endpoint_id)}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getColor(entry.health)} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
