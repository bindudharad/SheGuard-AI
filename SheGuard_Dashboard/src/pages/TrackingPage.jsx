import { useEffect, useMemo, useState } from "react";
import { MapContainer, Marker, Popup, TileLayer, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import { MapPin, ArrowUpRight, RefreshCw, Radio, AlertTriangle, Battery, Zap } from "lucide-react";
import { motion } from "framer-motion";
import { useEmergencySessions } from "../hooks/useEmergencySessions";
import { getTrackingHistory, getLiveTracking } from "../services/api";
import { formatTime } from "../lib/incidents";
import StatusBadge from "../components/StatusBadge";

const victimIcon = L.divIcon({
  className: "",
  html: '<div class="relative flex h-10 w-10 items-center justify-center rounded-full bg-red-500 text-white shadow-[0_0_34px_rgba(255,46,63,.9)]"><div class="absolute h-10 w-10 animate-ping rounded-full bg-red-500/40"></div><span class="relative text-[10px] font-black">SOS</span></div>',
  iconSize: [40, 40],
  iconAnchor: [20, 20],
});

const cameraIcon = L.divIcon({
  className: "",
  html: '<div class="flex h-8 w-8 items-center justify-center rounded-full bg-orange-500 text-white text-xs font-bold">CCTV</div>',
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

export default function TrackingPage() {
  const { 
    trackingSessions, 
    emergencySessions, 
    selectedSessionId, 
    selectSession, 
    refreshIncidents 
  } = useEmergencySessions();
  
  const [mapCenter, setMapCenter] = useState([20.5937, 78.9629]);
  const [mapZoom, setMapZoom] = useState(5);
  const [selectedTrackingSession, setSelectedTrackingSession] = useState(null);
  const [trackingRoutes, setTrackingRoutes] = useState({});

  const selectedSession = useMemo(() => 
    emergencySessions.find((s) => s.sessionId === selectedSessionId) || null,
    [emergencySessions, selectedSessionId]
  );

  // Focus map on selected session
  useEffect(() => {
    if (selectedSession?.latestLocation?.latitude && selectedSession?.latestLocation?.longitude) {
      setMapCenter([selectedSession.latestLocation.latitude, selectedSession.latestLocation.longitude]);
      setMapZoom(15);
    }
  }, [selectedSession]);

  // Load tracking history for all sessions
  useEffect(() => {
    const loadTrackingHistory = async () => {
      const routes = {};
      for (const session of trackingSessions) {
        if (session.sessionId) {
          try {
            const history = await getTrackingHistory(session.sessionId);
            if (history?.locations?.length > 1) {
              routes[session.sessionId] = history.locations.map((loc) => [loc.latitude, loc.longitude]);
            }
          } catch (err) {
            console.warn(`Failed to load tracking history for ${session.sessionId}:`, err);
          }
        }
      }
      setTrackingRoutes(routes);
    };
    loadTrackingHistory();
  }, [trackingSessions]);

  const handleSessionClick = (sessionId) => {
    selectSession(sessionId);
    setSelectedTrackingSession(sessionId);
  };

  if (trackingSessions.length === 0 && emergencySessions.length === 0) {
    return (
      <main className="min-w-0 flex-1 px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl text-center py-20">
          <MapPin className="h-16 w-16 mx-auto text-slate-600" />
          <h2 className="mt-6 text-2xl font-black text-white">No Active Tracking Sessions</h2>
          <p className="mt-2 text-slate-400">Emergency tracking sessions will appear here when users trigger SOS or HELP</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8">
      <section className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-6">
          <div className="inline-flex items-center gap-2 rounded-full border border-alert-500/30 bg-alert-500/12 px-4 py-2 text-xs font-black uppercase tracking-[0.16em] text-red-100">
            <Radio className="h-4 w-4" />
            Live GPS Tracking
          </div>
          <h1 className="mt-4 text-4xl font-black tracking-tight text-white sm:text-5xl">
            Active Tracking Sessions
          </h1>
          <p className="mt-2 text-lg text-slate-300">
            {trackingSessions.length} session{trackingSessions.length !== 1 ? "s" : ""} active across {emergencySessions.length} emergenc{emergencySessions.length !== 1 ? "ies" : "y"}
          </p>
        </div>

        {/* Map + Session List */}
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.5fr)_400px]">
          {/* Map */}
          <div className="relative">
            <div className="map-shell h-[600px] overflow-hidden rounded-[1.4rem] border border-white/10 bg-command-900">
              <MapContainer center={mapCenter} zoom={mapZoom} scrollWheelZoom className="z-0">
                <TileLayer
                  attribution="&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors"
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <MapFocus center={mapCenter} zoom={mapZoom} />
                
                {/* Tracking routes */}
                {Object.entries(trackingRoutes).map(([sessionId, path]) => (
                  <Polyline
                    key={sessionId}
                    positions={path}
                    color="#2f80ff"
                    weight={3}
                    opacity={0.8}
                    dashArray="5, 10"
                  />
                ))}

                {/* Victim markers */}
                {trackingSessions.map((session) => (
                  <Marker key={session.sessionId} position={[session.latitude, session.longitude]} icon={victimIcon}>
                    <Popup>
                      <div className="text-white">
                        <strong>{session.fullName}</strong>
                        <br />
                        Status: {session.status}
                        <br />
                        Threat: {session.threat}
                        <br />
                        GPS: {session.gpsStatus}
                        <br />
                        Speed: {session.speed?.toFixed(1) || 0} m/s
                        <br />
                        Last: {formatTime(session.lastUpdate)}
                      </div>
                    </Popup>
                  </Marker>
                ))}

                {/* CCTV markers for selected session */}
                {selectedSession?.nearbyCameras?.map((camera) => (
                  camera.latitude && camera.longitude && (
                    <Marker key={camera.camera_id || camera.id} position={[camera.latitude, camera.longitude]} icon={cameraIcon}>
                      <Popup>
                        <div className="text-white">
                          <strong>{camera.camera_name || camera.camera_id}</strong>
                          <br />
                          Distance: {camera.distance}m
                          <br />
                          Status: {camera.online_status || "unknown"}
                        </div>
                      </Popup>
                    </Marker>
                  )
                ))}
              </MapContainer>
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
                <RefreshCw className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Session List */}
          <div className="space-y-4">
            <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
              <h3 className="text-lg font-black text-white">Active Sessions</h3>
              <p className="text-xs text-slate-500 mt-1">Click to focus map</p>
            </div>

            {emergencySessions.map((session) => (
              <motion.div
                key={session.sessionId}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className={`rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-4 backdrop-blur-xl transition cursor-pointer ${
                  selectedSessionId === session.sessionId ? "border-alert-500/50 bg-alert-500/5 ring-1 ring-alert-500/20" : "hover:border-alert-500/30"
                }`}
                onClick={() => handleSessionClick(session.sessionId)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-white truncate">{session.fullName}</span>
                      <StatusBadge tone={session.status === "ACTIVE" ? "live" : "resolved"} pulse={session.status === "ACTIVE"}>
                        {session.status}
                      </StatusBadge>
                      <StatusBadge tone={session.threatLevel === "HIGH" || session.threatLevel === "CRITICAL" || session.threatLevel === "EMERGENCY" ? "high risk" : "active"}>
                        {session.threatLevel}
                      </StatusBadge>
                    </div>
                    <p className="mt-1 text-sm text-slate-400">Trigger: {session.triggerSource}</p>
                    <p className="text-xs text-slate-500 mt-0.5 font-mono">Session: {session.sessionId}</p>
                    <div className="mt-2 flex items-center gap-4 text-xs text-slate-400">
                      <span className="flex items-center gap-1">
                        <Zap className="h-3 w-3" />
                        Threat: {session.threatScore}
                      </span>
                      <span className="flex items-center gap-1">
                        <Battery className="h-3 w-3" />
                        GPS: {session.deviceStatus}
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
                        <Zap className="h-3 w-3" />
                        {session.nearbyCameras.length} CCTV nearby (closest: {session.nearbyCameras[0].distance}m)
                      </p>
                    )}
                  </div>
                  <ArrowUpRight className="h-5 w-5 text-slate-400 shrink-0" />
                </div>
              </motion.div>
            ))}

            {emergencySessions.length === 0 && (
              <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-8 text-center backdrop-blur-xl">
                <MapPin className="h-12 w-12 mx-auto text-slate-600" />
                <p className="mt-4 text-slate-400">No active emergency sessions</p>
              </div>
            )}
          </div>
        </div>

        {/* Selected Session Details */}
        {selectedSession && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-6 rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl"
          >
            <h3 className="text-lg font-black text-white">Session Details: {selectedSession.fullName}</h3>
            <div className="mt-4 grid gap-4 md:grid-cols-4">
              <div className="rounded-xl border border-white/10 bg-black/24 p-4">
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Session ID</p>
                <p className="mt-1 font-mono text-sm text-white break-all">{selectedSession.sessionId}</p>
              </div>
              <div className="rounded-xl border border-white/10 bg-black/24 p-4">
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">User ID</p>
                <p className="mt-1 font-mono text-sm text-white">{selectedSession.userId}</p>
              </div>
              <div className="rounded-xl border border-white/10 bg-black/24 p-4">
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Threat Score</p>
                <p className="mt-1 font-bold text-xl text-red-400">{selectedSession.threatScore}/100</p>
              </div>
              <div className="rounded-xl border border-white/10 bg-black/24 p-4">
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">GPS Status</p>
                <p className="mt-1 font-bold text-emerald-400">{selectedSession.deviceStatus}</p>
              </div>
            </div>
            
            {/* Live Location Details */}
            {selectedSession.latestLocation.latitude && (
              <div className="mt-4 grid gap-4 md:grid-cols-4">
                <div className="rounded-xl border border-white/10 bg-black/24 p-4">
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Latitude</p>
                  <p className="mt-1 font-mono text-sm text-white">{selectedSession.latestLocation.latitude.toFixed(6)}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/24 p-4">
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Longitude</p>
                  <p className="mt-1 font-mono text-sm text-white">{selectedSession.latestLocation.longitude.toFixed(6)}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/24 p-4">
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Last Update</p>
                  <p className="mt-1 font-mono text-sm text-white">{formatTime(selectedSession.locationUpdatedAt)}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/24 p-4">
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">GPS Quality</p>
                  <p className="mt-1 font-bold text-emerald-400">
                    {selectedSession.trackingStatus === "ACTIVE" ? "LIVE" : selectedSession.trackingStatus}
                  </p>
                </div>
              </div>
            )}
            
            {/* Nearby CCTV */}
            {selectedSession.nearbyCameras?.length > 0 && (
              <div className="mt-4">
                <h4 className="text-sm font-bold text-slate-300 mb-3">Nearby CCTV Cameras</h4>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {selectedSession.nearbyCameras.slice(0, 5).map((camera) => (
                    <div key={camera.camera_id || camera.id} className="flex items-center justify-between p-3 rounded-xl border border-white/10 bg-black/24">
                      <div>
                        <p className="font-medium text-white">{camera.camera_name || `CCTV-${camera.camera_id}`}</p>
                        <p className="text-xs text-slate-400">{camera.distance}m away • {camera.online_status || "unknown"}</p>
                      </div>
                      <div className={`flex h-2 w-2 rounded-full ${camera.online_status === "online" ? "bg-emerald-400" : "bg-slate-600"}`} />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </section>
    </main>
  );
}

function MapFocus({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, map, zoom]);
  return null;
}
