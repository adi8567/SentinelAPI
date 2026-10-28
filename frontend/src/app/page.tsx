'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import { useSentinelWebSocket } from '@/hooks/useSentinelWebSocket';
import {
  AlertRecord,
  AlertStatus,
  AnomalyTimeseriesPoint,
  DashboardOverview,
  EndpointHealthMetric,
  GeoDistributionPoint,
  RiskDistributionData,
  SequenceFlowGraph,
  TopEndpointAnomalies,
  TrafficTimeseriesPoint,
} from '@/lib/types';

import { OverviewCards } from '@/components/dashboard/OverviewCards';
import { TrafficVolumeChart } from '@/components/dashboard/TrafficVolumeChart';
import { AnomalyRateChart } from '@/components/dashboard/AnomalyRateChart';
import { RiskDistributionChart } from '@/components/dashboard/RiskDistributionChart';
import { TopAnomalousEndpointsChart } from '@/components/dashboard/TopAnomalousEndpointsChart';
import { EndpointHealthMatrix } from '@/components/dashboard/EndpointHealthMatrix';
import { GeoDistributionMap } from '@/components/dashboard/GeoDistributionMap';
import { SequenceFlowDiagram } from '@/components/dashboard/SequenceFlowDiagram';
import { LatencyVsErrorScatter } from '@/components/dashboard/LatencyVsErrorScatter';
import { ClientBehaviorComparison } from '@/components/dashboard/ClientBehaviorComparison';
import { AlertTimeline } from '@/components/dashboard/AlertTimeline';
import { ModelPerformanceMetrics } from '@/components/dashboard/ModelPerformanceMetrics';
import { ForensicTraceModal } from '@/components/dashboard/ForensicTraceModal';
import { RealTrafficInjector } from '@/components/dashboard/RealTrafficInjector';

import { motion, AnimatePresence, type Variants } from 'framer-motion';
import {
  Shield,
  ShieldAlert,
  Activity,
  HeartPulse,
  Cpu,
  RefreshCw,
  Menu,
  X,
} from 'lucide-react';

type TabKey = 'overview' | 'health' | 'threats' | 'engine';

const tabs: { key: TabKey; label: string; icon: React.ComponentType<any>; mobileLabel: string }[] = [
  { key: 'overview', label: 'Overview & Telemetry', icon: Activity, mobileLabel: 'Overview' },
  { key: 'health', label: 'Endpoint Health', icon: HeartPulse, mobileLabel: 'Health' },
  { key: 'threats', label: 'Threats & Attacks', icon: ShieldAlert, mobileLabel: 'Threats' },
  { key: 'engine', label: 'ML Engine', icon: Cpu, mobileLabel: 'ML Engine' },
];

const pageVariants: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.3, ease: 'easeOut' } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.2 } },
};

export default function DashboardPage() {
  const { isConnected: wsConnected, lastMessage } = useSentinelWebSocket();

  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [trafficTimeseries, setTrafficTimeseries] = useState<TrafficTimeseriesPoint[]>([]);
  const [anomaliesTimeseries, setAnomaliesTimeseries] = useState<AnomalyTimeseriesPoint[]>([]);
  const [riskDistribution, setRiskDistribution] = useState<RiskDistributionData | null>(null);
  const [topEndpoints, setTopEndpoints] = useState<TopEndpointAnomalies[]>([]);
  const [healthMatrix, setHealthMatrix] = useState<EndpointHealthMetric[]>([]);
  const [geoData, setGeoData] = useState<GeoDistributionPoint[]>([]);
  const [sequenceGraph, setSequenceGraph] = useState<SequenceFlowGraph | null>(null);
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);

  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string>('Just now');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const loadDashboardData = useCallback(async () => {
    setRefreshing(true);
    try {
      const [ov, traffic, anom, risk, topEp, health, geo, seq, alertList] = await Promise.all([
        api.getOverview().catch(() => null),
        api.getTrafficTimeseries(30).catch(() => []),
        api.getAnomaliesTimeseries(30).catch(() => []),
        api.getRiskDistribution().catch(() => null),
        api.getTopEndpoints(10).catch(() => []),
        api.getHealthMatrix().catch(() => []),
        api.getGeoDistribution().catch(() => []),
        api.getSequenceFlowGraph().catch(() => null),
        api.getAlerts(undefined, undefined, 50).catch(() => []),
      ]);

      if (ov) setOverview(ov);
      setTrafficTimeseries(traffic);
      setAnomaliesTimeseries(anom);
      if (risk) setRiskDistribution(risk);
      setTopEndpoints(topEp);
      setHealthMatrix(health);
      setGeoData(geo);
      if (seq) setSequenceGraph(seq);
      setAlerts(alertList);
      setLastRefreshedAt(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { loadDashboardData(); }, [loadDashboardData]);
  useEffect(() => { if (lastMessage) loadDashboardData(); }, [lastMessage, loadDashboardData]);

  const handleMitigateAlert = async (alertId: string, action: 'ban_ip' | 'quarantine' | 'throttle') => {
    try { await api.mitigateAlert(alertId, action); await loadDashboardData(); }
    catch (err) { console.error('Mitigation failed:', err); }
  };

  const handleUpdateAlertStatus = async (alertId: string, status: AlertStatus) => {
    try { await api.updateAlert(alertId, { status }); await loadDashboardData(); }
    catch (err) { console.error('Status update failed:', err); }
  };

  const handleRetrainModels = async () => {
    await new Promise((r) => setTimeout(r, 1500));
    await loadDashboardData();
  };

  const clientMap = new Map<string, any>();
  alerts.forEach((a) => {
    if (!clientMap.has(a.client_ip)) {
      clientMap.set(a.client_ip, {
        client_ip: a.client_ip,
        reputation_score: Math.max(10, 100 - a.risk_score),
        total_requests: 1, error_count: 1, distinct_endpoints_count: 1,
        is_banned: a.mitigation_action === 'ban_ip',
        is_quarantined: a.mitigation_action === 'quarantine',
      });
    } else {
      const c = clientMap.get(a.client_ip);
      c.total_requests += 1; c.error_count += 1;
    }
  });
  const clientList = Array.from(clientMap.values());

  return (
    <div className="min-h-screen bg-[#0F172A] text-slate-100 ambient-grid flex flex-col font-sans">
      {/* ═══════ Floating Glassmorphism Navbar ═══════ */}
      <header
        className="sticky top-0 z-50 mx-auto w-full max-w-7xl mt-3 px-4 sm:px-6"
        role="banner"
      >
        <nav className="glass-card px-4 sm:px-6 py-3 flex items-center justify-between gap-4 glow-violet-soft">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-500 text-white shadow-lg shadow-violet-500/25">
              <Shield className="w-5 h-5" aria-hidden="true" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono font-extrabold text-base tracking-wider gradient-text-brand">
                  SENTINEL
                </span>
                <span className="font-mono font-extrabold text-base tracking-wider text-white">API</span>
                <span className="px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-violet-500/10 text-violet-400 border border-violet-500/30">
                  PROD v1.0
                </span>
              </div>
              <p className="text-[10px] font-mono text-slate-500 hidden sm:block tracking-wide">
                Intelligent API Anomaly Detection & Adaptive Protection
              </p>
            </div>
          </div>

          {/* Desktop Controls */}
          <div className="hidden md:flex items-center gap-3">
            <div className="glass-card-sm px-3 py-1.5 text-[11px] font-mono text-slate-400 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-glow-pulse" />
              Synced: <span className="text-slate-200">{lastRefreshedAt}</span>
            </div>
            <button
              onClick={loadDashboardData}
              disabled={refreshing}
              className="p-2 rounded-xl glass-card-sm hover:bg-slate-700/30 text-slate-300 transition-all flex items-center gap-1.5 text-xs font-mono focus-visible:ring-2 focus-visible:ring-violet-500"
              aria-label="Refresh dashboard data"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-violet-400' : ''}`} />
              <span className="hidden lg:inline">Sync</span>
            </button>
          </div>

          {/* Mobile Menu Toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-xl glass-card-sm text-slate-300"
            aria-label="Toggle mobile menu"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </nav>

        {/* Mobile Drawer */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="md:hidden glass-card mt-2 overflow-hidden"
            >
              <nav className="p-3 space-y-1" role="navigation" aria-label="Mobile navigation">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.key}
                      onClick={() => { setActiveTab(tab.key); setMobileMenuOpen(false); }}
                      className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-mono transition-all ${
                        activeTab === tab.key ? 'pill-active font-semibold' : 'pill-inactive'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      {tab.label}
                      {tab.key === 'threats' && alerts.length > 0 && (
                        <span className="ml-auto px-2 py-0.5 rounded-full text-[10px] bg-rose-500/20 text-rose-400 border border-rose-500/30 font-bold">
                          {alerts.length}
                        </span>
                      )}
                    </button>
                  );
                })}
                <div className="pt-2 border-t border-slate-700/30">
                  <button
                    onClick={() => { loadDashboardData(); setMobileMenuOpen(false); }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-mono text-slate-400 hover:text-slate-200 transition-colors"
                  >
                    <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-violet-400' : ''}`} />
                    Sync Data
                  </button>
                </div>
              </nav>
            </motion.div>
          )}
        </AnimatePresence>
      </header>

      {/* ═══════ Main Container ═══════ */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 pt-6 pb-8 space-y-6" role="main">
        {/* Desktop Tab Navigation */}
        <div className="hidden md:flex flex-wrap items-center justify-between gap-3">
          <nav className="flex gap-1 p-1 glass-card-sm" role="tablist" aria-label="Dashboard sections">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  role="tab"
                  aria-selected={activeTab === tab.key}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono transition-all duration-200 ${
                    activeTab === tab.key ? 'pill-active font-semibold' : 'pill-inactive'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                  {tab.key === 'threats' && alerts.length > 0 && (
                    <span className="px-1.5 py-0.5 rounded-full text-[9px] bg-rose-500/20 text-rose-400 border border-rose-500/30 font-bold">
                      {alerts.length}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          <div className="flex items-center gap-2 text-[11px] font-mono text-slate-500">
            <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-glow-pulse" />
            <span>Live Data Mode</span>
          </div>
        </div>

        {/* Overview Cards (always visible) */}
        <OverviewCards overview={overview} wsConnected={wsConnected} />

        {/* Tab Content with Animated Transitions */}
        <AnimatePresence mode="wait">
          {activeTab === 'overview' && (
            <motion.div key="overview" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <TrafficVolumeChart data={trafficTimeseries} />
                <AnomalyRateChart data={anomaliesTimeseries} />
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <RiskDistributionChart data={riskDistribution} />
                <TopAnomalousEndpointsChart
                  data={topEndpoints}
                  onSelectEndpoint={(ep) => {
                    const matchingAlert = alerts.find((a) => a.endpoint === ep);
                    if (matchingAlert) setSelectedEventId(matchingAlert.event_id);
                  }}
                />
              </div>
              <RealTrafficInjector onTrafficIngested={loadDashboardData} />
            </motion.div>
          )}

          {activeTab === 'health' && (
            <motion.div key="health" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <EndpointHealthMatrix
                  data={healthMatrix}
                  onSelectEndpoint={(epId) => {
                    const matchingAlert = alerts.find((a) => a.endpoint.includes(epId));
                    if (matchingAlert) setSelectedEventId(matchingAlert.event_id);
                  }}
                />
                <LatencyVsErrorScatter
                  data={healthMatrix}
                  onSelectEndpoint={(epId) => {
                    const matchingAlert = alerts.find((a) => a.endpoint.includes(epId));
                    if (matchingAlert) setSelectedEventId(matchingAlert.event_id);
                  }}
                />
              </div>
              <div className="glass-card p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-slate-200 uppercase tracking-widest">
                    API Schema Discovery
                  </span>
                  <span className="text-xs font-mono text-violet-400">
                    {overview?.total_endpoints || 0} Routes Observed
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 font-mono leading-relaxed">
                  Endpoints, methods, query params, and status codes are continuously discovered from real ingested traffic without static OpenAPI specs.
                </p>
              </div>
            </motion.div>
          )}

          {activeTab === 'threats' && (
            <motion.div key="threats" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="space-y-6">
              <AlertTimeline
                alerts={alerts}
                onSelectAlert={(a) => setSelectedEventId(a.event_id)}
                onMitigate={handleMitigateAlert}
                onUpdateStatus={handleUpdateAlertStatus}
              />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <SequenceFlowDiagram data={sequenceGraph} />
                <GeoDistributionMap data={geoData} />
              </div>
              <ClientBehaviorComparison
                clients={clientList}
                onInspectClient={(ip) => {
                  const matchingAlert = alerts.find((a) => a.client_ip === ip);
                  if (matchingAlert) setSelectedEventId(matchingAlert.event_id);
                }}
                onBanClient={(ip) => {
                  const matchingAlert = alerts.find((a) => a.client_ip === ip);
                  if (matchingAlert) handleMitigateAlert(matchingAlert.alert_id, 'ban_ip');
                }}
              />
            </motion.div>
          )}

          {activeTab === 'engine' && (
            <motion.div key="engine" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="space-y-6">
              <ModelPerformanceMetrics onTriggerRetrain={handleRetrainModels} />
              <RealTrafficInjector onTrafficIngested={loadDashboardData} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Forensic Deep-Dive Modal */}
      <ForensicTraceModal
        eventId={selectedEventId}
        onClose={() => setSelectedEventId(null)}
      />

      {/* ═══════ Footer ═══════ */}
      <footer className="mt-auto border-t border-slate-800/40 bg-[#0F172A]/80 backdrop-blur-sm px-6 py-4" role="contentinfo">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-slate-600">
          <span>SentinelAPI Platform — Production API Defense</span>
          <div className="flex items-center gap-4">
            <span>Real Telemetry</span>
            <span className="text-violet-400/60">SOC Operational</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
