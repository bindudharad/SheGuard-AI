import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState, useMemo } from "react";
import { ArrowLeft, BadgeAlert, Fingerprint, MapPin, PhoneCall, RadioTower, Route, ShieldAlert, Video, X, Users, CreditCard, Brain, Activity, AlertTriangle, Camera, FileText, Clock, Gauge, Battery, Cpu, Camera as CameraIcon, CheckCircle2, Send, Flag } from "lucide-react";
import { scaleIn } from "../animations/variants";
import ConfidenceGraph from "../components/ConfidenceGraph";
import DetailMap from "../components/DetailMap";
import IncidentTimeline from "../components/IncidentTimeline";
import StatusBadge from "../components/StatusBadge";
import { confidenceLabel, formatTime } from "../lib/incidents";
import { getEvidence, getSecureEvidence, getUserProfile, getUserContacts, getCameras, getLiveTracking, getTrackingHistory, acknowledgeEmergency, respondEmergency, resolveEmergency } from "../services/api";

export default function IncidentDetailPage({ incident, onClose }) {
  const [evidence, setEvidence] = useState(null);
  const [contacts, setContacts] = useState(null);
  const [profile, setProfile] = useState(null);
  const [cameras, setCameras] = useState([]);
  const [tracking, setTracking] = useState(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);

  const following = incident?.following_relationship || {};
  const isFollowing = following.target_id != null;
  const riskScore = incident?.risk_score || incident?.threat_score || 0;
  const riskLevel = incident?.risk_level || incident?.threat_level || "SAFE";
  const behaviors = incident?.behaviors || [];
  const agentTimeline = incident?.agent_timeline || [];
  const x402Meta = incident?.x402_metadata || null;
  const intelligenceResult = incident?.intelligence_result || null;

  // Load additional data when incident changes
  useEffect(() => {
    if (!incident) return;
    
    const loadData = async () => {
      setLoading(true);
      try {
        // Load evidence
        if (incident.id) {
          try {
            const evidenceData = await getEvidence(incident.id);
            setEvidence(evidenceData);
          } catch (err) {
            console.warn("Failed to load evidence:", err);
            setEvidence(null);
          }
        }

        // Load user profile and contacts if user_id available
        if (incident.userId || incident.user_id) {
          const userId = incident.userId || incident.user_id;
          try {
            const [profileData, contactsData] = await Promise.all([
              getUserProfile(userId),
              getUserContacts(userId),
            ]);
            setProfile(profileData);
            setContacts(contactsData);
          } catch (err) {
            console.warn("Failed to load user data:", err);
          }
        }

        // Load cameras
        try {
          const camerasData = await getCameras();
          setCameras(camerasData?.cameras || []);
        } catch (err) {
          console.warn("Failed to load cameras:", err);
          setCameras([]);
        }

        // Load tracking if session_id available
        if (incident.sessionId || incident.emergency_session_id) {
          const sessionId = incident.sessionId || incident.emergency_session_id;
          try {
            const trackingData = await getLiveTracking(sessionId);
            setTracking(trackingData);
          } catch (err) {
            console.warn("Failed to load tracking:", err);
            setTracking(null);
          }
        }
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [incident]);

  const getRiskColor = (level) => {
    switch (level) {
      case "EMERGENCY": return "text-red-400 border-red-400/40 bg-red-400/15";
      case "CRITICAL": return "text-orange-400 border-orange-400/40 bg-orange-400/15";
      case "HIGH": return "text-yellow-400 border-yellow-400/40 bg-yellow-400/15";
      case "WARNING": return "text-blue-400 border-blue-400/40 bg-blue-400/15";
      default: return "text-green-400 border-green-400/40 bg-green-400/15";
    }
  };

  const nearbyCameras = useMemo(() => {
    if (!cameras.length || !incident?.latitude || !incident?.longitude) return [];
    return cameras
      .filter((c) => c.latitude && c.longitude)
      .map((c) => {
        const distance = calculateDistance(incident.latitude, incident.longitude, c.latitude, c.longitude);
        return { ...c, distance: Math.round(distance) };
      })
      .sort((a, b) => a.distance - b.distance)
      .slice(0, 10);
  }, [cameras, incident]);

  // Emergency response actions
  const handleAcknowledge = async () => {
    if (!incident?.sessionId && !incident?.emergency_session_id) return;
    const sessionId = incident.sessionId || incident.emergency_session_id;
    setActionLoading("acknowledge");
    try {
      await acknowledgeEmergency(sessionId);
      // Refresh incident data
      window.location.reload();
    } catch (err) {
      console.error("Failed to acknowledge emergency:", err);
      alert("Failed to acknowledge: " + err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRespond = async () => {
    if (!incident?.sessionId && !incident?.emergency_session_id) return;
    const sessionId = incident.sessionId || incident.emergency_session_id;
    setActionLoading("respond");
    try {
      await respondEmergency(sessionId);
      window.location.reload();
    } catch (err) {
      console.error("Failed to respond to emergency:", err);
      alert("Failed to respond: " + err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleResolve = async () => {
    if (!incident?.sessionId && !incident?.emergency_session_id) return;
    const sessionId = incident.sessionId || incident.emergency_session_id;
    if (!confirm("Are you sure you want to resolve this emergency? This will mark the session as resolved.")) {
      return;
    }
    setActionLoading("resolve");
    try {
      await resolveEmergency(sessionId);
      window.location.reload();
    } catch (err) {
      console.error("Failed to resolve emergency:", err);
      alert("Failed to resolve: " + err.message);
    } finally {
      setActionLoading(null);
    }
  };

  if (!incident) return null;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-[1000] overflow-y-auto bg-command-950 text-white"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_30%_0%,rgba(255,49,72,.18),transparent_34rem)]" />
        <motion.div variants={scaleIn} initial="hidden" animate="show" exit="exit" className="relative min-h-screen">
          <header className="sticky top-0 z-20 border-b border-white/10 bg-command-950/78 backdrop-blur-2xl">
            <div className="mx-auto flex h-20 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6">
              <button onClick={onClose} className="inline-flex h-11 items-center gap-2 rounded-full border border-white/10 bg-white/[0.055] px-4 text-sm font-bold text-white transition hover:border-alert-500/40">
                <ArrowLeft className="h-4 w-4" />
                Back to feed
              </button>
              <button onClick={onClose} className="flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-white/[0.055] transition hover:border-alert-500/40" aria-label="Close">
                <X className="h-5 w-5" />
              </button>
            </div>
          </header>

          <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
            {/* Emergency Response Actions Header */}
            {(incident.sessionId || incident.emergency_session_id) && incident.emergencySession?.status !== "resolved" && (
              <div className="mb-6 rounded-[1.7rem] border border-alert-500/30 bg-alert-500/10 p-4 backdrop-blur-xl">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex items-center gap-2 text-sm text-alert-100">
                    <Flag className="h-4 w-4" />
                    <span>Emergency Session: {incident.emergencySession?.status || "ACTIVE"}</span>
                  </div>
                  {incident.emergencySession?.status === "active" && (
                    <>
                      <button
                        onClick={handleAcknowledge}
                        disabled={actionLoading === "acknowledge"}
                        className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/15 px-4 py-2 text-sm font-medium text-emerald-100 hover:bg-emerald-500/25 transition disabled:opacity-50"
                      >
                        <CheckCircle2 className="h-4 w-4" />
                        {actionLoading === "acknowledge" ? "Acknowledging..." : "Acknowledge"}
                      </button>
                      <button
                        onClick={handleRespond}
                        disabled={actionLoading === "respond"}
                        className="flex items-center gap-2 rounded-xl border border-blue-500/30 bg-blue-500/15 px-4 py-2 text-sm font-medium text-blue-100 hover:bg-blue-500/25 transition disabled:opacity-50"
                      >
                        <Send className="h-4 w-4" />
                        {actionLoading === "respond" ? "Responding..." : "Start Response"}
                      </button>
                    </>
                  )}
                  {incident.emergencySession?.status === "acknowledged" && (
                    <button
                      onClick={handleRespond}
                      disabled={actionLoading === "respond"}
                      className="flex items-center gap-2 rounded-xl border border-blue-500/30 bg-blue-500/15 px-4 py-2 text-sm font-medium text-blue-100 hover:bg-blue-500/25 transition disabled:opacity-50"
                    >
                      <Send className="h-4 w-4" />
                      {actionLoading === "respond" ? "Responding..." : "Start Response"}
                    </button>
                  )}
                  {(incident.emergencySession?.status === "acknowledged" || incident.emergencySession?.status === "responding") && (
                    <button
                      onClick={handleResolve}
                      disabled={actionLoading === "resolve"}
                      className="flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/15 px-4 py-2 text-sm font-medium text-amber-100 hover:bg-amber-500/25 transition disabled:opacity-50"
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      {actionLoading === "resolve" ? "Resolving..." : "Resolve Emergency"}
                    </button>
                  )}
                  {incident.emergencySession?.status === "responding" && (
                    <span className="flex items-center gap-2 text-sm text-emerald-400">
                      <CheckCircle2 className="h-4 w-4" />
                      Response in progress
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* 1. Incident Overview */}
            <section className="grid gap-8 lg:grid-cols-[minmax(0,1.2fr)_minmax(360px,.8fr)]">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge tone={incident.isResolved ? "resolved" : "live"} pulse={!incident.isResolved}>
                    {incident.isResolved ? "Resolved" : "Live"}
                  </StatusBadge>
                  <StatusBadge tone={incident.severity === "critical" ? "high risk" : "active"}>
                    {incident.severity === "critical" ? "High Risk" : incident.emergencyStatus}
                  </StatusBadge>
                  <StatusBadge tone="active">{confidenceLabel(incident.confidence)}</StatusBadge>
                  <span className={`rounded-full border px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.12em] ${getRiskColor(riskLevel)}`}>
                    {riskLevel}
                  </span>
                </div>
                <h1 className="mt-5 max-w-5xl text-4xl font-black leading-[0.95] tracking-tight text-white sm:text-6xl lg:text-7xl">
                  {incident.title}
                </h1>
                <p className="mt-5 max-w-3xl text-lg leading-8 text-slate-300">{incident.description}</p>
              </div>

              <div className="rounded-[1.7rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-2xl">
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Incident Snapshot</p>
                <div className="mt-5 grid gap-3">
                  <Meta icon={MapPin} label="Location" value={incident.address} />
                  <Meta icon={Route} label="Coordinates" value={incident.latitude && incident.longitude ? `${incident.latitude}, ${incident.longitude}` : "GPS pending"} />
                  <Meta icon={RadioTower} label="Tracking session" value={incident.sessionId || "Unavailable"} />
                  <Meta icon={Fingerprint} label="Incident ID" value={incident.id} />
                  <Meta icon={ShieldAlert} label="Threat Risk" value={`${riskScore}/100 (${riskLevel})`} />
                  <Meta icon={BadgeAlert} label="AI Provider" value={incident.ai_provider || "Unknown"} />
                </div>
              </div>
            </section>

            {/* 2. Media / Evidence Preview */}
            <section className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(320px,.65fr)]">
              <div className="overflow-hidden rounded-[1.8rem] border border-white/10 bg-black shadow-panel">
                {incident.videoUrl ? (
                  <video src={incident.videoUrl} poster={incident.thumbnailUrl} controls autoPlay className="aspect-video w-full bg-black object-contain" />
                ) : incident.thumbnailUrl ? (
                  <img src={incident.thumbnailUrl} alt={incident.title} className="aspect-video w-full object-cover" />
                ) : (
                  <div className="flex aspect-video items-center justify-center text-slate-500">
                    <Video className="h-16 w-16" />
                    <span className="ml-3">No media available</span>
                  </div>
                )}
              </div>
              <div className="grid gap-6">
                <ConfidenceGraph value={incident.confidence} />
                <EmergencyContacts incident={incident} contacts={contacts?.contacts} />
              </div>
            </section>

            {/* 3. Victim / User Information */}
            {profile && (
              <section className="mt-6 rounded-[1.7rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
                <h3 className="flex items-center gap-2 text-xl font-black tracking-tight text-white">
                  <Users className="h-6 w-6 text-alert-500" />
                  Victim Information
                </h3>
                <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <Meta icon={Users} label="Name" value={profile.full_name || "Unknown"} />
                  <Meta icon={PhoneCall} label="Phone" value={maskPhone(profile.phone_number) || "Unknown"} />
                  <Meta icon={Fingerprint} label="User ID" value={profile.user_id || "Unknown"} />
                  <Meta icon={Clock} label="Registered" value={profile.created_at ? formatTime(profile.created_at) : "Unknown"} />
                </div>
              </section>
            )}

            {/* 4. Emergency Session */}
            {incident.emergencySession && (
              <section className="mt-6 rounded-[1.7rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
                <h3 className="flex items-center gap-2 text-xl font-black tracking-tight text-white">
                  <RadioTower className="h-6 w-6 text-alert-500" />
                  Emergency Session
                </h3>
                <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <Meta icon={RadioTower} label="Session ID" value={incident.emergencySession.session_id} />
                  <Meta icon={BadgeAlert} label="Status" value={incident.emergencySession.status} />
                  <Meta icon={ShieldAlert} label="Trigger" value={incident.emergencySession.trigger_source} />
                  <Meta icon={Clock} label="Started" value={incident.emergencySession.started_at ? formatTime(incident.emergencySession.started_at) : "Unknown"} />
                </div>
              </section>
            )}

            {/* 5. Location */}
            <section className="mt-6 grid gap-6 lg:grid-cols-2">
              <div className="rounded-[1.7rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
                <h3 className="flex items-center gap-2 text-xl font-black tracking-tight text-white">
                  <MapPin className="h-6 w-6 text-alert-500" />
                  Live Location
                </h3>
                {incident.latitude && incident.longitude ? (
                  <div className="mt-4 grid gap-4 sm:grid-cols-2">
                    <Meta icon={MapPin} label="Latitude" value={Number(incident.latitude).toFixed(6)} />
                    <Meta icon={MapPin} label="Longitude" value={Number(incident.longitude).toFixed(6)} />
                    {tracking?.accuracy && <Meta icon={Gauge} label="Accuracy" value={`${tracking.accuracy}m`} />}
                    {tracking?.speed && <Meta icon={Activity} label="Speed" value={`${tracking.speed} m/s`} />}
                    {tracking?.battery && <Meta icon={Battery} label="Battery" value={`${tracking.battery}%`} />}
                    {tracking?.updated_at && <Meta icon={Clock} label="Last Update" value={formatTime(tracking.updated_at)} />}
                  </div>
                ) : (
                  <div className="mt-4 flex items-center gap-3 text-amber-400">
                    <AlertTriangle className="h-5 w-5" />
                    <p className="text-sm">Location data unavailable</p>
                  </div>
                )}
              </div>

              {/* 6. Live Tracking */}
              <div className="rounded-[1.7rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
                <h3 className="flex items-center gap-2 text-xl font-black tracking-tight text-white">
                  <Route className="h-6 w-6 text-alert-500" />
                  Live Tracking
                </h3>
                {tracking ? (
                  <div className="mt-4 grid gap-4 sm:grid-cols-2">
                    <Meta icon={Route} label="Session ID" value={tracking.session_id || incident.sessionId} />
                    <Meta icon={BadgeAlert} label="Status" value={tracking.status || "Unknown"} />
                    <Meta icon={Activity} label="Speed" value={`${tracking.speed || 0} m/s`} />
                    <Meta icon={Gauge} label="Accuracy" value={`${tracking.accuracy || 0}m`} />
                    <Meta icon={Clock} label="Started" value={tracking.started_at ? formatTime(tracking.started_at) : "Unknown"} />
                    <Meta icon={Clock} label="Last Update" value={tracking.updated_at ? formatTime(tracking.updated_at) : "Unknown"} />
                  </div>
                ) : (
                  <div className="mt-4 flex items-center gap-3 text-slate-400">
                    <Route className="h-5 w-5" />
                    <p className="text-sm">No active tracking session</p>
                  </div>
                )}
              </div>
            </section>

            {/* 7. CCTV */}
            <section className="mt-6 rounded-[1.7rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
              <h3 className="flex items-center gap-2 text-xl font-black tracking-tight text-white">
                <Camera className="h-6 w-6 text-alert-500" />
                Nearby CCTV Cameras
              </h3>
              {nearbyCameras.length > 0 ? (
                <div className="mt-4 space-y-2 max-h-64 overflow-y-auto">
                  {nearbyCameras.map((camera) => (
                    <div key={camera.camera_id} className="flex items-center justify-between p-3 rounded-xl border border-white/10 bg-black/24">
                      <div>
                        <p className="font-medium text-white">{camera.camera_name || `CCTV-${camera.camera_id}`}</p>
                        <p className="text-xs text-slate-400">{camera.distance}m away • {camera.online_status || "unknown"}</p>
                      </div>
                      <div className={`flex h-2 w-2 rounded-full ${camera.online_status === "online" ? "bg-emerald-400" : "bg-slate-600"}`} />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-4 flex items-center gap-3 text-slate-400">
                  <Camera className="h-5 w-5" />
                  <p className="text-sm">No cameras in range</p>
                </div>
              )}
            </section>

            {/* 8. AI Analysis */}
            <section className="mt-6 grid gap-6 lg:grid-cols-2">
              <div className="rounded-[1.7rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
                <h3 className="flex items-center gap-2 text-xl font-black tracking-tight text-white">
                  <Brain className="h-6 w-6 text-alert-500" />
                  AI Threat Analysis
                </h3>
                <div className="mt-4 space-y-3">
                  <Meta icon={ShieldAlert} label="Threat Score" value={`${riskScore}/100`} />
                  <Meta icon={BadgeAlert} label="Threat Level" value={riskLevel} />
                  <Meta icon={Fingerprint} label="Confidence" value={confidenceLabel(incident.confidence)} />
                  <Meta icon={Cpu} label="AI Provider" value={incident.ai_provider || "Unknown"} />
                  {incident.ai_summary && (
                    <div className="rounded-xl border border-white/10 bg-black/24 p-4">
                      <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">AI Summary</p>
                      <p className="mt-2 text-sm text-slate-300">{incident.ai_summary}</p>
                    </div>
                  )}
                  {incident.explanation && (
                    <div className="rounded-xl border border-white/10 bg-black/24 p-4">
                      <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Explanation</p>
                      <p className="mt-2 text-sm text-slate-300">{incident.explanation}</p>
                    </div>
                  )}
                  {incident.risk_reasons && (
                    <div className="rounded-xl border border-white/10 bg-black/24 p-4">
                      <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Risk Reasons</p>
                      <pre className="mt-2 text-xs text-slate-300 overflow-auto">{JSON.stringify(incident.risk_reasons, null, 2)}</pre>
                    </div>
                  )}
                </div>
              </div>

              {/* 9. Evidence */}
              <div className="rounded-[1.7rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
                <h3 className="flex items-center gap-2 text-xl font-black tracking-tight text-white">
                  <FileText className="h-6 w-6 text-alert-500" />
                  Evidence
                </h3>
                {evidence?.evidence?.length > 0 ? (
                  <div className="mt-4 space-y-3">
                    {evidence.evidence.map((ev, idx) => (
                      <div key={ev.evidence_id || idx} className="rounded-xl border border-white/10 bg-black/24 p-4">
                        <div className="flex items-center justify-between">
                          <p className="font-medium text-white">Evidence #{ev.evidence_id || idx + 1}</p>
                          {ev.cctv_source && <span className="text-xs text-slate-400">{ev.cctv_source}</span>}
                        </div>
                        <div className="mt-2 flex gap-2">
                          {ev.image_url && (
                            <a href={ev.image_url} target="_blank" rel="noopener noreferrer" className="text-xs text-cyan-400 hover:underline">
                              View Image
                            </a>
                          )}
                          {ev.video_url && (
                            <a href={ev.video_url} target="_blank" rel="noopener noreferrer" className="text-xs text-cyan-400 hover:underline">
                              View Video
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="mt-4 flex items-center gap-3 text-slate-400">
                    <FileText className="h-5 w-5" />
                    <p className="text-sm">No evidence files available</p>
                  </div>
                )}
              </div>
            </section>

            {/* 10. Timeline */}
            <section className="mt-6 grid gap-6 lg:grid-cols-2">
              <DetailMap
                incidents={[incident]}
                trackingSessions={[]}
                selectedSession={null}
                center={incident.latitude && incident.longitude ? [Number(incident.latitude), Number(incident.longitude)] : [20.5937, 78.9629]}
                zoom={incident.latitude && incident.longitude ? 15 : 5}
              />
              <IncidentTimeline incident={incident} />
            </section>

            {/* 11. Emergency Contacts */}
            {contacts?.contacts?.length > 0 && (
              <section className="mt-6 rounded-[1.7rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
                <h3 className="flex items-center gap-2 text-xl font-black tracking-tight text-white">
                  <PhoneCall className="h-6 w-6 text-alert-500" />
                  Emergency Contacts
                </h3>
                <div className="mt-4 space-y-3">
                  {contacts.contacts.map((contact) => (
                    <div key={contact.contact_id} className="rounded-xl border border-white/10 bg-black/24 p-4">
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-white">{contact.contact_name}</p>
                        <span className="text-xs text-slate-400 capitalize">{contact.relation}</span>
                      </div>
                      <p className="mt-1 text-sm text-slate-300">{maskPhone(contact.phone_number)}</p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* 12. Raw Technical Data */}
            <section className="mt-6 rounded-[1.7rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
              <h3 className="text-xl font-black tracking-tight text-white">Full Technical Data</h3>
              <pre className="thin-scrollbar mt-4 max-h-80 overflow-auto rounded-[1rem] border border-white/10 bg-black/40 p-4 text-xs leading-6 text-slate-300">
                {JSON.stringify(incident.raw || incident, null, 2)}
              </pre>
            </section>
          </main>
        </motion.div>
      </motion.div>
    </AnimatePresence>
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

function maskPhone(phone) {
  if (!phone) return "Unknown";
  const str = String(phone);
  if (str.length <= 4) return "****";
  return str.slice(0, -4).replace(/\d/g, "*") + str.slice(-4);
}

function Meta({ icon: Icon, label, value }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/24 p-4">
      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-slate-500">
        <Icon className="h-4 w-4 text-alert-500" />
        {label}
      </div>
      <p className="mt-2 break-words text-sm font-bold text-white">{value || "Unavailable"}</p>
    </div>
  );
}

function EmergencyContacts({ incident, contacts }) {
  if (contacts?.length > 0) {
    return (
      <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-alert-500/14 text-alert-500">
            <PhoneCall className="h-5 w-5" />
          </div>
          <h3 className="text-xl font-black tracking-tight text-white">Emergency Contacts</h3>
        </div>
        <div className="mt-4 space-y-2 text-sm leading-6 text-slate-300">
          {contacts.map((contact) => (
            <p key={contact.contact_id}>
              {contact.contact_name} ({contact.relation}): {maskPhone(contact.phone_number)}
            </p>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-alert-500/14 text-alert-500">
          <PhoneCall className="h-5 w-5" />
        </div>
        <h3 className="text-xl font-black tracking-tight text-white">Emergency Contacts</h3>
      </div>
      <div className="mt-4 space-y-2 text-sm leading-6 text-slate-300">
        <p>{incident.contact_name || incident.emergency_contact || "Nearest response desk"}</p>
        <p>{incident.phone || incident.contact_phone || "112 / Police Control Room"}</p>
      </div>
    </div>
  );
}
