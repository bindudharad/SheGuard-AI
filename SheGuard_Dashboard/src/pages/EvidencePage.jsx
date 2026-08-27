import { useEffect, useState, useMemo } from "react";
import { Search, FileText, Video, Image, Download, Play, Eye, RefreshCw, AlertTriangle, Filter } from "lucide-react";
import { motion } from "framer-motion";
import { useEmergencySessions } from "../hooks/useEmergencySessions";
import { getEvidence, getSecureEvidence, getMediaUrl } from "../services/api";
import { formatTime } from "../lib/incidents";

export default function EvidencePage() {
  const { selectedSession, emergencySessions } = useEmergencySessions();
  const [selectedIncidentId, setSelectedIncidentId] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [secureEvidence, setSecureEvidence] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mediaStatus, setMediaStatus] = useState({}); // Track media load status

  // Get all incidents from emergency sessions
  const allIncidents = useMemo(() => {
    const incidents = [];
    emergencySessions.forEach((session) => {
      if (session.latestIncident) {
        incidents.push({
          id: session.latestIncident.id,
          title: session.latestIncident.title,
          sessionId: session.sessionId,
          victimName: session.fullName,
        });
      }
    });
    return incidents;
  }, [emergencySessions]);

  // Load evidence for selected incident or selected session's incident
  useEffect(() => {
    const incidentId = selectedIncidentId || selectedSession?.latestIncident?.id;
    if (!incidentId) return;

    const loadEvidence = async () => {
      setLoading(true);
      setError(null);
      try {
        const [evidenceData, secureData] = await Promise.allSettled([
          getEvidence(incidentId),
          getSecureEvidence(incidentId),
        ]);
        
        setEvidence(evidenceData.status === "fulfilled" ? evidenceData.value : null);
        setSecureEvidence(secureData.status === "fulfilled" ? secureData.value : null);
      } catch (err) {
        setError("Failed to load evidence: " + (err.message || "Unknown error"));
      } finally {
        setLoading(false);
      }
    };

    loadEvidence();
    const interval = setInterval(loadEvidence, 30000);
    return () => clearInterval(interval);
  }, [selectedIncidentId, selectedSession]);

  const allEvidence = useMemo(() => {
    const items = [];
    if (evidence?.evidence) {
      items.push(...evidence.evidence.map((e) => ({ ...e, source: "standard" })));
    }
    if (evidence?.evidence_records) {
      items.push(...evidence.evidence_records.map((e) => ({ ...e, source: "record" })));
    }
    if (secureEvidence?.evidence) {
      items.push(...secureEvidence.evidence.map((e) => ({ ...e, source: "secure" })));
    }
    return items;
  }, [evidence, secureEvidence]);

  const getEvidenceType = (item) => {
    if (item.evidence_type) return item.evidence_type.toUpperCase();
    if (item.video_path || item.video_url) return "VIDEO";
    if (item.image_path || item.image_url) return "IMAGE";
    if (item.metadata_path) return "METADATA";
    if (item.pre_event_video_path) return "PRE-EVENT VIDEO";
    return "UNKNOWN";
  };

  const getMediaUrlForItem = (item) => {
    if (item.image_url) return item.image_url;
    if (item.video_url) return item.video_url;
    if (item.public_url) return item.public_url;
    if (item.image_path) return getMediaUrl(item.image_path);
    if (item.video_path) return getMediaUrl(item.video_path);
    if (item.file_path) return getMediaUrl(item.file_path);
    if (item.metadata_path) return getMediaUrl(item.metadata_path);
    return null;
  };

  return (
    <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8">
      <section className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/12 px-4 py-2 text-xs font-black uppercase tracking-[0.16em] text-blue-100">
            <FileText className="h-4 w-4" />
            Evidence Center
          </div>
          <h1 className="mt-4 text-4xl font-black tracking-tight text-white sm:text-5xl">
            Digital Evidence Management
          </h1>
          <p className="mt-2 text-lg text-slate-300">
            Secure access to all incident evidence, media, and forensic data
          </p>
        </div>

        {/* Incident Selector */}
        {allIncidents.length > 0 && (
          <div className="mb-6">
            <label className="block text-xs font-medium text-slate-400 mb-2">Select Incident</label>
            <select
              value={selectedIncidentId || selectedSession?.latestIncident?.id || ""}
              onChange={(e) => setSelectedIncidentId(e.target.value)}
              className="w-full max-w-md h-12 rounded-xl border border-white/10 bg-white/[0.055] text-white outline-none focus:border-alert-500/50 px-4"
            >
              <option value="">Select an incident...</option>
              {allIncidents.map((incident) => (
                <option key={incident.id} value={incident.id}>
                  #{incident.id} - {incident.title} ({incident.victimName})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mb-6 rounded-xl border border-alert-500/30 bg-alert-500/12 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        )}

        {/* Evidence Grid */}
        {loading ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-80 animate-pulse rounded-[1.4rem] border border-white/10 bg-white/[0.055]" />
            ))}
          </div>
        ) : allEvidence.length > 0 ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {allEvidence.map((item, index) => {
              const mediaUrl = getMediaUrlForItem(item);
              const type = getEvidenceType(item);
              const isVideo = type.includes("VIDEO");
              const isImage = type.includes("IMAGE");
              
              return (
                <motion.div
                  key={item.evidence_id || item.record_id || index}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">
                        {type}
                      </p>
                      <p className="mt-1 text-sm text-slate-400">
                        {item.source === "secure" ? "Secure Evidence" : item.source === "record" ? "Evidence Record" : "Standard Evidence"}
                      </p>
                    </div>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${
                      item.confidence > 70 ? "bg-red-500/20 text-red-400" :
                      item.confidence > 40 ? "bg-amber-500/20 text-amber-400" :
                      "bg-slate-500/20 text-slate-400"
                    }`}>
                      {item.confidence || 0}% conf
                    </span>
                  </div>

                  {/* Media Preview */}
                  <div className="aspect-video rounded-xl bg-black/40 overflow-hidden mb-4 flex items-center justify-center">
                    {mediaUrl ? (
                      isVideo ? (
                        <video 
                          src={mediaUrl} 
                          controls 
                          className="w-full h-full object-contain"
                          onError={() => setMediaStatus((prev) => ({ ...prev, [index]: "error" }))}
                        />
                      ) : isImage ? (
                        <img 
                          src={mediaUrl} 
                          alt="Evidence" 
                          className="w-full h-full object-contain"
                          onError={() => setMediaStatus((prev) => ({ ...prev, [index]: "error" }))}
                        />
                      ) : (
                        <div className="text-center text-slate-500">
                          <FileText className="h-12 w-12 mx-auto" />
                          <p className="mt-2 text-xs">Metadata File</p>
                        </div>
                      )
                    ) : (
                      <div className="text-center text-slate-500">
                        <AlertTriangle className="h-12 w-12 mx-auto" />
                        <p className="mt-2 text-xs">No media file</p>
                      </div>
                    )}
                  </div>

                  {/* Media Status */}
                  {mediaStatus[index] === "error" && (
                    <div className="mb-4 flex items-center gap-2 text-xs text-amber-400">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      Media file not available or inaccessible
                    </div>
                  )}

                  {/* Metadata */}
                  <div className="space-y-1 text-xs text-slate-400">
                    {item.camera_id && <p>Camera: {item.camera_id}</p>}
                    {item.cctv_source && <p>Source: {item.cctv_source}</p>}
                    {item.captured_at && <p>Captured: {formatTime(item.captured_at)}</p>}
                    {item.created_at && <p>Created: {formatTime(item.created_at)}</p>}
                    {item.latitude && item.longitude && (
                      <p>Location: {item.latitude.toFixed(4)}, {item.longitude.toFixed(4)}</p>
                    )}
                  </div>

                  {/* Actions */}
                  {mediaUrl && (
                    <div className="mt-4 flex gap-2">
                      <a
                        href={mediaUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.055] py-2 text-xs font-bold text-white hover:border-alert-500/40 transition"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        VIEW
                      </a>
                      <a
                        href={mediaUrl}
                        download
                        className="flex-1 flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.055] py-2 text-xs font-bold text-white hover:border-alert-500/40 transition"
                      >
                        <Download className="h-3.5 w-3.5" />
                        DOWNLOAD
                      </a>
                    </div>
                  )}
                </motion.div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-20">
            <FileText className="h-16 w-16 mx-auto text-slate-600" />
            <h2 className="mt-6 text-xl font-bold text-white">No Evidence Available</h2>
            <p className="mt-2 text-slate-400">
              {selectedIncidentId || selectedSession ? "No evidence files found for this incident" : "Select an incident to view evidence"}
            </p>
          </div>
        )}
      </section>
    </main>
  );
}
