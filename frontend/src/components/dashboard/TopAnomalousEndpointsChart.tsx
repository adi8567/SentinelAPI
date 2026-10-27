'use client';

import React from 'react';
import { TopEndpointAnomalies } from '@/lib/types';
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
import { Target, Flame } from 'lucide-react';

interface Props {
  data: TopEndpointAnomalies[];
  onSelectEndpoint?: (endpoint: string) => void;
}

export function TopAnomalousEndpointsChart({ data, onSelectEndpoint }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="p-5 bg-slate-900/70 backdrop-blur-md rounded-xl border border-slate-800 flex items-center justify-center min-h-[260px] text-slate-500 text-xs font-mono">
        <Target className="w-5 h-5 mr-2 opacity-50" />
        No anomalous endpoints detected yet. System traffic is within baseline limits.
      </div>
    );
  }

  // Format short endpoint labels for the chart
  const chartData = data.slice(0, 7).map((ep) => {
    const rawEp = ep.endpoint || (ep as any).path_template || (ep as any).endpoint_id || '/';
    const method = ep.http_method || 'GET';
    const maxScore = ep.max_risk_score ?? (ep as any).highest_risk_score ?? 0;
    const anomCount = ep.anomaly_count ?? 0;
    const detector = ep.primary_detector || (ep as any).risk_level || 'Ensemble';

    return {
      name: `${method} ${rawEp.length > 25 ? rawEp.substring(0, 22) + '...' : rawEp}`,
      fullEndpoint: rawEp,
      method,
      anomaly_count: anomCount,
      max_risk_score: maxScore,
      primary_detector: detector,
    };
  });

  const getHeatmapColor = (score: number) => {
    if (score >= 80) return 'bg-rose-500/20 text-rose-300 border-rose-500/40';
    if (score >= 60) return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
    if (score >= 40) return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40';
    return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
  };

  return (
    <div className="p-5 bg-slate-900/70 backdrop-blur-md rounded-xl border border-slate-800 flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <Flame className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-mono">
              Top Anomalous Endpoints & Threat Heatmap
            </h4>
            <p className="text-xs text-slate-400">
              Ranked by anomaly frequency & attack severity (Real Ingested Telemetry)
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        {/* Horizontal Bar Chart */}
        <div className="min-h-[240px]">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart
              layout="vertical"
              data={chartData}
              margin={{ top: 5, right: 20, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
              <XAxis type="number" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis
                type="category"
                dataKey="name"
                stroke="#94a3b8"
                fontSize={10}
                tickLine={false}
                width={120}
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
              <Bar dataKey="anomaly_count" radius={[0, 4, 4, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.max_risk_score >= 80 ? '#f43f5e' : entry.max_risk_score >= 60 ? '#fb923c' : '#06b6d4'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Endpoint Heatmap Grid */}
        <div className="space-y-2 font-mono text-xs overflow-y-auto max-h-[240px] pr-1">
          {data.map((ep, i) => {
            const endpointStr = ep.endpoint || ep.path_template || ep.endpoint_id || '/';
            const riskScore = ep.max_risk_score ?? ep.highest_risk_score ?? 0;
            return (
              <div
                key={i}
                onClick={() => onSelectEndpoint && onSelectEndpoint(endpointStr)}
                className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-700/50 hover:border-cyan-500/50 transition-all cursor-pointer flex items-center justify-between gap-2"
              >
                <div className="flex items-center gap-2 truncate">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-700 text-slate-200">
                    {ep.http_method}
                  </span>
                  <span className="text-slate-200 truncate font-mono text-[11px] hover:text-cyan-400">
                    {endpointStr}
                  </span>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span className={`px-2 py-0.5 rounded text-[10px] border font-bold ${getHeatmapColor(riskScore)}`}>
                    Risk {riskScore.toFixed(0)}
                  </span>
                  <span className="text-[10px] text-slate-400">
                    {ep.anomaly_count} hits
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
