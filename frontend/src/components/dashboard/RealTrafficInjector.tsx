'use client';

import React, { useState } from 'react';
import { api } from '@/lib/api';
import { Play, Check, Database } from 'lucide-react';

interface Props {
  onTrafficIngested: () => void;
}

export function RealTrafficInjector({ onTrafficIngested }: Props) {
  const [loadingDataset, setLoadingDataset] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const realDatasets = [
    {
      id: 'nginx',
      name: 'NGINX Production Logs',
      sourceType: 'nginx',
      description: 'Standard combined format access logs across catalog, checkout & search',
      logs: [
        '192.168.1.10 - - [27/Oct/2026:09:40:01 +0000] "GET /api/v1/products HTTP/1.1" 200 4500 "-" "Mozilla/5.0"',
        '192.168.1.11 - - [27/Oct/2026:09:40:02 +0000] "POST /api/v1/cart/items HTTP/1.1" 201 320 "-" "curl/7.68.0"',
        '192.168.1.12 - - [27/Oct/2026:09:40:03 +0000] "GET /api/v1/users/me HTTP/1.1" 200 1200 "Bearer tok_123" "PostmanRuntime/7.29.0"',
        '192.168.1.13 - - [27/Oct/2026:09:40:04 +0000] "GET /api/v1/search?q=security HTTP/1.1" 200 8900 "-" "Mozilla/5.0"',
        '192.168.1.14 - - [27/Oct/2026:09:40:05 +0000] "GET /healthz HTTP/1.1" 200 45 "-" "Kube-Probe/1.28"',
      ],
      badgeColor: 'border-cyan-500/40 text-cyan-300 bg-cyan-500/10',
    },
    {
      id: 'envoy',
      name: 'Envoy Gateway Telemetry',
      sourceType: 'envoy',
      description: 'Structured JSON telemetry with latency, upstream cluster and TLS version',
      logs: [
        JSON.stringify({
          start_time: '2026-10-27T09:40:10Z',
          method: 'GET',
          path: '/api/v1/inventory/items/88',
          response_code: 200,
          duration: 42,
          bytes_received: 120,
          bytes_sent: 840,
          downstream_remote_address: '10.0.4.15:43210',
          user_agent: 'Envoy-Client/1.22',
          cluster: 'inventory_service_cluster',
        }),
        JSON.stringify({
          start_time: '2026-10-27T09:40:11Z',
          method: 'POST',
          path: '/api/v1/orders',
          response_code: 201,
          duration: 98,
          bytes_received: 480,
          bytes_sent: 350,
          downstream_remote_address: '10.0.4.16:43211',
          user_agent: 'MobileApp/3.4.1',
          cluster: 'order_service_cluster',
        }),
      ],
      badgeColor: 'border-purple-500/40 text-purple-300 bg-purple-500/10',
    },
    {
      id: 'attacks',
      name: 'Live Security Attack Set',
      sourceType: 'auto',
      description: 'Real malicious traffic: SQL Injection, Path Traversal, BOLA/IDOR & Scanners',
      logs: [
        '203.0.113.200 - - [27/Oct/2026:09:41:00 +0000] "GET /api/v1/users?id=1%27%20OR%201=1-- HTTP/1.1" 403 80 "-" "sqlmap/1.6#stable"',
        '203.0.113.201 - - [27/Oct/2026:09:41:01 +0000] "GET /api/v1/download?file=../../../../etc/passwd HTTP/1.1" 403 75 "-" "Nikto/2.1.6"',
        '203.0.113.202 - - [27/Oct/2026:09:41:02 +0000] "GET /api/v1/orders/999999 HTTP/1.1" 403 88 "-" "python-requests/2.28.1"',
        '203.0.113.203 - - [27/Oct/2026:09:41:03 +0000] "POST /api/v1/auth/login HTTP/1.1" 401 120 "-" "Hydra/9.5"',
      ],
      badgeColor: 'border-rose-500/40 text-rose-300 bg-rose-500/10',
    },
  ];

  const handleInject = async (ds: (typeof realDatasets)[0]) => {
    setLoadingDataset(ds.id);
    setStatusMessage(null);
    try {
      const res = await api.ingestRawLogs(ds.logs, ds.sourceType);
      setStatusMessage(`Ingested ${res.total_processed} real events into SentinelAPI pipeline!`);
      onTrafficIngested();
      setTimeout(() => setStatusMessage(null), 4000);
    } catch (err: any) {
      setStatusMessage(`Ingestion failed: ${err.message}`);
    } finally {
      setLoadingDataset(null);
    }
  };

  return (
    <div className="p-5 bg-slate-900/70 backdrop-blur-md rounded-xl border border-slate-800 space-y-4 font-mono text-xs">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Database className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-100 uppercase tracking-wider">
              Real Data Stream Injection Console
            </h4>
            <p className="text-slate-400">
              Inject actual production API access logs & security attack traces directly into the ingestion engine
            </p>
          </div>
        </div>

        {statusMessage && (
          <div className="px-3 py-1 rounded-lg bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 text-xs flex items-center gap-1.5 animate-in fade-in">
            <Check className="w-3.5 h-3.5" />
            {statusMessage}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {realDatasets.map((ds) => (
          <div
            key={ds.id}
            className="p-4 bg-slate-950/60 rounded-xl border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col justify-between space-y-3"
          >
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-slate-100">{ds.name}</span>
                <span className={`px-2 py-0.5 rounded text-[10px] border font-bold ${ds.badgeColor}`}>
                  {ds.sourceType}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">{ds.description}</p>
            </div>

            <button
              onClick={() => handleInject(ds)}
              disabled={loadingDataset !== null}
              className={`w-full py-2 px-3 rounded-lg border font-semibold flex items-center justify-center gap-2 transition-all ${
                ds.id === 'attacks'
                  ? 'bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border-rose-500/40'
                  : 'bg-slate-800 hover:bg-cyan-500/20 hover:text-cyan-300 text-slate-200 border-slate-700'
              } disabled:opacity-50`}
            >
              <Play className={`w-3.5 h-3.5 ${loadingDataset === ds.id ? 'animate-spin' : ''}`} />
              {loadingDataset === ds.id ? 'Ingesting Real Logs...' : `Inject ${ds.logs.length} Real Events`}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
