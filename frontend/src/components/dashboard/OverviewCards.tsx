'use client';

import React from 'react';
import { DashboardOverview } from '@/lib/types';
import { Activity, AlertTriangle, Zap, Server } from 'lucide-react';

interface Props {
  overview: DashboardOverview | null;
  wsConnected: boolean;
}

export function OverviewCards({ overview, wsConnected }: Props) {
  if (!overview) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-28 bg-slate-900/60 border border-slate-800 rounded-xl" />
        ))}
      </div>
    );
  }

  const cards = [
    {
      title: 'TOTAL INGESTED TRAFFIC',
      value: overview.total_requests.toLocaleString(),
      subtitle: `${overview.total_endpoints} unique endpoints • ${overview.total_clients} clients`,
      icon: Activity,
      color: 'text-cyan-400',
      border: 'border-cyan-500/30 hover:border-cyan-500/60',
      badge: 'Real Logs Ingested',
      badgeColor: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
    },
    {
      title: 'ANOMALY DETECTION RATE',
      value: `${overview.anomaly_rate_percent.toFixed(2)}%`,
      subtitle: `${overview.total_anomalies} flagged of ${overview.total_requests} requests`,
      icon: AlertTriangle,
      color: overview.anomaly_rate_percent > 15 ? 'text-rose-400' : 'text-amber-400',
      border: overview.anomaly_rate_percent > 15 ? 'border-rose-500/30 hover:border-rose-500/60' : 'border-amber-500/30 hover:border-amber-500/60',
      badge: overview.total_anomalies > 0 ? `${overview.total_anomalies} Scored` : 'Nominal',
      badgeColor: overview.anomaly_rate_percent > 15 ? 'bg-rose-500/10 text-rose-300 border-rose-500/30' : 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    },
    {
      title: 'ACTIVE INCIDENTS & ALERTS',
      value: overview.active_alerts.toLocaleString(),
      subtitle: `${overview.policy_enforcements_count} automated policy actions executed`,
      icon: Zap,
      color: 'text-rose-400',
      border: 'border-rose-500/30 hover:border-rose-500/60',
      badge: `${overview.banned_clients_count} Banned • ${overview.quarantined_clients_count} Quarantined`,
      badgeColor: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
    },
    {
      title: 'API LATENCY (P50 / P95)',
      value: `${overview.p50_latency_ms.toFixed(1)}ms / ${overview.p95_latency_ms.toFixed(1)}ms`,
      subtitle: `P99 tail: ${overview.p99_latency_ms.toFixed(1)}ms across live telemetry`,
      icon: Server,
      color: 'text-emerald-400',
      border: 'border-emerald-500/30 hover:border-emerald-500/60',
      badge: 'SLO Monitored',
      badgeColor: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    },
  ];

  return (
    <div className="space-y-4">
      {/* Live Stream Status Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 bg-slate-900/60 backdrop-blur-md border border-slate-800 rounded-xl text-xs">
        <div className="flex items-center gap-2.5">
          <span className="relative flex h-2.5 w-2.5">
            {wsConnected && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            )}
            <span
              className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                wsConnected ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            />
          </span>
          <span className="font-mono uppercase tracking-wider text-slate-300">
            {wsConnected ? 'REAL-TIME WEBSOCKET STREAM CONNECTED' : 'STREAM RECONNECTING (POLLING FALLBACK)'}
          </span>
          <span className="hidden sm:inline-block text-slate-600">|</span>
          <span className="text-slate-400 font-mono hidden sm:inline-block">
            Target: <code className="text-cyan-400">/api/v1/ws/live</code>
          </span>
        </div>
        <div className="flex items-center gap-3 text-slate-400 font-mono">
          <span>Engine: <span className="text-emerald-400 font-semibold">Active</span></span>
          <span>Adaptive Protection: <span className="text-cyan-400 font-semibold">Enforcing</span></span>
        </div>
      </div>

      {/* 4 Primary High-Level Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div
              key={idx}
              className={`relative overflow-hidden p-5 bg-slate-900/70 backdrop-blur-md rounded-xl border ${card.border} transition-all duration-200 group hover:-translate-y-0.5`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[11px] font-mono tracking-wider text-slate-400 uppercase font-semibold">
                    {card.title}
                  </p>
                  <h3 className="text-2xl font-bold tracking-tight text-white mt-1.5 font-mono">
                    {card.value}
                  </h3>
                </div>
                <div className={`p-2.5 rounded-lg bg-slate-800/80 border border-slate-700/50 ${card.color}`}>
                  <Icon className="w-5 h-5" />
                </div>
              </div>
              <div className="mt-4 flex items-center justify-between text-xs">
                <span className="text-slate-400 truncate max-w-[180px]">{card.subtitle}</span>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono border ${card.badgeColor}`}>
                  {card.badge}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
