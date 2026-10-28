'use client';

import React, { useState } from 'react';
import { SequenceFlowGraph } from '@/lib/types';
import { GitFork, ArrowRight, ShieldAlert } from 'lucide-react';
import { motion } from 'framer-motion';

interface Props {
  data: SequenceFlowGraph | null;
}

export function SequenceFlowDiagram({ data }: Props) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <div className="glass-card p-5 flex items-center justify-center min-h-[280px] text-slate-500 text-xs font-mono">
        <GitFork className="w-5 h-5 mr-2 text-slate-600" />
        No session call sequences detected yet. Markov transitions will appear with ingested traffic.
      </div>
    );
  }

  const displayedLinks = selectedNode
    ? data.links.filter((l) => l.source === selectedNode || l.target === selectedNode)
    : data.links;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.1 }}
      className="glass-card p-5 flex flex-col h-full"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/20 shadow-sm shadow-violet-500/10">
            <GitFork className="w-4 h-4" aria-hidden="true" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white tracking-wide">
              Call Chain Sequence Flow
            </h4>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Markov state transitions: Normal traversal vs Anomalous out-of-order jumps
            </p>
          </div>
        </div>

        {selectedNode && (
          <button
            type="button"
            onClick={() => setSelectedNode(null)}
            className="text-xs font-mono text-violet-400 hover:text-violet-300 transition-colors"
          >
            Clear Filter ({selectedNode})
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-1">
        {/* Discovered Endpoint State Nodes */}
        <div className="lg:col-span-1 space-y-2 font-mono text-xs overflow-y-auto max-h-[300px] pr-1">
          <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mb-2">
            Discovered Nodes ({data.nodes.length})
          </div>
          {data.nodes.map((node) => {
            const isSelected = selectedNode === node.id;
            return (
              <button
                key={node.id}
                type="button"
                onClick={() => setSelectedNode(isSelected ? null : node.id)}
                className={`w-full text-left p-2.5 rounded-xl border transition-all duration-200 cursor-pointer flex items-center justify-between gap-2 focus-visible:ring-2 focus-visible:ring-violet-500 ${
                  isSelected
                    ? 'pill-active font-semibold shadow-sm'
                    : 'glass-card-sm border-slate-700/40 hover:border-violet-500/40'
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      node.anomaly_count > 0 ? 'bg-rose-500' : 'bg-emerald-500'
                    }`}
                  />
                  <span className="truncate text-slate-200">{node.label}</span>
                </div>
                <div className="text-[10px] text-slate-500 shrink-0">
                  {node.call_count} calls
                </div>
              </button>
            );
          })}
        </div>

        {/* Transition Probability Links */}
        <div className="lg:col-span-2 space-y-2 font-mono text-xs overflow-y-auto max-h-[300px] pr-1">
          <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mb-2">
            Observed State Transitions ({displayedLinks.length})
          </div>
          {displayedLinks.length === 0 ? (
            <div className="p-8 text-center text-slate-500 glass-card-sm">
              No transitions connect with the selected node.
            </div>
          ) : (
            displayedLinks.map((link, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-xl border flex items-center justify-between gap-3 transition-all ${
                  link.is_anomalous
                    ? 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                    : 'glass-card-sm border-slate-700/40 text-slate-300'
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <span className="font-semibold text-white truncate max-w-[140px] sm:max-w-[180px]">
                    {link.source}
                  </span>
                  <ArrowRight
                    className={`w-3.5 h-3.5 shrink-0 ${
                      link.is_anomalous ? 'text-rose-400' : 'text-violet-400'
                    }`}
                  />
                  <span className="font-semibold text-white truncate max-w-[140px] sm:max-w-[180px]">
                    {link.target}
                  </span>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-[11px] text-slate-400">{link.value}x</span>
                  {link.is_anomalous && (
                    <span className="px-2 py-0.5 rounded-full text-[9px] bg-rose-500/20 text-rose-400 border border-rose-500/40 font-bold flex items-center gap-1">
                      <ShieldAlert className="w-3 h-3" /> Anomalous
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </motion.div>
  );
}
