'use client';

import React, { useState } from 'react';
import { EndpointHealthMetric } from '@/lib/types';
import { HeartPulse, CheckCircle2, AlertCircle, XCircle, Search } from 'lucide-react';

interface Props {
  data: EndpointHealthMetric[];
  onSelectEndpoint?: (endpointId: string) => void;
}

export function EndpointHealthMatrix({ data, onSelectEndpoint }: Props) {
  const [searchTerm, setSearchTerm] = useState('');
  const [healthFilter, setHealthFilter] = useState<'all' | 'healthy' | 'degraded' | 'critical'>('all');

  const filtered = data.filter((item) => {
    const matchesSearch =
      item.path_template.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.http_method.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesHealth = healthFilter === 'all' || item.health_status === healthFilter;
    return matchesSearch && matchesHealth;
  });

  const getHealthBadge = (status: string) => {
    switch (status) {
      case 'healthy':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3" /> Healthy
          </span>
        );
      case 'degraded':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <AlertCircle className="w-3 h-3" /> Degraded
          </span>
        );
      case 'critical':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30 animate-pulse">
            <XCircle className="w-3 h-3" /> Critical
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="p-5 bg-slate-900/70 backdrop-blur-md rounded-xl border border-slate-800 flex flex-col h-full">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <HeartPulse className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-mono">
              API Endpoint Health & Reliability Matrix
            </h4>
            <p className="text-xs text-slate-400">
              Discovered endpoints, error rate %, and latency vs learned baseline
            </p>
          </div>
        </div>

        {/* Search & Status Filters */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search endpoint..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 pr-3 py-1 bg-slate-800/80 border border-slate-700 rounded-lg text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-36 sm:w-48"
            />
          </div>

          <div className="flex bg-slate-800/80 p-0.5 rounded-lg border border-slate-700 text-xs font-mono">
            {(['all', 'healthy', 'degraded', 'critical'] as const).map((status) => (
              <button
                key={status}
                onClick={() => setHealthFilter(status)}
                className={`px-2 py-0.5 rounded-md uppercase text-[10px] transition-colors ${
                  healthFilter === status
                    ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Health Table */}
      <div className="overflow-x-auto flex-1 max-h-[320px]">
        <table className="w-full text-left font-mono text-xs">
          <thead className="sticky top-0 bg-slate-900 border-b border-slate-800 text-[11px] text-slate-400 uppercase">
            <tr>
              <th className="py-2 px-3">Method</th>
              <th className="py-2 px-3">Path Template</th>
              <th className="py-2 px-3 text-right">Calls</th>
              <th className="py-2 px-3 text-right">Error Rate</th>
              <th className="py-2 px-3 text-right">Avg Latency</th>
              <th className="py-2 px-3 text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500">
                  No matching endpoints found.
                </td>
              </tr>
            ) : (
              filtered.map((ep) => (
                <tr
                  key={ep.endpoint_id}
                  onClick={() => onSelectEndpoint && onSelectEndpoint(ep.endpoint_id)}
                  className="hover:bg-slate-800/40 transition-colors cursor-pointer group"
                >
                  <td className="py-2 px-3">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-cyan-400 border border-slate-700">
                      {ep.http_method}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-slate-200 group-hover:text-cyan-300 font-semibold truncate max-w-xs">
                    {ep.path_template}
                  </td>
                  <td className="py-2 px-3 text-right text-slate-300">
                    {ep.total_requests.toLocaleString()}
                  </td>
                  <td className="py-2 px-3 text-right font-bold">
                    <span
                      className={
                        ep.error_rate_percent > 20
                          ? 'text-rose-400'
                          : ep.error_rate_percent > 5
                          ? 'text-amber-400'
                          : 'text-emerald-400'
                      }
                    >
                      {ep.error_rate_percent.toFixed(1)}%
                    </span>
                  </td>
                  <td className="py-2 px-3 text-right text-slate-300">
                    {ep.avg_latency_ms.toFixed(1)}ms
                  </td>
                  <td className="py-2 px-3 text-center">{getHealthBadge(ep.health_status)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
