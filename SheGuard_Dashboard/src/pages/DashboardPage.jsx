import { AnimatePresence, motion } from "framer-motion";
import { useMemo, useState, useEffect } from "react";
import { Radio, Sparkles, MapPin, AlertTriangle, Users, Zap, Cpu, Camera, Activity, ShieldCheck } from "lucide-react";
import { stagger } from "../animations/variants";
import EmptyState from "../components/EmptyState";
import FilterBar from "../components/FilterBar";
import IncidentArticleCard from "../components/IncidentArticleCard";
import IncidentDetailPage from "./IncidentDetailPage";
import DetailMap from "../components/DetailMap";
import { useEmergencySessions } from "../hooks/useEmergencySessions";
import { formatTime } from "../lib/incidents";

export default function DashboardPage() {
  const {
    emergencySessions,
    activeCount,
    highRiskCount,
    trackingSessions,
    selectedSessionId,
    selectedSession,
    selectSession,
    notifications,
    unreadCount,
    realtimeStatus,
    backendError,
    isLoading,
    refreshIncidents,
  } = useEmergencySessions();

  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [confidenceFilter, setConfidenceFilter] = useState("all");
  const [timeFilter, setTimeFilter] = useState("all");
  const [mapCenter, setMapCenter] = useState([20.5937, 78.9629]);
  const [mapZoom, setMapZoom] = useState(5);

  // Get all incidents from emergency sessions
  const allIncidents = useMemo(() => {
    const incidents = [];
    emergencySessions.forEach((session) => {
      if (session.latestIncident) {
        incidents.push({
          ...session.latestIncident,
          sessionId: session.sessionId,
          sessionStatus: session.status,
          sessionThreatLevel: session.threatLevel,
          sessionThreatScore: session.threatScore,
          victimName: session.fullName,
          maskedPhone: session.maskedPhone,
          triggerSource: session.triggerSource,
        });
      }
    });
    return incidents.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }, [emergencySessions]);

  const filteredIncidents = useMemo(() => {
    const search = query.trim().toLowerCase();
    const minimumConfidence = confidenceFilter === "all" ? 0 : Number(confidenceFilter);
    const hours = timeFilter === "all" ? null : Number(timeFilter);
    const now = Date.now();

    return allIncidents.filter((incident) => {
      const confidence = Number(incident.confidence) <= 1 ? Number(incident.confidence) * 100 : Number(incident.confidence) || 0;
      const incidentTime = new Date(incident.timestamp).getTime();
      const matchesSearch =
        !search ||
        [incident.address, incident.title, incident.description, incident.emergencyStatus, incident.id, incident.sessionId, incident.victimName]
          .some((value) => String(value || "").toLowerCase().includes(search));
      const matchesConfidence = confidence >= minimumConfidence;
      const matchesTime = !hours || (Number.isFinite(incidentTime) && now - incidentTime <= hours * 60 * 60 * 1000);
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "active" && !incident.isResolved) ||
        (statusFilter === "resolved" && incident.isResolved) ||
        (statusFilter === "live" && !incident.isResolved) ||
        (statusFilter === "high" && incident.severity === "critical");
      return matchesSearch && matchesConfidence && matchesTime && matchesStatus;
    });
  }, [allIncidents, confidenceFilter, query, statusFilter, timeFilter]);

  // Focus map on selected session
  useEffect(() => {
    if (selectedSession?.latestLocation?.latitude && selectedSession?.latestLocation?.longitude) {
      setMapCenter([selectedSession.latestLocation.latitude, selectedSession.latestLocation.longitude]);
      setMapZoom(15);
    }
  }, [selectedSession]);

  const getRiskColor = (level) => {
    switch (level) {
      case "EMERGENCY":
        return "text-red-400 bg-red-400/20 border-red-400/30";
      case "CRITICAL":
        return "text-orange-400 bg-orange-400/20 border-orange-400/30";
      case "HIGH":
        return "text-yellow-400 bg-yellow-400/20 border-yellow-400/30";
      case "WARNING":
        return "text-blue-400 bg-blue-400/20 border-blue-400/30";
      default:
        return "text-green-400 bg-green-400/20 border-green-400/30";
    }
  };

  return (
    <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8">
      {/* Top Header Section */}
      <section className="mx-auto max-w-7xl mb-6">
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_400px]"
        >
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-alert-500/30 bg-alert-500/12 px-4 py-2 text-xs font-black uppercase tracking-[0.16em] text-red-100">
              <span className="h-2 w-2 rounded-full bg-alert-500 shadow-[0_0_16px_rgba(255,46,63,.9)] animate-sos-pulse" />
              SHEGUARD AI+ POLICE COMMAND CENTER
            </div>
            <h1 className="mt-4 max-w-5xl text-4xl font-black leading-[0.92] tracking-tight text-white sm:text-5xl lg:text-6xl">
              Active Emergency Operations
            </h1>
            <p className="mt-3 max-w-2xl text-lg leading-7 text-slate-300">
              Real-time monitoring of all active emergency sessions across the SheGuard network.
            </p>
          </div>

          {/* Quick Stats Card */}
          <div className="rounded-[1.7rem] border border-white/10 bg-white/[0.055] p-5 shadow-panel backdrop-blur-2xl">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Active Emergencies</p>
                  <p className="mt-1 text-3xl font-black text-red-400">{activeCount}</p>
                </div>
                <div className="flex h-14 w-14 items-center justify-center rounded-full border border-red-500/35 bg-red-500/15 text-red-500 shadow-glow">
                  <ShieldCheck className="h-6 w-6" />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">High Risk</p>
                  <p className="mt-1 text-3xl font-black text-amber-400">{highRiskCount}</p>
                </div>
                <div className="flex h-14 w-14 items-center justify-center rounded-full border border-amber-500/35 bg-amber-500/15 text-amber-500 shadow-glow">
                  <AlertTriangle className="h-6 w-6" />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Tracking Sessions</p>
                  <p className="mt-1 text-3xl font-black text-blue-400">{trackingSessions.length}</p>
                </div>
                <div className="flex h-14 w-14 items-center justify-center rounded-full border border-blue-500/35 bg-blue-500/15 text-blue-500 shadow-glow">
                  <MapPin className="h-6 w-6" />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Realtime</p>
                  <p className="mt-1 text-3xl font-black text-cyan-400">
                    {realtimeStatus === "connected" ? "LIVE" : realtimeStatus.toUpperCase()}
                  </p>
                </div>
                <div className={`flex h-14 w-14 items-center justify-center rounded-full border ${
                  realtimeStatus === "connected"
                    ? "border-cyan-500/35 bg-cyan-500/15 text-cyan-500"
                    : realtimeStatus === "reconnecting"
                    ? "border-amber-500/35 bg-amber-500/15 text-amber-500"
                    : "border-red-500/35 bg-red-500/15 text-red-500"
                } shadow-glow`}>
                  <Zap className="h-6 w-6" />
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Active Emergencies Command Panel */}
      {emergencySessions.length > 0 && (
        <section className="mx-auto max-w-7xl mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Active Emergencies</p>
              <h2 className="mt-1 text-2xl font-black tracking-tight text-white">
                {emergencySessions.length} Session{emergencySessions.length !== 1 ? "s" : ""} Active
              </h2>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {emergencySessions.map((session) => (
              <motion.div
                key={session.sessionId}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className={`rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-4 backdrop-blur-xl transition cursor-pointer ${
                  selectedSessionId === session.sessionId ? "border-alert-500/50 bg-alert-500/5 ring-1 ring-alert-500/20" : "hover:border-alert-500/30"
                }`}
                onClick={() => selectSession(session.sessionId)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-white truncate">{session.fullName}</span>
                      <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em] ${
                        session.status === "ACTIVE" ? "border-red-500/50 bg-red-500/15 text-red-400" :
                        session.status === "ACKNOWLEDGED" ? "border-amber-500/50 bg-amber-500/15 text-amber-400" :
                        session.status === "RESPONDING" ? "border-blue-500/50 bg-blue-500/15 text-blue-400" :
                        "border-emerald-500/50 bg-emerald-500/15 text-emerald-400"
                      }`}>
                        {session.status}
                      </span>
                      <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em] ${getRiskColor(session.threatLevel)}`}>
                        {session.threatLevel}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">Trigger: {session.triggerSource}</p>
                    <p className="text-xs text-slate-500 mt-0.5 font-mono">Session: {session.sessionId}</p>
                    <div className="mt-2 flex items-center gap-4 text-xs text-slate-400">
                      <span className="flex items-center gap-1">
                        <Zap className="h-3 w-3" />
                        Threat: {session.threatScore}
                      </span>
                      <span className="flex items-center gap-1">
                        <Users className="h-3 w-3" />
                        {session.deviceStatus}
                      </span>
                    </div>
                    {session.latestLocation?.latitude && (
                      <p className="mt-2 text-xs font-mono text-slate-300">
                        {session.latestLocation.latitude.toFixed(6)}, {session.latestLocation.longitude.toFixed(6)}
                      </p>
                    )}
                    <p className="mt-1 text-xs text-slate-500">
                      Last update: {formatTime(session.locationUpdatedAt)}
                    </p>
                    {session.nearbyCameras?.length > 0 && (
                      <p className="mt-2 text-xs text-slate-400 flex items-center gap-1">
                        <Camera className="h-3 w-3" />
                        {session.nearbyCameras.length} CCTV nearby (closest: {session.nearbyCameras[0].distance}m)
                      </p>
                    )}
                  </div>
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/5 text-slate-400 shrink-0">
                    <MapPin className="h-4 w-4" />
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </section>
      )}

      {/* Live Map + Incident Feed */}
      <section className="mx-auto max-w-7xl">
        <FilterBar
          query={query}
          setQuery={setQuery}
          statusFilter={statusFilter}
          setStatusFilter={setStatusFilter}
          confidenceFilter={confidenceFilter}
          setConfidenceFilter={setConfidenceFilter}
          timeFilter={timeFilter}
          setTimeFilter={setTimeFilter}
        />

        {backendError && (
          <div className="mb-5 rounded-2xl border border-alert-500/30 bg-alert-500/12 px-4 py-3 text-sm text-red-100">
            Backend connection warning: {backendError}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,.6fr)]">
          {/* Live Map */}
          <div className="relative">
            <div className="map-shell h-[500px] overflow-hidden rounded-[1.4rem] border border-white/10 bg-command-900">
              <DetailMap
                incidents={allIncidents}
                trackingSessions={trackingSessions}
                selectedSession={selectedSession}
                center={mapCenter}
                zoom={mapZoom}
                onViewportChange={(center, zoom) => {
                  setMapCenter(center);
                  setMapZoom(zoom);
                }}
              />
            </div>
            
            {/* Map controls */}
            <div className="absolute bottom-4 right-4 flex flex-col gap-2">
              <button
                onClick={() => {
                  if (selectedSession?.latestLocation?.latitude) {
                    setMapCenter([selectedSession.latestLocation.latitude, selectedSession.latestLocation.longitude]);
                    setMapZoom(15);
                  }
                }}
                disabled={!selectedSession?.latestLocation?.latitude}
                className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-command-950/80 backdrop-blur-xl text-white hover:bg-white/10 transition disabled:opacity-50 disabled:cursor-not-allowed"
                title="Focus selected session"
              >
                <MapPin className="h-5 w-5" />
              </button>
              <button
                onClick={refreshIncidents}
                className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-command-950/80 backdrop-blur-xl text-white hover:bg-white/10 transition"
                title="Refresh"
              >
                <Sparkles className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Incident Feed */}
          <div className="space-y-4 max-h-[500px] overflow-y-auto thin-scrollbar">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Live Incident Feed</p>
                <h2 className="mt-1 text-xl font-black tracking-tight text-white">
                  {filteredIncidents.length} Incident{filteredIncidents.length !== 1 ? "s" : ""}
                </h2>
              </div>
              <div className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/[0.055] px-4 py-2 text-sm text-slate-300 sm:flex">
                <Sparkles className="h-4 w-4 text-alert-500" />
                Live updates
              </div>
            </div>

            <AnimatePresence mode="wait">
              {isLoading ? (
                <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid gap-4 md:grid-cols-2">
                  {[1, 2, 3].map((item) => (
                    <div key={item} className="h-[300px] animate-pulse rounded-[1.4rem] border border-white/10 bg-white/[0.055]" />
                  ))}
                </motion.div>
              ) : filteredIncidents.length ? (
                <motion.div key="feed" variants={stagger} initial="hidden" animate="show" className="space-y-4">
                  {filteredIncidents.map((incident, index) => (
                    <IncidentArticleCard
                      key={incident.id}
                      incident={incident}
                      featured={false}
                      onView={() => selectSession(incident.sessionId)}
                    />
                  ))}
                </motion.div>
              ) : (
                <div className="text-center py-12">
                  <EmptyState />
                </div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </section>

      {/* Selected Session Detail Overlay */}
      <IncidentDetailPage incident={selectedSession?.latestIncident} onClose={() => selectSession(null)} />
    </main>
  );
}
