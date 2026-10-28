'use client';

import React, { useState } from 'react';
import { AlertRecord, AlertSeverity, AlertStatus } from '@/lib/types';
import {
  BellRing,
  Ban,
  Clock,
  Eye,
  ShieldAlert,
} from 'lucide-react';
import { motion } from 'framer-motion';

interface Props {
  alerts: AlertRecord[];
  onSelectAlert?: (alert: AlertRecord) => void;
  onMitigate?: (alertId: string, action: 'ban_ip' | 'quarantine' | 'throttle') => void;
  onUpdateStatus?: (alertId: string, status: AlertStatus) => void;
}

export function AlertTimeline({ alerts, onSelectAlert, onMitigate, onUpdateStatus }: Props) {
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const filtered = alerts.filter((a) => {
    const matchesSev = severityFilter === 'all' || a.severity === severityFilter;
    const matchesStatus = statusFilter === 'all' || a.status === statusFilter;
    return matchesSev && matchesStatus;
  });

  const getSeverityBadge = (sev: AlertSeverity) => {
    switch (sev) {
      case 'critical':
        return (
          <span className="px-2 py-0.5 rounded-full text-[9px] font-bold font-mono bg-rose-500/15 text-rose-400 border border-rose-500/30 animate-pulse">
            CRITICAL
          </span>
        );
      case 'high':
        return (
          <span className="px-2 py-0.5 rounded-full text-[9px] font-bold font-mono bg-amber-500/15 text-amber-400 border border-amber-500/30">
            HIGH
          </span>
        );
      case 'medium':
        return (
          <span className="px-2 py-0.5 rounded-full text-[9px] font-semibold font-mono bg-yellow-500/15 text-yellow-300 border border-yellow-500/25">
            MEDIUM
          </span>
        );
      case 'low':
        return (
          <span className="px-2 py-0.5 rounded-full text-[9px] font-semibold font-mono bg-violet-500/15 text-violet-300 border border-violet-500/25">
            LOW
          </span>
        );
    }
  };

  const getStatusBadge = (st: AlertStatus) => {
    switch (st) {
      case 'new':
        return <span className="text-violet-400 flex items-center gap-1 font-semibold">● New</span>;
      case 'investigating':
        return <span className="text-amber-400 flex items-center gap-1 font-semibold">● Investigating</span>;
      case 'mitigated':
        return <span className="text-indigo-400 flex items-center gap-1 font-semibold">● Mitigated</span>;
      case 'resolved':
        return <span className="text-emerald-400 flex items-center gap-1 font-semibold">● Resolved</span>;
      case 'false_positive':
        return <span className="text-slate-400 flex items-center gap-1 font-semibold">● False Positive</span>;
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
          <div className="p-2.5 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20 shadow-sm shadow-rose-500/10">
            <BellRing className="w-4 h-4" aria-hidden="true" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white tracking-wide">
              Incident Response Timeline
            </h4>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Live anomaly alerts, forensic traces & automated mitigations
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-1.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-slate-300 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500 text-xs transition-all"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical Only</option>
            <option value="high">High Only</option>
            <option value="medium">Medium Only</option>
            <option value="low">Low Only</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-slate-300 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500 text-xs transition-all"
          >
            <option value="all">All Statuses</option>
            <option value="new">New</option>
            <option value="investigating">Investigating</option>
            <option value="mitigated">Mitigated</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>
      </div>

      {/* Timeline Stream */}
      <div className="space-y-3 font-mono text-xs overflow-y-auto max-h-[380px] pr-1 flex-1">
        {filtered.length === 0 ? (
          <div className="p-10 text-center text-slate-500 glass-card-sm flex flex-col items-center justify-center gap-2">
            <ShieldAlert className="w-6 h-6 text-slate-600" />
            <span>No alerts match the selected criteria.</span>
          </div>
        ) : (
          filtered.map((alert) => (
            <div
              key={alert.alert_id}
              className="p-4 glass-card-sm border border-slate-700/40 hover:border-violet-500/40 transition-all duration-200 space-y-2.5 group"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  {getSeverityBadge(alert.severity)}
                  <span className="font-bold text-white text-[13px]">
                    {alert.http_method} {alert.endpoint}
                  </span>
                  <span className="text-[11px] text-slate-400">
                    from <span className="text-violet-400 font-semibold">{alert.client_ip}</span>
                  </span>
                </div>

                <div className="flex items-center gap-3 text-[11px]">
                  <span className="text-slate-400 flex items-center gap-1">
                    <Clock className="w-3 h-3 text-slate-500" />
                    {new Date(alert.timestamp).toLocaleTimeString()}
                  </span>
                  <span>{getStatusBadge(alert.status)}</span>
                </div>
              </div>

              {/* Factors & Detector */}
              <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800/80 text-[11px]">
                <div className="flex flex-wrap items-center gap-2 text-slate-400">
                  <span className="text-slate-500">Detector:</span>
                  <span className="px-2 py-0.5 rounded-md bg-slate-800/80 text-violet-300 border border-slate-700/50">
                    {alert.primary_detector}
                  </span>
                  <span className="text-slate-500 ml-1">Risk Score:</span>
                  <span className="font-bold text-rose-400">
                    {alert.risk_score.toFixed(1)}/100
                  </span>
                  {alert.contributing_factors && alert.contributing_factors.length > 0 && (
                    <span className="text-slate-500 truncate max-w-xs ml-1">
                      ({alert.contributing_factors.slice(0, 2).join(', ')})
                    </span>
                  )}
                </div>

                {/* Quick SOC Actions */}
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => onSelectAlert && onSelectAlert(alert)}
                    className="px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-violet-500/20 hover:text-violet-300 text-slate-300 border border-slate-700/60 transition-colors flex items-center gap-1.5 text-[11px] focus-visible:ring-2 focus-visible:ring-violet-500"
                  >
                    <Eye className="w-3 h-3" /> Forensic Trace
                  </button>

                  {alert.status === 'new' && onUpdateStatus && (
                    <button
                      type="button"
                      onClick={() => onUpdateStatus(alert.alert_id, 'investigating')}
                      className="px-2.5 py-1 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/30 transition-colors text-[11px] font-semibold focus-visible:ring-2 focus-visible:ring-amber-500"
                    >
                      Acknowledge
                    </button>
                  )}

                  {onMitigate && alert.status !== 'mitigated' && (
                    <button
                      type="button"
                      onClick={() => onMitigate(alert.alert_id, 'ban_ip')}
                      className="px-2.5 py-1 rounded-lg bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/30 transition-colors flex items-center gap-1 text-[11px] font-semibold focus-visible:ring-2 focus-visible:ring-rose-500"
                    >
                      <Ban className="w-3 h-3" /> Ban Attacker
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </motion.div>
  );
}
