'use client';

import React, { useState } from 'react';
import { SequenceFlowGraph } from '@/lib/types';
import { GitFork, ArrowRight, ShieldAlert } from 'lucide-react';

interface Props {
  data: SequenceFlowGraph | null;
}

export function SequenceFlowDiagram({ data }: Props) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <div className="p-5 bg-slate-900/70 backdrop-blur-md rounded-xl border border-slate-800 flex items-center justify-center min-h-[260px] text-slate-500 text-xs font-mono">
        <GitFork className="w-5 h-5 mr-2 opacity-50" />
        No session call sequences detected yet. Markov state transitions will appear as real traffic is ingested.
      </div>
    );
  }

  // Filter links by selected node if any
  const displayedLinks = selectedNode
    ? data.links.filter((l) => l.source === selectedNode || l.target === selectedNode)
    : data.links;

  return (
    <div className="p-5 bg-slate-900/70 backdrop-blur-md rounded-xl border border-slate-800 flex flex-col h-full">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <GitFork className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-mono">
              Call Chain Sequence Flow & Markov Attack Graph
            </h4>
            <p className="text-xs text-slate-400">
              Session behavioral transitions: Normal flow vs Anomalous paths (Red Glow)
            </p>
          </div>
        </div>

        {selectedNode && (
          <button
            onClick={() => setSelectedNode(null)}
            className="text-xs font-mono text-cyan-400 hover:underline"
          >
            Clear Selection ({selectedNode})
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-1">
        {/* Discovered Endpoint State Nodes */}
        <div className="lg:col-span-1 space-y-2 font-mono text-xs overflow-y-auto max-h-[300px] pr-1">
          <div className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider mb-2">
            Discovered Call Chain Nodes ({data.nodes.length})
          </div>
          {data.nodes.map((node) => {
            const isSelected = selectedNode === node.id;
            const hasAnomalies = node.anomaly_count > 0;
            return (
              <div
                key={node.id}
                onClick={() => setSelectedNode(isSelected ? null : node.id)}
                className={`p-2.5 rounded-lg border transition-all cursor-pointer flex items-center justify-between ${
                  isSelected
                    ? 'bg-purple-950/40 border-purple-500 shadow-md shadow-purple-900/20'
                    : hasAnomalies
                    ? 'bg-slate-900/80 border-rose-500/40 hover:border-rose-500'
                    : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="truncate pr-2">
                  <div className="text-slate-200 font-semibold truncate hover:text-cyan-400">
                    {node.label}
                  </div>
                  <div className="text-[10px] text-slate-400">
                    {node.call_count} interactions
                  </div>
                </div>

                {hasAnomalies && (
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-rose-500/20 text-rose-400 border border-rose-500/30 flex items-center gap-1 font-bold">
                    <ShieldAlert className="w-3 h-3" />
                    {node.anomaly_count}
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Transition Links Flowchart / Sankey representation */}
        <div className="lg:col-span-2 p-4 bg-slate-950/60 rounded-xl border border-slate-800/80 overflow-y-auto max-h-[300px]">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-3 flex items-center justify-between">
            <span>Observed Sequence Transitions ({displayedLinks.length})</span>
            <span className="text-purple-400 font-semibold">Markov Transition Probabilities</span>
          </div>

          <div className="space-y-2.5 font-mono text-xs">
            {displayedLinks.length === 0 ? (
              <div className="text-slate-500 text-center py-8">
                No direct transition paths recorded for this node.
              </div>
            ) : (
              displayedLinks.map((link, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg border flex items-center justify-between transition-all ${
                    link.is_anomalous
                      ? 'bg-rose-950/30 border-rose-500/60 shadow-sm shadow-rose-950/30'
                      : 'bg-slate-900/70 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate flex-1">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 text-[11px] truncate max-w-[140px]">
                      {link.source}
                    </span>
                    <ArrowRight
                      className={`w-4 h-4 shrink-0 ${
                        link.is_anomalous ? 'text-rose-400 animate-pulse' : 'text-slate-500'
                      }`}
                    />
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] truncate max-w-[140px] ${
                        link.is_anomalous
                          ? 'bg-rose-900/40 text-rose-300 font-semibold border border-rose-500/40'
                          : 'bg-slate-800 text-slate-200'
                      }`}
                    >
                      {link.target}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 shrink-0 pl-2">
                    <span className="text-[11px] text-slate-400">
                      Weight: <span className="text-slate-200 font-bold">{link.value}</span>
                    </span>
                    {link.is_anomalous ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40">
                        Anomalous Chain
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Verified Flow
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
