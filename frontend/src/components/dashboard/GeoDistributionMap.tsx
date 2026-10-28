'use client';

import React from 'react';
import { GeoDistributionPoint } from '@/lib/types';
import { Globe2, ShieldAlert, Shield } from 'lucide-react';
import { motion } from 'framer-motion';

interface Props {
  data: GeoDistributionPoint[];
}

export function GeoDistributionMap({ data }: Props) {
  const sorted = [...data].sort((a, b) => b.request_count - a.request_count);
  const totalGeoRequests = data.reduce((acc, curr) => acc + curr.request_count, 0);

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
            <Globe2 className="w-4 h-4" aria-hidden="true" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white tracking-wide">
              Geographic Traffic & Threat Origin
            </h4>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Client IP geographical distribution and threat score density
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1">
        {/* Visual Map Grid / Node Cards */}
        <div className="glass-card-sm p-4 border border-slate-700/40 flex flex-col justify-between">
          <div className="text-xs font-mono text-slate-400 mb-2 flex items-center justify-between">
            <span>Global Ingestion Nodes</span>
            <span className="text-violet-400 font-semibold">{data.length} Detected Regions</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 my-auto py-2">
            {sorted.slice(0, 6).map((geo) => (
              <div
                key={geo.country_code}
                className="p-3 glass-card-sm border border-slate-700/30 rounded-xl flex flex-col justify-between hover:border-violet-500/40 transition-all"
              >
                <div className="flex items-center justify-between">
                  <span className="text-base font-bold font-mono text-white">
                    {geo.country_code}
                  </span>
                  {geo.anomaly_count > 0 ? (
                    <span className="p-1 rounded-full bg-rose-500/20 text-rose-400 text-[10px]">
                      <ShieldAlert className="w-3 h-3" />
                    </span>
                  ) : (
                    <span className="p-1 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px]">
                      <Shield className="w-3 h-3" />
                    </span>
                  )}
                </div>
                <div className="mt-2 text-[11px] font-mono text-slate-400 truncate">
                  {geo.country_name}
                </div>
                <div className="mt-1 flex items-baseline justify-between text-xs font-mono">
                  <span className="text-slate-200 font-semibold">{(geo.request_count ?? 0).toLocaleString()} reqs</span>
                  {(geo.threat_score ?? 0) > 0 && (
                    <span className="text-rose-400 text-[10px]">
                      {(geo.threat_score ?? 0).toFixed(0)} risk
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="text-[11px] font-mono text-slate-500 pt-2 border-t border-slate-700/30 flex justify-between">
            <span>Geo-IP Telemetry</span>
            <span className="text-emerald-400">All Nodes Active</span>
          </div>
        </div>

        {/* Breakdown Progress Bars */}
        <div className="space-y-3 font-mono text-xs overflow-y-auto max-h-[260px] pr-1">
          {sorted.map((item) => {
            const pct = totalGeoRequests > 0 ? (item.request_count / totalGeoRequests) * 100 : 0;
            return (
              <div key={item.country_code} className="space-y-1">
                <div className="flex justify-between items-center text-slate-300">
                  <div className="flex items-center gap-2">
                    <span className="px-1.5 py-0.5 rounded-md bg-slate-800 text-violet-300 border border-slate-700/60 text-[10px] font-bold">
                      {item.country_code}
                    </span>
                    <span className="text-slate-200">{item.country_name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">{item.request_count.toLocaleString()}</span>
                    <span className="text-slate-500 text-[10px]">({pct.toFixed(1)}%)</span>
                  </div>
                </div>
                <div className="w-full h-1.5 bg-slate-800/80 rounded-full overflow-hidden flex">
                  <div
                    className="h-full bg-gradient-to-r from-violet-600 to-indigo-500"
                    style={{ width: `${Math.max(2, pct)}%` }}
                  />
                  {item.anomaly_count > 0 && (
                    <div
                      className="h-full bg-rose-500"
                      style={{
                        width: `${Math.min(100, (item.anomaly_count / item.request_count) * 100)}%`,
                      }}
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}
