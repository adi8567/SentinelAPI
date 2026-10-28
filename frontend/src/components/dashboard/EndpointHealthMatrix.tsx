'use client';

import React, { useState } from 'react';
import { EndpointHealthMetric } from '@/lib/types';
import { HeartPulse, CheckCircle2, AlertCircle, XCircle, Search } from 'lucide-react';
import { motion } from 'framer-motion';

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
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/25">
            <CheckCircle2 className="w-3 h-3" /> Healthy
          </span>
        );
      case 'degraded':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/25">
            <AlertCircle className="w-3 h-3" /> Degraded
          </span>
        );
      case 'critical':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30 animate-pulse">
            <XCircle className="w-3 h-3" /> Critical
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="glass-card p-5 flex flex-col h-full"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/20 shadow-sm shadow-violet-500/10">
            <HeartPulse className="w-4 h-4" aria-hidden="true" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white tracking-wide">
              Endpoint Health Matrix
            </h4>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Live latency, error rates & learned baseline compliance
            </p>
          </div>
        </div>

        {/* Search & Status Filters */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search endpoint..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 pr-3 py-1.5 bg-slate-800/60 border border-slate-700/60 rounded-xl text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500 w-36 sm:w-44 transition-all"
            />
          </div>

          <div className="flex bg-slate-800/40 p-0.5 rounded-xl border border-slate-700/50 text-xs font-mono">
            {(['all', 'healthy', 'degraded', 'critical'] as const).map((status) => (
              <button
                key={status}
                onClick={() => setHealthFilter(status)}
                className={`px-2.5 py-1 rounded-lg uppercase text-[9px] font-bold tracking-wider transition-all ${
                  healthFilter === status
                    ? 'pill-active shadow-sm'
                    : 'pill-inactive'
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Health Table */}
      <div className="overflow-x-auto flex-1 max-h-[340px]">
        <table className="w-full text-left font-mono text-xs">
          <thead className="sticky top-0 bg-[#0F172A]/90 backdrop-blur-md border-b border-slate-800 text-[10px] text-slate-400 uppercase tracking-widest">
            <tr>
              <th className="py-2.5 px-3">Method</th>
              <th className="py-2.5 px-3">Path Template</th>
              <th className="py-2.5 px-3 text-right">Calls</th>
              <th className="py-2.5 px-3 text-right">Error Rate</th>
              <th className="py-2.5 px-3 text-right">Avg Latency</th>
              <th className="py-2.5 px-3 text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/40">
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
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      if (onSelectEndpoint) onSelectEndpoint(ep.endpoint_id);
                    }
                  }}
                  className="hover:bg-violet-500/5 transition-colors cursor-pointer group focus-visible:outline-none focus-visible:bg-violet-500/10"
                >
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded-md text-[9px] font-bold bg-slate-800 text-violet-300 border border-slate-700/60">
                      {ep.http_method}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-slate-200 group-hover:text-white font-medium truncate max-w-xs transition-colors">
                    {ep.path_template}
                  </td>
                  <td className="py-2.5 px-3 text-right text-slate-400">
                    {ep.total_requests.toLocaleString()}
                  </td>
                  <td className="py-2.5 px-3 text-right font-bold">
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
                  <td className="py-2.5 px-3 text-right text-slate-400">
                    {ep.avg_latency_ms.toFixed(1)}ms
                  </td>
                  <td className="py-2.5 px-3 text-center">{getHealthBadge(ep.health_status)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}
