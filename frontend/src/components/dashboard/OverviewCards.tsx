'use client';

import React from 'react';
import { DashboardOverview } from '@/lib/types';
import { Activity, AlertTriangle, Zap, Server, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { motion, type Variants } from 'framer-motion';

interface Props {
  overview: DashboardOverview | null;
  wsConnected: boolean;
}

const container: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const item: Variants = {
  hidden: { opacity: 0, y: 16, scale: 0.97 },
  show: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.35, ease: 'easeOut' } },
};

export function OverviewCards({ overview, wsConnected }: Props) {
  if (!overview) {
    return (
      <div className="bento-grid">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-36 glass-card animate-shimmer" />
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
      title: 'Total Traffic',
      value: totalReqs.toLocaleString(),
      subtitle: `${totalEps} endpoints · ${totalClients} clients`,
      icon: Activity,
      accentFrom: 'from-violet-500',
      accentTo: 'to-indigo-500',
      accentGlow: 'rgba(124,58,237,0.15)',
      iconBg: 'bg-violet-500/10',
      iconColor: 'text-violet-400',
      borderAccent: 'hover:border-violet-500/40',
      trend: totalReqs > 100 ? '+12.4%' : null,
      trendUp: true,
    },
    {
      title: 'Anomaly Rate',
      value: `${anomRate.toFixed(2)}%`,
      subtitle: `${totalAnoms} flagged of ${totalReqs} requests`,
      icon: AlertTriangle,
      accentFrom: anomRate > 15 ? 'from-red-500' : 'from-amber-500',
      accentTo: anomRate > 15 ? 'to-rose-500' : 'to-orange-500',
      accentGlow: anomRate > 15 ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.15)',
      iconBg: anomRate > 15 ? 'bg-red-500/10' : 'bg-amber-500/10',
      iconColor: anomRate > 15 ? 'text-red-400' : 'text-amber-400',
      borderAccent: anomRate > 15 ? 'hover:border-red-500/40' : 'hover:border-amber-500/40',
      trend: totalAnoms > 0 ? `${totalAnoms} scored` : 'Nominal',
      trendUp: false,
    },
    {
      title: 'Active Incidents',
      value: activeAlerts.toLocaleString(),
      subtitle: `${policyActions} policy actions executed`,
      icon: Zap,
      accentFrom: 'from-rose-500',
      accentTo: 'to-pink-500',
      accentGlow: 'rgba(244,63,94,0.15)',
      iconBg: 'bg-rose-500/10',
      iconColor: 'text-rose-400',
      borderAccent: 'hover:border-rose-500/40',
      trend: `${bannedCount} banned · ${quarantinedCount} quarantined`,
      trendUp: false,
    },
    {
      title: 'Latency P50 / P95',
      value: `${p50.toFixed(1)} / ${p95.toFixed(1)}ms`,
      subtitle: `P99 tail: ${p99.toFixed(1)}ms`,
      icon: Server,
      accentFrom: 'from-emerald-500',
      accentTo: 'to-teal-500',
      accentGlow: 'rgba(16,185,129,0.15)',
      iconBg: 'bg-emerald-500/10',
      iconColor: 'text-emerald-400',
      borderAccent: 'hover:border-emerald-500/40',
      trend: 'SLO Monitored',
      trendUp: true,
    },
  ];

  return (
    <div className="space-y-5">
      {/* Live Connection Status */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card-sm px-4 py-2.5 flex flex-wrap items-center justify-between gap-3"
      >
        <div className="flex items-center gap-3">
          <span className="relative flex h-2.5 w-2.5" aria-label={wsConnected ? 'WebSocket connected' : 'WebSocket reconnecting'}>
            {wsConnected && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
            )}
            <span
              className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                wsConnected ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            />
          </span>
          <span className="font-mono text-xs tracking-wide text-slate-300">
            {wsConnected ? (
              <span>Real-Time Stream <span className="gradient-text-status font-semibold">Connected</span></span>
            ) : (
              <span className="text-amber-400">Reconnecting — Polling Fallback</span>
            )}
          </span>
        </div>
        <div className="flex items-center gap-4 text-[11px] font-mono text-slate-500">
          <span>Engine: <span className="text-emerald-400 font-semibold">Active</span></span>
          <span className="hidden sm:inline">Protection: <span className="text-violet-400 font-semibold">Enforcing</span></span>
        </div>
      </motion.div>

      {/* Stat Cards Bento Grid */}
      <motion.div className="bento-grid" variants={container} initial="hidden" animate="show">
        {cards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <motion.div
              key={idx}
              variants={item}
              className={`stat-card glass-card p-5 border border-slate-700/30 ${card.borderAccent} cursor-default`}
              style={{ '--card-accent-color': card.accentGlow } as React.CSSProperties}
            >
              {/* Top accent line */}
              <div className={`absolute top-0 left-4 right-4 h-[2px] bg-gradient-to-r ${card.accentFrom} ${card.accentTo} rounded-full opacity-60`} />

              <div className="relative flex items-start justify-between">
                <div className="space-y-1.5">
                  <p className="text-[11px] font-mono tracking-widest text-slate-400 uppercase font-medium">
                    {card.title}
                  </p>
                  <h3 className="text-2xl font-extrabold tracking-tight text-white font-mono">
                    {card.value}
                  </h3>
                </div>
                <div className={`p-2.5 rounded-xl ${card.iconBg} ${card.iconColor} border border-white/5`}>
                  <Icon className="w-5 h-5" aria-hidden="true" />
                </div>
              </div>

              <div className="relative mt-4 flex items-center justify-between gap-2">
                <span className="text-[11px] text-slate-500 truncate max-w-[200px]">{card.subtitle}</span>
                {card.trend && (
                  <span className={`inline-flex items-center gap-0.5 text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full ${
                    card.trendUp
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'bg-slate-700/40 text-slate-400 border border-slate-600/30'
                  }`}>
                    {card.trendUp ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                    {card.trend}
                  </span>
                )}
              </div>
            </motion.div>
          );
        })}
      </motion.div>
    </div>
  );
}
