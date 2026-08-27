import * as React from "react";
import { Outlet, NavLink, useLocation } from "react-router-dom";

const NAV_ITEMS = [
  { path: "/", label: "Overview", icon: "🏠" },
  { path: "/pipeline", label: "Live Pipeline", icon: "🔄" },
  { path: "/agents", label: "Agents", icon: "🤖" },
  { path: "/events", label: "Events", icon: "📡" },
  { path: "/incidents", label: "Incidents", icon: "🚨" },
  { path: "/responses", label: "Responses", icon: "🚑" },
  { path: "/x402", label: "x402", icon: "💳" },
  { path: "/performance", label: "Performance", icon: "📊" },
  { path: "/health", label: "Health", icon: "🏥" },
  { path: "/logs", label: "Logs", icon: "📝" },
  { path: "/tests", label: "Tests", icon: "✅" },
  { path: "/settings", label: "Settings", icon: "⚙️" },
];

export function Layout() {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = React.useState(true);

  return (
    <div className="min-h-screen bg-bg-DEFAULT font-sans text-slate-100 flex">
      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 z-40 h-screen transition-all duration-300 bg-bg-secondary border-r border-slate-800/50 flex flex-col ${
          sidebarOpen ? "w-64" : "w-20"
        }`}
      >
        <div className="flex items-center justify-between h-16 px-4 border-b border-slate-800/50">
          {sidebarOpen && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-DEFAULT to-sky-700 flex items-center justify-center">
                <span style={{ fontSize: 16 }}>🛡️</span>
              </div>
              <span className="font-semibold text-lg tracking-tight">SheGuard AI+</span>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 rounded-lg hover:bg-slate-800/50 transition-colors text-slate-400 hover:text-slate-100"
            aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {sidebarOpen ? (
                <>
                  <polyline points="15 18 9 12 15 6" />
                </>
              ) : (
                <>
                  <polyline points="9 18 15 12 9 6" />
                </>
              )}
            </svg>
          </button>
        </div>

        <nav className="flex-1 py-4 px-2 overflow-y-auto" role="navigation" aria-label="Main navigation">
          <ul className="space-y-1">
            {NAV_ITEMS.map((item) => {
              const isActive = location.pathname === item.path || (item.path !== "/" && location.pathname.startsWith(item.path + "/"));
              return (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${
                        isActive
                          ? "bg-accent-DEFAULT/15 text-accent-DEFAULT border-l-2 border-accent-DEFAULT"
                          : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/50"
                      }`
                    }
                    title={sidebarOpen ? undefined : item.label}
                  >
                    <span style={{ fontSize: 18 }} aria-hidden="true">{item.icon}</span>
                    {sidebarOpen && <span className="font-medium">{item.label}</span>}
                  </NavLink>
                </li>
              );
            })}
          </ul>
        </nav>

        {sidebarOpen && (
          <div className="p-4 border-t border-slate-800/50">
            <div className="flex items-center gap-3 p-3 rounded-lg bg-slate-800/30 border border-slate-700/50">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" aria-hidden="true" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-slate-500 uppercase tracking-wider">System Status</p>
                <p className="text-sm font-medium text-green-400">LIVE</p>
              </div>
            </div>
          </div>
        )}
      </aside>

      {/* Main Content */}
      <main
        className={`flex-1 flex flex-col transition-all duration-300 ${sidebarOpen ? "ml-64" : "ml-20"}`}
        role="main"
      >
        {/* Top Header */}
        <header className="h-16 bg-bg-secondary/80 backdrop-blur-lg border-b border-slate-800/50 flex items-center justify-between px-6 sticky top-0 z-30">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold tracking-tight">
              {NAV_ITEMS.find((i) => location.pathname === i.path || (i.path !== "/" && location.pathname.startsWith(i.path + "/")))?.label || "Dashboard"}
            </h1>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/50 border border-slate-700/50 text-sm font-mono text-slate-300">
              <span id="live-time" className="font-mono">00:00:00</span>
            </div>

            <div className="flex items-center gap-3">
              <button className="p-2 rounded-lg hover:bg-slate-800/50 transition-colors text-slate-400 hover:text-slate-100" aria-label="Notifications">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                  <path d="M13.73 21a2 2 0 0 1-3.46 0" />
                </svg>
              </button>

              <button className="p-2 rounded-lg hover:bg-slate-800/50 transition-colors text-slate-400 hover:text-slate-100" aria-label="Settings">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
              </button>

              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-sky-500 to-violet-500 flex items-center justify-center font-medium text-xs">
                SG
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 p-6 overflow-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
