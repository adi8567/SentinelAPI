'use client';

import React, { useState } from 'react';
import { AlertRecord, AlertSeverity, AlertStatus } from '@/lib/types';
import {
  BellRing,
  Ban,
  Clock,
  Eye,
} from 'lucide-react';

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
          <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-rose-500/20 text-rose-400 border border-rose-500/40 animate-pulse">
            CRITICAL
          </span>
        );
      case 'high':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-amber-500/20 text-amber-400 border border-amber-500/40">
            HIGH
          </span>
        );
      case 'medium':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold font-mono bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">
            MEDIUM
          </span>
        );
      case 'low':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
            LOW
          </span>
        );
    }
  };

  const getStatusBadge = (st: AlertStatus) => {
    switch (st) {
      case 'new':
        return <span className="text-cyan-400">● New</span>;
      case 'investigating':
        return <span className="text-amber-400">● Investigating</span>;
      case 'mitigated':
        return <span className="text-purple-400">● Mitigated</span>;
      case 'resolved':
        return <span className="text-emerald-400">● Resolved</span>;
      case 'false_positive':
        return <span className="text-slate-400">● False Positive</span>;
    }
  };

  return (
    <div className="p-5 bg-slate-900/70 backdrop-blur-md rounded-xl border border-slate-800 flex flex-col h-full">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <BellRing className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-mono">
              Live Incident Alert Timeline & SOC Responses
            </h4>
            <p className="text-xs text-slate-400">
              Chronological security alarms with automated mitigations & root cause drill-down
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-2.5 py-1 bg-slate-800 border border-slate-700 rounded-lg text-slate-300 focus:outline-none focus:border-cyan-500"
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
            className="px-2.5 py-1 bg-slate-800 border border-slate-700 rounded-lg text-slate-300 focus:outline-none focus:border-cyan-500"
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
          <div className="p-8 text-center text-slate-500">
            No incident alerts found for the selected filter criteria.
          </div>
        ) : (
          filtered.map((alert) => (
            <div
              key={alert.alert_id}
              className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800 hover:border-slate-700 transition-all space-y-2 group"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  {getSeverityBadge(alert.severity)}
                  <span className="font-bold text-slate-100">
                    {alert.http_method} {alert.endpoint}
                  </span>
                  <span className="text-[11px] text-slate-400">
                    from <span className="text-cyan-400">{alert.client_ip}</span>
                  </span>
                </div>

                <div className="flex items-center gap-3 text-[11px]">
                  <span className="text-slate-400 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(alert.timestamp).toLocaleTimeString()}
                  </span>
                  <span className="font-semibold">{getStatusBadge(alert.status)}</span>
                </div>
              </div>

              {/* Factors & Detector */}
              <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-900 text-[11px]">
                <div className="flex flex-wrap items-center gap-1.5 text-slate-400">
                  <span className="text-slate-500">Detector:</span>
                  <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
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
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => onSelectAlert && onSelectAlert(alert)}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-cyan-500/20 hover:text-cyan-300 text-slate-300 transition-colors flex items-center gap-1 text-[10px]"
                  >
                    <Eye className="w-3 h-3" /> Forensic Trace
                  </button>

                  {alert.status === 'new' && onUpdateStatus && (
                    <button
                      onClick={() => onUpdateStatus(alert.alert_id, 'investigating')}
                      className="px-2 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 transition-colors text-[10px]"
                    >
                      Acknowledge
                    </button>
                  )}

                  {onMitigate && alert.status !== 'mitigated' && (
                    <button
                      onClick={() => onMitigate(alert.alert_id, 'ban_ip')}
                      className="px-2 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 transition-colors flex items-center gap-1 text-[10px]"
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
    </div>
  );
}
