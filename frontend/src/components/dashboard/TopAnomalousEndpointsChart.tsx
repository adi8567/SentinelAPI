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
import { Flame, ShieldAlert, ArrowUpRight } from 'lucide-react';
import { motion } from 'framer-motion';

interface Props {
  data: TopEndpointAnomalies[];
  onSelectEndpoint?: (endpoint: string) => void;
}

export function TopAnomalousEndpointsChart({ data, onSelectEndpoint }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="glass-card p-5 flex items-center justify-center min-h-[280px] text-slate-500 text-xs font-mono">
        <ShieldAlert className="w-5 h-5 mr-2 text-slate-600" />
        No anomalous endpoints detected. All routes within baseline parameters.
      </div>
    );
  }

  const chartData = data.slice(0, 7).map((ep) => {
    const rawEp = ep.endpoint || (ep as any).path_template || (ep as any).endpoint_id || '/';
    const method = ep.http_method || 'GET';
    const maxScore = ep.max_risk_score ?? (ep as any).highest_risk_score ?? 0;
    const anomCount = ep.anomaly_count ?? 0;
    const detector = ep.primary_detector || (ep as any).risk_level || 'Ensemble';

    return {
      name: `${method} ${rawEp.length > 22 ? rawEp.substring(0, 19) + '...' : rawEp}`,
      fullEndpoint: rawEp,
      method,
      anomaly_count: anomCount,
      max_risk_score: maxScore,
      primary_detector: detector,
    };
  });

  const getHeatmapColor = (score: number) => {
    if (score >= 80) return 'bg-rose-500/15 text-rose-300 border-rose-500/40';
    if (score >= 60) return 'bg-amber-500/15 text-amber-300 border-amber-500/40';
    if (score >= 40) return 'bg-yellow-500/15 text-yellow-300 border-yellow-500/30';
    return 'bg-violet-500/15 text-violet-300 border-violet-500/30';
  };

  const getBarColor = (score: number) => {
    if (score >= 80) return '#ef4444';
    if (score >= 60) return '#f97316';
    if (score >= 40) return '#eab308';
    return '#7c3aed';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.25 }}
      className="glass-card p-5 flex flex-col h-full"
    >
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/20 shadow-sm shadow-violet-500/10">
            <Flame className="w-4 h-4" aria-hidden="true" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white tracking-wide">
              Top Anomalous Endpoints
            </h4>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Ranked by attack volume & threat severity
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start flex-1">
        {/* Horizontal Bar Chart */}
        <div className="min-h-[230px] w-full">
          <ResponsiveContainer width="100%" height={230}>
            <BarChart
              layout="vertical"
              data={chartData}
              margin={{ top: 5, right: 15, left: 10, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.4)" horizontal={false} />
              <XAxis type="number" stroke="#475569" fontSize={10} tickLine={false} axisLine={false} />
              <YAxis
                type="category"
                dataKey="name"
                stroke="#94a3b8"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                width={110}
              />
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
                formatter={(value: any) => [`${value} incidents`, 'Anomalies']}
              />
              <Bar dataKey="anomaly_count" radius={[0, 6, 6, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={getBarColor(entry.max_risk_score)}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Endpoint Heatmap Grid */}
        <div className="space-y-2 font-mono text-xs overflow-y-auto max-h-[230px] pr-1">
          {data.slice(0, 8).map((ep, i) => {
            const endpointStr = ep.endpoint || ep.path_template || ep.endpoint_id || '/';
            const riskScore = ep.max_risk_score ?? ep.highest_risk_score ?? 0;
            return (
              <button
                key={i}
                type="button"
                onClick={() => onSelectEndpoint && onSelectEndpoint(endpointStr)}
                className="w-full text-left p-2.5 rounded-xl glass-card-sm border border-slate-700/40 hover:border-violet-500/50 hover:bg-violet-500/5 transition-all duration-200 cursor-pointer flex items-center justify-between gap-2 group focus-visible:ring-2 focus-visible:ring-violet-500"
              >
                <div className="flex items-center gap-2 truncate">
                  <span className="px-1.5 py-0.5 rounded-md text-[9px] font-bold bg-slate-800 text-violet-300 border border-slate-700/60">
                    {ep.http_method}
                  </span>
                  <span className="text-slate-300 truncate font-mono text-[11px] group-hover:text-white transition-colors">
                    {endpointStr}
                  </span>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] border font-bold ${getHeatmapColor(riskScore)}`}>
                    Score {riskScore.toFixed(0)}
                  </span>
                  <span className="text-[10px] text-slate-500 group-hover:text-slate-400">
                    {ep.anomaly_count} hits
                  </span>
                  <ArrowUpRight className="w-3 h-3 text-slate-600 group-hover:text-violet-400 transition-colors" />
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}
