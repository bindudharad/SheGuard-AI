import { useEffect, useMemo, useState } from "react";
import { BarChart3, TrendingUp, TrendingDown, AlertTriangle, MapPin, Users, Camera, Clock, ShieldCheck, Target } from "lucide-react";
import { motion } from "framer-motion";
import { useIncidents } from "../hooks/useIncidents";
import { formatTime } from "../lib/incidents";

export default function AnalyticsPage() {
  const { incidents, isLoading, error, refresh } = useIncidents();

  const analytics = useMemo(() => {
    if (!incidents.length) return null;

    const total = incidents.length;
    const active = incidents.filter((i) => !i.isResolved).length;
    const resolved = incidents.filter((i) => i.isResolved).length;
    const highRisk = incidents.filter((i) => i.severity === "critical" || i.severity === "high").length;
    
    const threatScores = incidents.map((i) => i.threat_score || 0).filter((s) => s > 0);
    const avgThreatScore = threatScores.length ? Math.round(threatScores.reduce((a, b) => a + b, 0) / threatScores.length) : 0;
    
    const confidences = incidents.map((i) => i.confidence || 0).filter((c) => c > 0);
    const avgConfidence = confidences.length ? Math.round(confidences.reduce((a, b) => a + b, 0) / confidences.length * 100) : 0;

    // Incidents by type
    const byType = incidents.reduce((acc, i) => {
      const type = i.incidentType || i.type || "Unknown";
      acc[type] = (acc[type] || 0) + 1;
      return acc;
    }, {});

    // Incidents by threat level
    const byThreat = incidents.reduce((acc, i) => {
      const level = i.threat_level || i.severity || "UNKNOWN";
      acc[level] = (acc[level] || 0) + 1;
      return acc;
    }, {});

    // Incidents by camera
    const byCamera = incidents.reduce((acc, i) => {
      const cam = i.camera_id || "Unknown";
      acc[cam] = (acc[cam] || 0) + 1;
      return acc;
    }, {});

    // Incidents over time (last 24 hours in 2-hour buckets)
    const now = Date.now();
    const buckets = Array.from({ length: 12 }, (_, i) => ({
      start: now - (12 - i) * 2 * 60 * 60 * 1000,
      end: now - (11 - i) * 2 * 60 * 60 * 1000,
      count: 0,
    }));
    
    incidents.forEach((i) => {
      const time = new Date(i.timestamp).getTime();
      const bucket = buckets.find((b) => time >= b.start && time < b.end);
      if (bucket) bucket.count++;
    });

    // Unique users
    const uniqueUsers = new Set(incidents.map((i) => i.userId || i.user_id).filter(Boolean)).size;

    // Sessions
    const uniqueSessions = new Set(incidents.map((i) => i.sessionId).filter(Boolean)).size;

    return {
      total,
      active,
      resolved,
      highRisk,
      avgThreatScore,
      avgConfidence,
      uniqueUsers,
      uniqueSessions,
      byType,
      byThreat,
      byCamera,
      overTime: buckets,
    };
  }, [incidents]);

  if (isLoading) {
    return (
      <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-40 animate-pulse rounded-[1.4rem] border border-white/10 bg-white/[0.055]" />
            ))}
          </div>
        </div>
      </main>
    );
  }

  if (!analytics) {
    return (
      <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl text-center py-20">
          <BarChart3 className="h-16 w-16 mx-auto text-slate-600" />
          <h2 className="mt-6 text-2xl font-black text-white">No Data Available</h2>
          <p className="mt-2 text-slate-400">Incidents will appear here once data is loaded</p>
        </div>
      </main>
    );
  }

  const { total, active, resolved, highRisk, avgThreatScore, avgConfidence, uniqueUsers, uniqueSessions, byType, byThreat, byCamera, overTime } = analytics;

  const statCards = [
    { label: "Total Incidents", value: total, icon: Target, color: "text-white" },
    { label: "Active Emergencies", value: active, icon: AlertTriangle, color: "text-red-400" },
    { label: "Resolved", value: resolved, icon: ShieldCheck, color: "text-emerald-400" },
    { label: "High Risk", value: highRisk, icon: TrendingUp, color: "text-amber-400" },
    { label: "Avg Threat Score", value: `${avgThreatScore}/100`, icon: AlertTriangle, color: "text-orange-400" },
    { label: "Avg Confidence", value: `${avgConfidence}%`, icon: Target, color: "text-cyan-400" },
    { label: "Unique Victims", value: uniqueUsers, icon: Users, color: "text-blue-400" },
    { label: "Emergency Sessions", value: uniqueSessions, icon: Clock, color: "text-violet-400" },
  ];

  return (
    <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8">
      <section className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/12 px-4 py-2 text-xs font-black uppercase tracking-[0.16em] text-violet-100">
            <BarChart3 className="h-4 w-4" />
            Analytics Dashboard
          </div>
          <h1 className="mt-4 text-4xl font-black tracking-tight text-white sm:text-5xl">
            Incident Analytics & Intelligence
          </h1>
          <p className="mt-2 text-lg text-slate-300">
            Real-time analytics from live incident data across all emergency sessions
          </p>
        </div>

        {/* Key Metrics Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
          {statCards.map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">{stat.label}</p>
                  <p className="mt-2 text-3xl font-black {stat.color}">{stat.value}</p>
                </div>
                <div className={`flex h-12 w-12 items-center justify-center rounded-full bg-white/5 ${stat.color}/20`}>
                  <stat.icon className="h-6 w-6" />
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Charts Section */}
        <div className="grid gap-6 lg:grid-cols-2 mb-8">
          {/* Incidents by Type */}
          <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
            <h3 className="text-lg font-black text-white mb-4">Incidents by Type</h3>
            <div className="space-y-3">
              {Object.entries(byType)
                .sort(([, a], [, b]) => b - a)
                .map(([type, count]) => (
                  <div key={type} className="flex items-center gap-3">
                    <div className="w-32 text-sm text-slate-300 truncate">{type}</div>
                    <div className="flex-1 h-6 bg-white/10 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-alert-500 rounded-full transition-all duration-500"
                        style={{ width: `${(count / total) * 100}%` }}
                      />
                    </div>
                    <span className="w-12 text-right font-bold text-white">{count}</span>
                  </div>
                ))}
            </div>
          </div>

          {/* Incidents by Threat Level */}
          <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
            <h3 className="text-lg font-black text-white mb-4">Incidents by Threat Level</h3>
            <div className="space-y-3">
              {Object.entries(byThreat)
                .sort(([, a], [, b]) => b - a)
                .map(([level, count]) => {
                  const threatColor =
                    level === "CRITICAL" || level === "critical"
                      ? "bg-red-500"
                      : level === "HIGH" || level === "high"
                      ? "bg-amber-500"
                      : level === "MEDIUM" || level === "medium"
                      ? "bg-yellow-500"
                      : level === "LOW" || level === "low"
                      ? "bg-green-500"
                      : "bg-slate-500";
                  return (
                    <div key={level} className="flex items-center gap-3">
                      <div className="w-32 text-sm text-slate-300 capitalize">{level.toLowerCase()}</div>
                      <div className="flex-1 h-6 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${threatColor} rounded-full transition-all duration-500`}
                          style={{ width: `${(count / total) * 100}%` }}
                        />
                      </div>
                      <span className="w-12 text-right font-bold text-white">{count}</span>
                    </div>
                  );
                })}
            </div>
          </div>

          {/* Incidents Over Time */}
          <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl lg:col-span-2">
            <h3 className="text-lg font-black text-white mb-4">Incidents Over Time (Last 24 Hours)</h3>
            <div className="h-64 flex items-end gap-2">
              {overTime.map((bucket, index) => (
                <div key={index} className="flex-1 flex flex-col items-center">
                  <div
                    className="w-full bg-alert-500/50 rounded-t transition-all duration-300 hover:bg-alert-500"
                    style={{ height: `${Math.max(4, (bucket.count / Math.max(1, ...overTime.map((b) => b.count))) * 100)}%` }}
                    title={`${bucket.count} incidents`}
                  />
                  <span className="text-xs text-slate-500 mt-2">
                    {new Date(bucket.start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Top Cameras */}
          <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
            <h3 className="text-lg font-black text-white mb-4">Top Cameras by Incidents</h3>
            <div className="space-y-3">
              {Object.entries(byCamera)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 10)
                .map(([camera, count]) => (
                  <div key={camera} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-orange-500/20 text-orange-400 text-xs font-bold">
                        CCTV
                      </div>
                      <span className="text-sm text-white truncate max-w-[150px]">{camera}</span>
                    </div>
                    <span className="font-bold text-white">{count}</span>
                  </div>
                ))}
            </div>
          </div>
        </div>

        {/* Data Quality Note */}
        <div className="rounded-[1.4rem] border border-amber-500/30 bg-amber-500/10 p-4 backdrop-blur-xl">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-400 mt-0.5 shrink-0" />
            <div>
              <p className="font-medium text-amber-100">Data Source</p>
              <p className="text-sm text-slate-300 mt-1">
                Analytics are computed from real-time incident data fetched from the backend.
                Metrics update automatically as new incidents arrive via polling and WebSocket events.
                {" "}
                <span className="text-slate-500">
                  (Last refresh: {new Date().toLocaleTimeString()})
                </span>
              </p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
