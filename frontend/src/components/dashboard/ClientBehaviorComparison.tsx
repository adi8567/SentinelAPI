'use client';

import React, { useState } from 'react';
import { Users, Search, Ban, Eye } from 'lucide-react';
import { motion } from 'framer-motion';

interface ClientItem {
  client_ip: string;
  reputation_score: number;
  total_requests: number;
  error_count: number;
  distinct_endpoints_count: number;
  is_banned: boolean;
  is_quarantined: boolean;
}

interface Props {
  clients: ClientItem[];
  onInspectClient?: (clientIp: string) => void;
  onBanClient?: (clientIp: string) => void;
  onQuarantineClient?: (clientIp: string) => void;
}

export function ClientBehaviorComparison({
  clients,
  onInspectClient,
  onBanClient,
}: Props) {
  const [search, setSearch] = useState('');

  const filtered = clients.filter((c) =>
    c.client_ip.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.2 }}
      className="glass-card p-5 flex flex-col h-full"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/20 shadow-sm shadow-violet-500/10">
            <Users className="w-4 h-4" aria-hidden="true" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white tracking-wide">
              Client Behavioral Comparison
            </h4>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Reputation scores, error ratios, surface area traversal & enforcement states
            </p>
          </div>
        </div>

        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search client IP..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 pr-3 py-1.5 bg-slate-800/60 border border-slate-700/60 rounded-xl text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500 w-36 sm:w-48 transition-all"
          />
        </div>
      </div>

      <div className="overflow-x-auto flex-1 max-h-[340px]">
        <table className="w-full text-left font-mono text-xs">
          <thead className="sticky top-0 bg-[#0F172A]/90 backdrop-blur-md border-b border-slate-800 text-[10px] text-slate-400 uppercase tracking-widest">
            <tr>
              <th className="py-2.5 px-3">Client Identity</th>
              <th className="py-2.5 px-3">Reputation Score</th>
              <th className="py-2.5 px-3 text-right">Total Requests</th>
              <th className="py-2.5 px-3 text-right">Unique Endpoints</th>
              <th className="py-2.5 px-3 text-center">Status</th>
              <th className="py-2.5 px-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/40">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500">
                  No matching client profiles found.
                </td>
              </tr>
            ) : (
              filtered.map((c) => (
                <tr
                  key={c.client_ip}
                  className="hover:bg-violet-500/5 transition-colors group"
                >
                  <td className="py-2.5 px-3 font-semibold text-white">
                    {c.client_ip}
                  </td>
                  <td className="py-2.5 px-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-20 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            c.reputation_score < 40
                              ? 'bg-rose-500'
                              : c.reputation_score < 70
                              ? 'bg-amber-500'
                              : 'bg-emerald-500'
                          }`}
                          style={{ width: `${c.reputation_score}%` }}
                        />
                      </div>
                      <span
                        className={`text-[11px] font-bold ${
                          c.reputation_score < 40
                            ? 'text-rose-400'
                            : c.reputation_score < 70
                            ? 'text-amber-400'
                            : 'text-emerald-400'
                        }`}
                      >
                        {c.reputation_score.toFixed(0)}/100
                      </span>
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-right text-slate-400">
                    {c.total_requests.toLocaleString()}
                  </td>
                  <td className="py-2.5 px-3 text-right text-slate-400">
                    {c.distinct_endpoints_count}
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    {c.is_banned ? (
                      <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                        BANNED
                      </span>
                    ) : c.is_quarantined ? (
                      <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                        QUARANTINED
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                        ACTIVE
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        type="button"
                        onClick={() => onInspectClient && onInspectClient(c.client_ip)}
                        className="px-2 py-1 rounded-lg bg-slate-800/80 hover:bg-violet-500/20 hover:text-violet-300 text-slate-300 border border-slate-700/60 transition-colors flex items-center gap-1 text-[10px] focus-visible:ring-2 focus-visible:ring-violet-500"
                      >
                        <Eye className="w-3 h-3" /> Inspect
                      </button>

                      {!c.is_banned && onBanClient && (
                        <button
                          type="button"
                          onClick={() => onBanClient(c.client_ip)}
                          className="px-2 py-1 rounded-lg bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/30 transition-colors flex items-center gap-1 text-[10px] font-semibold focus-visible:ring-2 focus-visible:ring-rose-500"
                        >
                          <Ban className="w-3 h-3" /> Ban
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}
