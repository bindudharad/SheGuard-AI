import { useEffect, useMemo, useState } from "react";
import { Search, Filter, Video, Camera, Zap, MapPin, AlertTriangle, Wifi, WifiOff, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";
import { useEmergencySessions } from "../hooks/useEmergencySessions";
import { getCameras, getCameraHealth } from "../services/api";
import { formatTime } from "../lib/incidents";

export default function CctvPage() {
  const { selectedSession } = useEmergencySessions();
  const [cameras, setCameras] = useState([]);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [camerasData, healthData] = await Promise.all([
          getCameras(),
          getCameraHealth(),
        ]);
        setCameras(camerasData?.cameras || []);
        setHealth(healthData);
      } catch (err) {
        console.error("Failed to load CCTV data:", err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
    const interval = setInterval(loadData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const filteredCameras = useMemo(() => {
    let result = [...cameras];

    if (query.trim()) {
      const search = query.trim().toLowerCase();
      result = result.filter((camera) =>
        [camera.camera_name, camera.camera_id, camera.ip_address].some((val) =>
          String(val || "").toLowerCase().includes(search)
        )
      );
    }

    if (statusFilter !== "all") {
      result = result.filter((c) => c.online_status === statusFilter);
    }

    return result;
  }, [cameras, query, statusFilter]);

  const onlineCount = cameras.filter((c) => c.online_status === "online").length;
  const offlineCount = cameras.filter((c) => c.online_status === "offline").length;
  const degradedCount = cameras.filter((c) => c.online_status === "degraded").length;

  const runtime = health?.runtime || {};

  return (
    <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8">
      <section className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-orange-500/30 bg-orange-500/12 px-4 py-2 text-xs font-black uppercase tracking-[0.16em] text-orange-100">
            <Video className="h-4 w-4" />
            CCTV Command Center
          </div>
          <h1 className="mt-4 text-4xl font-black tracking-tight text-white sm:text-5xl">
            Camera Monitoring & Status
          </h1>
          <p className="mt-2 text-lg text-slate-300">
            Real-time CCTV camera status and health monitoring across the SheGuard network
          </p>
        </div>

        {/* Summary Stats */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5 mb-8">
          <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Total Cameras</p>
                <p className="mt-2 text-3xl font-black text-white">{cameras.length}</p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-orange-500/20 text-orange-400">
                <Camera className="h-6 w-6" />
              </div>
            </div>
          </div>
          <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Online</p>
                <p className="mt-2 text-3xl font-black text-emerald-400">{onlineCount}</p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400">
                <Wifi className="h-6 w-6" />
              </div>
            </div>
          </div>
          <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Degraded</p>
                <p className="mt-2 text-3xl font-black text-amber-400">{degradedCount}</p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-amber-500/20 text-amber-400">
                <AlertTriangle className="h-6 w-6" />
              </div>
            </div>
          </div>
          <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Offline</p>
                <p className="mt-2 text-3xl font-black text-red-400">{offlineCount}</p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/20 text-red-400">
                <WifiOff className="h-6 w-6" />
              </div>
            </div>
          </div>
          <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">AI Active</p>
                <p className="mt-2 text-3xl font-black text-violet-400">
                  {cameras.filter((c) => c.ai_enabled).length}
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-violet-500/20 text-violet-400">
                <Zap className="h-6 w-6" />
              </div>
            </div>
          </div>
        </div>

        {/* Search & Filters */}
        <div className="mb-6">
          <div className="flex flex-wrap gap-4">
            <div className="relative flex-1 min-w-[280px]">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search camera name, ID, IP..."
                className="w-full h-12 pl-12 pr-4 rounded-xl border border-white/10 bg-white/[0.055] text-white placeholder:text-slate-500 outline-none focus:border-alert-500/50 transition"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-12 rounded-xl border border-white/10 bg-white/[0.055] text-white outline-none focus:border-alert-500/50 px-4"
            >
              <option value="all">All Status</option>
              <option value="online">Online</option>
              <option value="degraded">Degraded</option>
              <option value="offline">Offline</option>
              <option value="unknown">Unknown</option>
            </select>
            <button
              onClick={() => {
                setLoading(true);
                getCameras().then((data) => {
                  setCameras(data?.cameras || []);
                  setLoading(false);
                });
              }}
              disabled={loading}
              className="h-12 px-4 rounded-xl border border-white/10 bg-white/[0.055] text-white outline-none focus:border-alert-500/50 flex items-center gap-2 disabled:opacity-50"
            >
              <RefreshCw className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
              Refresh
            </button>
          </div>
        </div>

        {/* Camera Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {loading ? (
            [...Array(8)].map((_, i) => (
              <div key={i} className="h-80 animate-pulse rounded-[1.4rem] border border-white/10 bg-white/[0.055]" />
            ))
          ) : filteredCameras.length > 0 ? (
            filteredCameras.map((camera) => (
              <motion.div
                key={camera.camera_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-bold text-white">{camera.camera_name || `CCTV-${camera.camera_id}`}</p>
                    <p className="text-xs text-slate-400 font-mono">ID: {camera.camera_id}</p>
                  </div>
                  <div className={`flex h-2 w-2 rounded-full ${
                    camera.online_status === "online" ? "bg-emerald-400" :
                    camera.online_status === "degraded" ? "bg-amber-400" :
                    "bg-slate-600"
                  }`} />
                </div>

                <div className="mt-4 space-y-2 text-sm text-slate-300">
                  {camera.ip_address && (
                    <p className="flex items-center gap-2">
                      <MapPin className="h-3.5 w-3.5 text-orange-400" />
                      <span className="font-mono">{camera.ip_address}</span>
                    </p>
                  )}
                  {camera.latitude && camera.longitude && (
                    <p className="flex items-center gap-2">
                      <MapPin className="h-3.5 w-3.5 text-blue-400" />
                      <span className="font-mono">{camera.latitude.toFixed(4)}, {camera.longitude.toFixed(4)}</span>
                    </p>
                  )}
                  {camera.rtsp_url && (
                    <p className="flex items-center gap-2">
                      <Video className="h-3.5 w-3.5 text-violet-400" />
                      <span className="font-mono text-xs truncate max-w-[200px]">{camera.rtsp_url}</span>
                    </p>
                  )}
                  <p className="flex items-center gap-2">
                    <Zap className="h-3.5 w-3.5 text-cyan-400" />
                    <span>AI: {camera.ai_enabled ? "Enabled" : "Disabled"}</span>
                  </p>
                </div>

                {/* Distance from selected session */}
                {selectedSession?.latestLocation?.latitude && camera.latitude && camera.longitude && (
                  <div className="mt-4 pt-4 border-t border-white/10">
                    <p className="text-xs text-slate-400">
                      Distance from selected victim:{' '}
                      <span className="font-mono text-white">
                        {calculateDistance(
                          selectedSession.latestLocation.latitude,
                          selectedSession.latestLocation.longitude,
                          camera.latitude,
                          camera.longitude
                        ).toFixed(0)}m
                      </span>
                    </p>
                  </div>
                )}
              </motion.div>
            ))
          ) : (
            <div className="col-span-full text-center py-20">
              <Camera className="h-16 w-16 mx-auto text-slate-600" />
              <h2 className="mt-6 text-xl font-bold text-white">No cameras found</h2>
              <p className="mt-2 text-slate-400">Try adjusting your filters or search terms</p>
            </div>
          )}
        </div>

        {/* Runtime Status */}
        {runtime && Object.keys(runtime).length > 0 && (
          <div className="mt-8 rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
            <h3 className="text-lg font-black text-white mb-4">Runtime Status</h3>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-xl border border-white/10 bg-black/24 p-4">
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Active Streams</p>
                <p className="mt-1 font-bold text-xl text-white">{runtime.active_streams || 0}</p>
              </div>
              <div className="rounded-xl border border-white/10 bg-black/24 p-4">
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Total Frames</p>
                <p className="mt-1 font-bold text-xl text-white">{runtime.total_frames || 0}</p>
              </div>
              <div className="rounded-xl border border-white/10 bg-black/24 p-4">
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Errors</p>
                <p className="mt-1 font-bold text-xl text-white">{runtime.errors || 0}</p>
              </div>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}

function calculateDistance(lat1, lon1, lat2, lon2) {
  const R = 6371000; // Earth radius in meters
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}
