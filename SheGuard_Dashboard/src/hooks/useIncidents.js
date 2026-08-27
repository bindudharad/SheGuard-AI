import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { REFRESH_INTERVAL_MS } from "../config";
import { getIncidents, getLatestIncidents, handleApiError } from "../services/api";
import { normalizeIncident, toIncidentArray } from "../lib/incidents";

export function useIncidents() {
  const [incidents, setIncidents] = useState([]);
  const [latestIncident, setLatestIncident] = useState(null);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [backendStatus, setBackendStatus] = useState("connected"); // connected, disconnected, error
  const seenIncidentIds = useRef(new Set());

  const refresh = useCallback(async () => {
    try {
      const [incidentPayload, latestPayload] = await Promise.allSettled([
        getIncidents(),
        getLatestIncidents(),
      ]);

      let newIncidents = [];
      let newLatest = null;

      if (incidentPayload.status === "fulfilled") {
        const normalized = toIncidentArray(incidentPayload.value).map(normalizeIncident);
        // Deduplicate by incident ID
        newIncidents = normalized.filter((inc) => {
          if (seenIncidentIds.current.has(inc.id)) return false;
          seenIncidentIds.current.add(inc.id);
          return true;
        });
      } else {
        throw incidentPayload.reason;
      }

      if (latestPayload.status === "fulfilled") {
        const [latest] = toIncidentArray(latestPayload.value).map(normalizeIncident);
        newLatest = latest || null;
      }

      setIncidents((prev) => {
        // Merge new incidents with existing, keeping the most recent
        const merged = [...newIncidents, ...prev.filter((p) => !newIncidents.some((n) => n.id === p.id))];
        return merged.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
      });
      
      if (newLatest) {
        setLatestIncident(newLatest);
      }

      setError("");
      setBackendStatus("connected");
      setLastUpdated(new Date());
    } catch (err) {
      setError(handleApiError(err));
      setBackendStatus("error");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, REFRESH_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const stats = useMemo(() => {
    const active = incidents.filter((incident) => !incident.isResolved);
    const resolved = incidents.filter((incident) => incident.isResolved);
    return {
      activeCount: active.length,
      resolvedCount: resolved.length,
      criticalCount: active.filter((incident) => incident.severity === "critical").length,
    };
  }, [incidents]);

  return {
    incidents,
    latestIncident,
    error,
    isLoading,
    lastUpdated,
    refresh,
    stats,
    backendStatus,
  };
}
