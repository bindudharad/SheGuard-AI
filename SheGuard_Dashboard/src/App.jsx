import { useEffect, useState, useCallback } from "react";
import "leaflet/dist/leaflet.css";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "./layouts/AppLayout";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import IncidentDetailPage from "./pages/IncidentDetailPage";
import TrackingPage from "./pages/TrackingPage";
import ArchivePage from "./pages/ArchivePage";
import AnalyticsPage from "./pages/AnalyticsPage";
import CctvPage from "./pages/CctvPage";
import EvidencePage from "./pages/EvidencePage";
import ErrorBoundary from "./components/ErrorBoundary";
import { isAuthenticated, setToken, logout as apiLogout, api } from "./services/api";

export default function App() {
  const [authed, setAuthed] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);

  // Check authentication on mount
  useEffect(() => {
    const checkAuth = () => {
      const token = localStorage.getItem("sheguard_dashboard_token");
      if (token) {
        setToken(token);
        setAuthed(true);
      }
      setAuthChecked(true);
    };
    checkAuth();
  }, []);

  // Setup axios interceptor for 401/403 handling
  useEffect(() => {
    const interceptor = api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401 || error.response?.status === 403) {
          // Token expired or invalid
          apiLogout();
          setAuthed(false);
          window.location.href = "/login?expired=1";
        }
        return Promise.reject(error);
      }
    );

    return () => {
      api.interceptors.response.eject(interceptor);
    };
  }, []);

  const handleLogin = useCallback(() => {
    setAuthed(true);
  }, []);

  const handleLogout = useCallback(() => {
    apiLogout();
    setAuthed(false);
  }, []);

  // Show loading state while auth is being checked - but dont early return!
  // This avoids the "Rendered more hooks than during the previous render" error
  const showLoading = !authChecked;

  return (
    <ErrorBoundary fallbackMessage="Application failed to initialize. Please refresh.">
      <Router>
        <div className="min-h-screen bg-command text-white">
          {showLoading && (
            <div className="min-h-screen bg-command text-white flex items-center justify-center fixed inset-0 z-50">
              <div className="text-center">
                <div className="h-12 w-12 animate-spin border-4 border-alert-500/30 border-t-alert-500 rounded-full mx-auto" />
                <p className="mt-4 text-slate-400">Initializing...</p>
              </div>
            </div>
          )}
          <Routes>
            <Route path="/login" element={authed ? <Navigate to="/" replace /> : <LoginPage onSuccess={handleLogin} />} />
            <Route
              path="/*"
              element={
                authed ? (
                  <AppLayout onLogout={handleLogout}>
                    <Routes>
                      <Route path="/" element={<DashboardPage />} />
                      <Route path="incident/:id" element={<IncidentDetailPage />} />
                      <Route path="tracking" element={<TrackingPage />} />
                      <Route path="archive" element={<ArchivePage />} />
                      <Route path="analytics" element={<AnalyticsPage />} />
                      <Route path="cctv" element={<CctvPage />} />
                      <Route path="evidence" element={<EvidencePage />} />
                    </Routes>
                  </AppLayout>
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
          </Routes>
        </div>
      </Router>
    </ErrorBoundary>
  );
}
