import { useLocation } from "react-router-dom";
import { Archive, BarChart3, LayoutDashboard, MapPinned, RadioTower, Video, FileText, Bell, ShieldAlert } from "lucide-react";
import { motion } from "framer-motion";
import { NavLink } from "react-router-dom";

const items = [
  { label: "Dashboard", icon: LayoutDashboard, path: "/" },
  { label: "Live Incidents", icon: RadioTower, path: "/incidents" },
  { label: "CCTV Center", icon: Video, path: "/cctv" },
  { label: "Tracking", icon: MapPinned, path: "/tracking" },
  { label: "Archive", icon: Archive, path: "/archive" },
  { label: "Analytics", icon: BarChart3, path: "/analytics" },
  { label: "Evidence", icon: FileText, path: "/evidence" },
  { label: "Notifications", icon: Bell, path: "/notifications" },
];

export default function MinimalSidebar() {
  const location = useLocation();
  
  return (
    <aside className="hidden w-[92px] shrink-0 border-r border-white/10 bg-black/28 px-3 py-5 backdrop-blur-2xl lg:block">
      <nav className="flex h-full flex-col items-center gap-3">
        {items.map((item, index) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path || (item.path !== "/" && location.pathname.startsWith(item.path));
          return (
            <NavLink
              key={item.label}
              to={item.path}
              initial={{ opacity: 0, x: -18 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.04 }}
              title={item.label}
              className={({ isActive: active }) => `group flex h-14 w-14 items-center justify-center rounded-2xl border transition ${active ? "border-alert-500 bg-alert-500/10" : "border-white/10"}`}
            >
              <Icon className="h-5 w-5 transition group-hover:scale-110" />
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}
