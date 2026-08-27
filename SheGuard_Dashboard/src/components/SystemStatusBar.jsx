import { Wifi, WifiOff, Cpu, Camera, AlertTriangle, MapPin, Zap, ShieldCheck, Users, Activity } from "lucide-react";

export default function SystemStatusBar({ 
  backendStatus = "connected",
  realtimeStatus = "connected",
  aiStatus = "online",
  agentsStatus = "online",
  cctvOnline = 0,
  cctvTotal = 0,
  activeEmergencies = 0,
  highRisk = 0,
  trackingActive = 0,
  lastSync = null
}) {
  const statuses = [
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
      status: cctvOnline > 0 ? "online" : "offline", 
      icon: Camera, 
      iconOff: AlertTriangle,
      colors: { online: "text-orange-400", offline: "text-red-400" },
    },
  ];

  return (
    <div className="border-b border-white/10 bg-command-950/68 backdrop-blur-2xl">
      {/* Top metrics row */}
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6">
        <div className="flex items-center gap-6 text-xs font-semibold uppercase tracking-[0.12em]">
          <div className="flex items-center gap-2 text-red-400">
            <ShieldCheck className="h-4 w-4" />
            <span>ACTIVE EMERGENCIES</span>
            <span className="font-black text-white px-2 py-0.5 rounded bg-red-500/20 border border-red-500/30">{activeEmergencies}</span>
          </div>
          <div className="flex items-center gap-2 text-amber-400">
            <AlertTriangle className="h-4 w-4" />
            <span>HIGH RISK</span>
            <span className="font-black text-white px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/30">{highRisk}</span>
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
