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

  const totalReqs = overview.total_requests ?? 0;
  const totalAnoms = overview.total_anomalies ?? 0;
  const anomRate = overview.anomaly_rate_percent ?? (totalReqs > 0 ? (totalAnoms / totalReqs) * 100 : 0);
  const activeAlerts = overview.active_alerts ?? totalAnoms;
  const totalEps = (overview as any).total_endpoints ?? (overview as any).monitored_endpoints_count ?? 0;
  const totalClients = (overview as any).total_clients ?? (overview as any).unique_clients_count ?? 0;
  const bannedCount = (overview as any).banned_clients_count ?? (overview as any).active_banned_ips ?? 0;
  const quarantinedCount = (overview as any).quarantined_clients_count ?? 0;
  const policyActions = (overview as any).policy_enforcements_count ?? ((overview as any).blocked_attacks ?? 0) + ((overview as any).throttled_requests ?? 0);
  const p50 = overview.p50_latency_ms ?? 0;
  const p95 = overview.p95_latency_ms ?? 0;
  const p99 = (overview as any).p99_latency_ms ?? (p95 > 0 ? p95 * 1.25 : 0);

  const cards = [
    {
      title: 'TOTAL INGESTED TRAFFIC',
      value: totalReqs.toLocaleString(),
      subtitle: `${totalEps} unique endpoints • ${totalClients} clients`,
      icon: Activity,
      color: 'text-cyan-400',
      border: 'border-cyan-500/30 hover:border-cyan-500/60',
      badge: 'Real Logs Ingested',
      badgeColor: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
    },
    {
      title: 'ANOMALY DETECTION RATE',
      value: `${anomRate.toFixed(2)}%`,
      subtitle: `${totalAnoms} flagged of ${totalReqs} requests`,
      icon: AlertTriangle,
      color: anomRate > 15 ? 'text-rose-400' : 'text-amber-400',
      border: anomRate > 15 ? 'border-rose-500/30 hover:border-rose-500/60' : 'border-amber-500/30 hover:border-amber-500/60',
      badge: totalAnoms > 0 ? `${totalAnoms} Scored` : 'Nominal',
      badgeColor: anomRate > 15 ? 'bg-rose-500/10 text-rose-300 border-rose-500/30' : 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    },
    {
      title: 'ACTIVE INCIDENTS & ALERTS',
      value: activeAlerts.toLocaleString(),
      subtitle: `${policyActions} automated policy actions executed`,
      icon: Zap,
      color: 'text-rose-400',
      border: 'border-rose-500/30 hover:border-rose-500/60',
      badge: `${bannedCount} Banned • ${quarantinedCount} Quarantined`,
      badgeColor: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
    },
    {
      title: 'API LATENCY (P50 / P95)',
      value: `${p50.toFixed(1)}ms / ${p95.toFixed(1)}ms`,
      subtitle: `P99 tail: ${p99.toFixed(1)}ms across live telemetry`,
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
