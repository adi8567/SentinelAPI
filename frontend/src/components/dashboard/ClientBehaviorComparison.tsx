'use client';

import React, { useState } from 'react';
import { Users, Search } from 'lucide-react';

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
    <div className="p-5 bg-slate-900/70 backdrop-blur-md rounded-xl border border-slate-800 flex flex-col h-full">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Users className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-mono">
              Client & Consumer Behavioral Comparison
            </h4>
            <p className="text-xs text-slate-400">
              Reputation scores, error ratios, surface area traversal & enforcement states
            </p>
          </div>
        </div>

        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search client IP..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 pr-3 py-1 bg-slate-800/80 border border-slate-700 rounded-lg text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-36 sm:w-48"
          />
        </div>
      </div>

      <div className="overflow-x-auto flex-1 max-h-[320px]">
        <table className="w-full text-left font-mono text-xs">
          <thead className="sticky top-0 bg-slate-900 border-b border-slate-800 text-[11px] text-slate-400 uppercase">
            <tr>
              <th className="py-2 px-3">Client IP</th>
              <th className="py-2 px-3 text-right">Reputation</th>
              <th className="py-2 px-3 text-right">Requests</th>
              <th className="py-2 px-3 text-right">Errors</th>
              <th className="py-2 px-3 text-right">Endpoints</th>
              <th className="py-2 px-3 text-center">Enforcement</th>
              <th className="py-2 px-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-500">
                  No matching client identities found.
                </td>
              </tr>
            ) : (
              filtered.map((client) => {
                const rep = client.reputation_score;
                return (
                  <tr
                    key={client.client_ip}
                    className="hover:bg-slate-800/40 transition-colors group"
                  >
                    <td className="py-2 px-3 font-semibold text-slate-200 group-hover:text-cyan-300">
                      {client.client_ip}
                    </td>
                    <td className="py-2 px-3 text-right">
                      <span
                        className={`font-bold ${
                          rep >= 80
                            ? 'text-emerald-400'
                            : rep >= 50
                            ? 'text-amber-400'
                            : 'text-rose-400'
                        }`}
                      >
                        {rep.toFixed(1)}/100
                      </span>
                    </td>
                    <td className="py-2 px-3 text-right text-slate-300">
                      {client.total_requests.toLocaleString()}
                    </td>
                    <td className="py-2 px-3 text-right">
                      <span className={client.error_count > 0 ? 'text-amber-400' : 'text-slate-400'}>
                        {client.error_count}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-right text-slate-300">
                      {client.distinct_endpoints_count}
                    </td>
                    <td className="py-2 px-3 text-center">
                      {client.is_banned ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40">
                          BANNED
                        </span>
                      ) : client.is_quarantined ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40">
                          QUARANTINE
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          CLEAN
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-right space-x-1.5">
                      <button
                        onClick={() => onInspectClient && onInspectClient(client.client_ip)}
                        className="px-2 py-1 rounded bg-slate-800 hover:bg-cyan-500/20 hover:text-cyan-300 text-slate-300 transition-colors text-[10px]"
                        title="Investigate Dossier"
                      >
                        Inspect
                      </button>
                      {!client.is_banned && onBanClient && (
                        <button
                          onClick={() => onBanClient(client.client_ip)}
                          className="px-2 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 transition-colors text-[10px]"
                          title="Apply Adaptive Ban"
                        >
                          Ban
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
