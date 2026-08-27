import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import { useIncidents } from "./useIncidents";
import { useRealtime } from "./useRealtime";
import { normalizeIncident } from "../lib/incidents";
import { CONNECTION_STATUS, REALTIME_EVENTS } from "../config";
import { getUserProfile, getLiveTracking, getTrackingHistory, getCameras } from "../services/api";

export function useEmergencySessions() {
  const { 
    incidents, 
    error: incidentsError, 
    isLoading, 
    refresh: refreshIncidents, 
    stats 
  } = useIncidents();
  
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [emergencySessions, setEmergencySessions] = useState([]);
  const [trackingSessions, setTrackingSessions] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [realtimeStatus, setRealtimeStatus] = useState(CONNECTION_STATUS.DISCONNECTED);
  const sessionRefs = useRef(new Map());
  const processedEventIds = useRef(new Set());

  // Process incidents into emergency sessions
  useEffect(() => {
    const sessions = buildEmergencySessions(incidents);
    setEmergencySessions(sessions);
    setTrackingSessions(buildTrackingSessions(sessions));
  }, [incidents]);

  // Handle realtime events
  const handleRealtimeMessage = useCallback((message) => {
    if (!message || !message.event) return;
    
    // Deduplicate events
    const eventId = message.payload?.incident_id || message.payload?.session_id || message.payload?.event_id;
    if (eventId && processedEventIds.current.has(`${message.event}:${eventId}`)) {
      return;
    }
    if (eventId) {
      processedEventIds.current.add(`${message.event}:${eventId}`);
      // Keep set size reasonable
      if (processedEventIds.current.size > 1000) {
        const first = processedEventIds.current.values().next().value;
        processedEventIds.current.delete(first);
      }
    }

    const { event, payload } = message;
    
    switch (event) {
      case REALTIME_EVENTS.INCIDENT_CREATED:
      case REALTIME_EVENTS.INCIDENT_UPDATED:
      case REALTIME_EVENTS.POLICE_ALERT:
      case REALTIME_EVENTS.INCIDENT_NEW:
        handleIncidentCreated(payload);
        break;
        
      case REALTIME_EVENTS.EMERGENCY_STARTED:
        handleEmergencyStarted(payload);
        break;
        
      case REALTIME_EVENTS.EMERGENCY_UPDATED:
        handleEmergencyUpdated(payload);
        break;
        
      case REALTIME_EVENTS.TRACKING_UPDATE:
        handleTrackingUpdate(payload);
        break;
        
      case REALTIME_EVENTS.EMERGENCY_ACKNOWLEDGED:
      case REALTIME_EVENTS.EMERGENCY_RESPONDING:
      case REALTIME_EVENTS.EMERGENCY_RESOLVED:
        handleEmergencyStatusChange(payload, event);
        break;
        
      case REALTIME_EVENTS.THREAT_ESCALATION:
        handleThreatEscalation(payload);
        break;
        
      case REALTIME_EVENTS.CCTV_OFFLINE:
        handleCctvOffline(payload);
        break;
        
      case REALTIME_EVENTS.AI_DETECTION:
        handleAiDetection(payload);
        break;
        
      default:
        console.debug("Unhandled realtime event:", event, payload);
    }
  }, [refreshIncidents]);

  // Realtime connection with status tracking
  useRealtime({
    onMessage: handleRealtimeMessage,
    enabled: true,
    onStatusChange: setRealtimeStatus,
  });

  // Build emergency sessions from incidents
  function buildEmergencySessions(incidentList) {
    const sessionMap = new Map();
    
    for (const incident of incidentList) {
      const sessionId = incident.sessionId || incident.emergency_session_id || incident.emergencySession?.session_id || incident.id;
      const userId = incident.userId || incident.user_id || incident.linked_user?.user_id || incident.emergencySession?.user_id;
      const emergencySession = incident.emergencySession || incident.emergency_session;
      
      if (!sessionMap.has(sessionId)) {
        sessionMap.set(sessionId, {
          sessionId,
          userId,
          fullName: incident.victimName || incident.full_name || incident.linked_user?.full_name || `User ${userId}`,
          phoneNumber: incident.maskedPhone || incident.phone_number,
          status: emergencySession?.status || "active",
          threatLevel: incident.threat_level || emergencySession?.threat_level || "UNKNOWN",
          threatScore: incident.threat_score || emergencySession?.threat_score || 0,
          latestIncident: incident,
          incidents: [incident],
          location: emergencySession?.location || incident,
          startedAt: emergencySession?.started_at || incident.created_at,
          liveTrackingUrl: emergencySession?.live_tracking_url || `/track/${sessionId}`,
        });
      } else {
        const session = sessionMap.get(sessionId);
        session.incidents.push(incident);
        if (incident.threat_score > session.threatScore) {
          session.threatScore = incident.threat_score;
          session.threatLevel = incident.threat_level;
        }
        session.latestIncident = incident;
      }
    }
    
    return Array.from(sessionMap.values());
  }

  function buildTrackingSessions(sessions) {
    return sessions
      .filter(s => s.location?.latitude && s.location?.longitude)
      .map(s => ({
        sessionId: s.sessionId,
        userId: s.userId,
        fullName: s.fullName,
        phoneNumber: s.phoneNumber,
        latitude: s.location.latitude,
        longitude: s.location.longitude,
        speed: s.location.speed,
        battery: s.location.battery,
        accuracy: s.location.accuracy,
        lastUpdate: s.location.last_update_at || s.location.timestamp,
        status: s.status,
        threatLevel: s.threatLevel,
      }));
  }

  // Handlers for realtime events
  function handleIncidentCreated(payload) {
    console.debug("Incident created:", payload);
    refreshIncidents();
  }

  function handleEmergencyStarted(payload) {
    console.debug("Emergency started:", payload);
    refreshIncidents();
  }

  function handleEmergencyUpdated(payload) {
    console.debug("Emergency updated:", payload);
    refreshIncidents();
  }

  function handleTrackingUpdate(payload) {
    const sessionId = payload.session_id || payload.sessionId;
    if (sessionId) {
      setEmergencySessions(prev => prev.map(s => 
        s.sessionId === sessionId 
          ? { ...s, location: { ...s.location, ...payload.location }, threatLevel: payload.threat_level || s.threatLevel }
          : s
      ));
      setTrackingSessions(prev => prev.map(s => 
        s.sessionId === sessionId 
          ? { ...s, latitude: payload.location?.latitude, longitude: payload.location?.longitude, speed: payload.location?.speed, battery: payload.location?.battery, accuracy: payload.location?.accuracy, lastUpdate: payload.timestamp }
          : s
      ));
    }
  }

  function handleEmergencyStatusChange(payload, event) {
    console.debug("Emergency status change:", event, payload);
    refreshIncidents();
  }

  function handleThreatEscalation(payload) {
    console.debug("Threat escalation:", payload);
    refreshIncidents();
  }

  function handleCctvOffline(payload) {
    console.debug("CCTV offline:", payload);
    refreshIncidents();
  }

  function handleAiDetection(payload) {
    console.debug("AI detection:", payload);
    refreshIncidents();
  }

  const activeCount = useMemo(() => emergencySessions.filter(s => s.status === "active").length, [emergencySessions]);
  const highRiskCount = useMemo(() => emergencySessions.filter(s => s.threatScore >= 7).length, [emergencySessions]);
  const selectedSession = emergencySessions.find(s => s.sessionId === selectedSessionId);

  return {
    emergencySessions,
    activeCount,
    highRiskCount,
    trackingSessions,
    selectedSessionId,
    selectedSession,
    selectSession: setSelectedSessionId,
    notifications,
    unreadCount,
    realtimeStatus,
    backendError: incidentsError,
    isLoading,
    refreshIncidents,
  };
}
