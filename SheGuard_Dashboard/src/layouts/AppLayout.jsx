import { useState, useEffect, useCallback, useMemo } from "react";
import { Bell, Radio, Search, ShieldCheck, UserRound, LogOut, Wifi, WifiOff, Cpu, Camera, AlertTriangle, MapPin, Zap, Activity, Users, Gauge } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import MinimalSidebar from "../components/MinimalSidebar";
import NotificationCenter from "../components/NotificationCenter";
import SystemStatusBar from "../components/SystemStatusBar";
import { useEmergencySessions } from "../hooks/useEmergencySessions";
import { getCameras, checkBackendHealth } from "../services/api";
import { HEALTH_STATUS } from "../config";

export default function AppLayout({ children, onLogout }) {
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [backendStatus, setBackendStatus] = useState("connected");
  const [lastSync, setLastSync] = useState(null);
  const [aiStatus, setAiStatus] = useState("online");
  const [agentsStatus, setAgentsStatus] = useState("online");
  const [cctvCount, setCctvCount] = useState({ online: 0, total: 0 });

  const {
    emergencySessions,
    activeCount,
    highRiskCount,
    trackingSessions,
    notifications,
    unreadCount,
    realtimeStatus,
    backendError,
    isLoading,
    refreshIncidents,
  } = useEmergencySessions();

  const handleLogout = useCallback(() => {
    onLogout?.();
  }, [onLogout]);

  // Check backend health periodically
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const health = await checkBackendHealth();
        if (health.status === HEALTH_STATUS.HEALTHY) {
          setBackendStatus("connected");
          setLastSync(new Date());
        } else {
          setBackendStatus("disconnected");
        }
      } catch {
        setBackendStatus("disconnected");
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  // Load camera data
  useEffect(() => {
    const loadCameras = async () => {
      try {
        const response = await getCameras();
        const cameras = response?.cameras || [];
        const online = cameras.filter((c) => c.online_status === "online").length;
        setCctvCount({ online, total: cameras.length });
      } catch {
        setCctvCount({ online: 0, total: 0 });
      }
    };
    loadCameras();
  }, []);

  // Calculate tracking active count
  const trackingActive = useMemo(() => 
    trackingSessions.filter((s) => s.status === "ACTIVE").length,
    [trackingSessions]
  );

  const statuses = useMemo(() => [
    { 
      key: "backend", 
      label: "Backend", 
      status: backendStatus, 
      icon: Wifi, 
      iconOff: WifiOff,
      colors: { connected: "text-emerald-400", disconnected: "text-red-400" }
    },
    { 
      key: "realtime", 
      label: "Realtime", 
      status: realtimeStatus, 
      icon: Zap, 
      iconOff: AlertTriangle,
      colors: { connected: "text-cyan-400", connecting: "text-amber-400", reconnecting: "text-amber-400", disconnected: "text-red-400" }
    },
    { 
      key: "ai", 
      label: "AI", 
      status: aiStatus, 
      icon: Cpu, 
      iconOff: AlertTriangle,
      colors: { online: "text-violet-400", offline: "text-red-400" }
    },
    { 
      key: "agents", 
      label: "Agents", 
      status: agentsStatus, 
      icon: Activity, 
      iconOff: AlertTriangle,
      colors: { online: "text-blue-400", offline: "text-red-400" }
    },
    { 
      key: "cctv", 
      label: "CCTV", 
      status: cctvCount.online > 0 ? "online" : "offline", 
      icon: Camera, 
      iconOff: AlertTriangle,
      colors: { online: "text-orange-400", offline: "text-red-400" },
      detail: `${cctvCount.online}/${cctvCount.total} online`
    },
  ], [backendStatus, realtimeStatus, aiStatus, agentsStatus, cctvCount]);

  return (
    <div className="min-h-screen bg-command text-white">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute left-1/2 top-[-18rem] h-[38rem] w-[38rem] -translate-x-1/2 rounded-full bg-alert-500/14 blur-3xl" />
        <div className="absolute right-[-10rem] top-24 h-[26rem] w-[26rem] rounded-full bg-cyan-400/8 blur-3xl" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.028)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.028)_1px,transparent_1px)] bg-[size:52px_52px]" />
      </div>

      <div className="relative flex min-h-screen">
        <MinimalSidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          {/* System Status Bar */}
          <div className="border-b border-white/10 bg-command-950/68 backdrop-blur-2xl">
            {/* Top metrics row */}
            <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6">
              <div className="flex items-center gap-6 text-xs font-semibold uppercase tracking-[0.12em]">
                <div className="flex items-center gap-2 text-red-400">
                  <ShieldCheck className="h-4 w-4" />
                  <span>ACTIVE EMERGENCIES</span>
                  <span className="font-black text-white px-2 py-0.5 rounded bg-red-500/20 border border-red-500/30">{activeCount}</span>
                </div>
                <div className="flex items-center gap-2 text-amber-400">
                  <AlertTriangle className="h-4 w-4" />
                  <span>HIGH RISK</span>
                  <span className="font-black text-white px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/30">{highRiskCount}</span>
                </div>
                <div className="flex items-center gap-2 text-blue-400">
                  <MapPin className="h-4 w-4" />
                  <span>TRACKING</span>
                  <span className="font-black text-white px-2 py-0.5 rounded bg-blue-500/20 border border-blue-500/30">{trackingActive}</span>
                </div>
                <div className="flex items-center gap-2 text-slate-400">
                  <Activity className="h-4 w-4" />
                  <span>LAST SYNC</span>
                  <span className="font-mono text-white">{lastSync ? formatLastSync(lastSync) : "---"}</span>
                </div>
              </div>
            </div>

            {/* System status row */}
            <div className="border-t border-white/5 px-4 py-2">
              <div className="mx-auto flex max-w-7xl items-center gap-4 flex-wrap">
                {statuses.map((item) => {
                  const isOnline = item.status === "connected" || item.status === "online" || item.status === "ok";
                  const isConnecting = item.status === "connecting" || item.status === "reconnecting";
                  const Icon = isOnline ? item.icon : item.iconOff;
                  const color = isOnline 
                    ? item.colors.connected 
                    : isConnecting 
                      ? item.colors.connecting || item.colors.disconnected 
                      : item.colors.disconnected || item.colors.offline || "text-red-400";
                  const statusText = item.status.charAt(0).toUpperCase() + item.status.slice(1);
                  
                  return (
                    <div key={item.key} className="flex items-center gap-2 text-xs font-medium">
                      <Icon className={`${color} h-3.5 w-3.5`} />
                      <span className="text-slate-400">{item.label}</span>
                      <span className={`${color} font-mono`}>{statusText}</span>
                      {item.detail && <span className="text-slate-500 ml-1">{item.detail}</span>}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
          
          <motion.header
            initial={{ opacity: 0, y: -18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="sticky top-0 z-40 border-b border-white/10 bg-command-950/68 backdrop-blur-2xl"
          >
            <div className="flex h-20 items-center gap-3 px-4 sm:px-6">
              <div className="flex min-w-0 flex-1 items-center gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-alert-500/40 bg-alert-500/14 shadow-glow">
                  <ShieldCheck className="h-6 w-6 text-alert-500" />
                </div>
                <div className="min-w-0">
                  <p className="truncate text-lg font-black tracking-tight text-white">SheGuard AI+</p>
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_16px_rgba(52,211,153,.9)]" />
                    Police Command Center
                  </div>
                </div>
              </div>

              <label className="hidden h-11 w-full max-w-md items-center gap-3 rounded-full border border-white/10 bg-white/[0.055] px-4 text-slate-400 transition focus-within:border-alert-500/50 md:flex">
                <Search className="h-4 w-4" />
                <input
                  form="incident-filters"
                  name="globalSearch"
                  placeholder="Search incident, user, camera, location..."
                  className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
                />
              </label>

              <div className="flex items-center gap-2">
                <div className="hidden items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-2 text-sm font-semibold text-emerald-100 sm:flex">
                  <Radio className="h-4 w-4" />
                  Live
                </div>
                
                {/* Notifications */}
                <div className="relative">
                  <button
                    onClick={() => setShowNotifications(!showNotifications)}
                    className="relative flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-white/[0.055] text-slate-200 transition hover:border-alert-500/40 hover:text-white"
                    aria-label="Notifications"
                  >
                    <Bell className="h-5 w-5" />
                    {unreadCount > 0 && (
                      <span className="absolute right-2.5 top-2.5 h-2 w-2 rounded-full bg-alert-500" />
                    )}
                  </button>
                  
                  <AnimatePresence>
                    {showNotifications && (
                      <NotificationCenter 
                        notifications={notifications} 
                        onClose={() => setShowNotifications(false)} 
                        onNotificationClick={(notification) => {
                          // Handle notification click - navigate to incident/session
                          console.log("Notification clicked:", notification);
                        }}
                      />
                    )}
                  </AnimatePresence>
                </div>

                {/* User Menu */}
                <div className="relative">
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-white/[0.055] text-slate-200 transition hover:border-alert-500/40 hover:text-white"
                    aria-label="User menu"
                  >
                    <UserRound className="h-5 w-5" />
                  </button>
                  
                  <AnimatePresence>
                    {showUserMenu && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 10 }}
                        className="absolute right-0 top-full mt-2 w-48 rounded-xl border border-white/10 bg-command-950/95 backdrop-blur-2xl shadow-xl py-2 z-50"
                      >
                        <button
                          onClick={handleLogout}
                          className="flex w-full items-center gap-3 px-4 py-3 text-sm text-slate-300 hover:bg-white/5 hover:text-white transition"
                        >
                          <LogOut className="h-4 w-4" />
                          Sign Out
                        </button>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            </div>
          </motion.header>
          
          {children}
        </div>
      </div>
    </div>
  );
}

function formatLastSync(date) {
  const d = new Date(date);
  const now = Date.now();
  const diff = Math.floor((now - d.getTime()) / 1000);
  
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
