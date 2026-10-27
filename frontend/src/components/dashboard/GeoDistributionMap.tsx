'use client';

import React from 'react';
import { GeoDistributionPoint } from '@/lib/types';
import { Globe2, ShieldAlert, Shield } from 'lucide-react';

interface Props {
  data: GeoDistributionPoint[];
}

export function GeoDistributionMap({ data }: Props) {
  const sorted = [...data].sort((a, b) => b.request_count - a.request_count);
  const totalGeoRequests = data.reduce((acc, curr) => acc + curr.request_count, 0);

  return (
    <div className="p-5 bg-slate-900/70 backdrop-blur-md rounded-xl border border-slate-800 flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Globe2 className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-mono">
              Geographic Traffic & Threat Origin Map
            </h4>
            <p className="text-xs text-slate-400">
              Client IP geographical distribution and threat score density (Real Data)
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1">
        {/* Visual Map Grid / Node Cards */}
        <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800/80 flex flex-col justify-between">
          <div className="text-xs font-mono text-slate-400 mb-2 flex items-center justify-between">
            <span>Global Ingestion Nodes</span>
            <span className="text-cyan-400">{data.length} Detected Regions</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 my-auto py-2">
            {sorted.slice(0, 6).map((geo) => (
              <div
                key={geo.country_code}
                className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg flex flex-col justify-between hover:border-slate-700 transition-all"
              >
                <div className="flex items-center justify-between">
                  <span className="text-base font-bold font-mono text-slate-200">
                    {geo.country_code}
                  </span>
                  {geo.anomaly_count > 0 ? (
                    <span className="p-1 rounded bg-rose-500/20 text-rose-400 text-[10px]">
                      <ShieldAlert className="w-3 h-3" />
                    </span>
                  ) : (
                    <span className="p-1 rounded bg-emerald-500/20 text-emerald-400 text-[10px]">
                      <Shield className="w-3 h-3" />
                    </span>
                  )}
                </div>
                <div className="mt-2 text-[11px] font-mono text-slate-400 truncate">
                  {geo.country_name}
                </div>
                <div className="mt-1 flex items-baseline justify-between text-xs font-mono">
                  <span className="text-slate-100 font-semibold">{(geo.request_count ?? 0).toLocaleString()} reqs</span>
                  {(geo.threat_score ?? 0) > 0 && (
                    <span className="text-rose-400 text-[10px]">
                      {(geo.threat_score ?? 0).toFixed(0)} risk
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="text-[11px] font-mono text-slate-500 pt-2 border-t border-slate-800/60 flex justify-between">
            <span>Telemetry Source: Ingested Geo-IP Metadata</span>
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
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-400 text-[10px] font-bold">
                      {item.country_code}
                    </span>
                    <span className="text-slate-200">{item.country_name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">{item.request_count.toLocaleString()}</span>
                    <span className="text-slate-500 text-[10px]">({pct.toFixed(1)}%)</span>
                  </div>
                </div>
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden flex">
                  <div
                    className="h-full bg-cyan-500"
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
    </div>
  );
}
