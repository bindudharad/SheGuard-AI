import { MapContainer, Marker, Popup, TileLayer, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import { useEffect, useMemo } from "react";

const victimIcon = L.divIcon({
  className: "",
  html: '<div class="relative flex h-10 w-10 items-center justify-center rounded-full bg-red-500 text-white shadow-[0_0_34px_rgba(255,46,63,.9)]"><div class="absolute h-10 w-10 animate-ping rounded-full bg-red-500/40"></div><span class="relative text-[10px] font-black">SOS</span></div>',
  iconSize: [40, 40],
  iconAnchor: [20, 20],
});

const victimHighIcon = L.divIcon({
  className: "",
  html: '<div class="relative flex h-10 w-10 items-center justify-center rounded-full bg-red-600 text-white shadow-[0_0_34px_rgba(255,46,63,.9)] border-2 border-amber-400"><div class="absolute h-10 w-10 animate-ping rounded-full bg-red-600/40"></div><span class="relative text-[10px] font-black">!</span></div>',
  iconSize: [40, 40],
  iconAnchor: [20, 20],
});

const victimMediumIcon = L.divIcon({
  className: "",
  html: '<div class="relative flex h-10 w-10 items-center justify-center rounded-full bg-amber-500 text-white shadow-[0_0_34px_rgba(245,158,11,.9)]"><div class="absolute h-10 w-10 animate-ping rounded-full bg-amber-500/40"></div><span class="relative text-[10px] font-black">⚠</span></div>',
  iconSize: [40, 40],
  iconAnchor: [20, 20],
});

const victimLowIcon = L.divIcon({
  className: "",
  html: '<div class="flex h-10 w-10 items-center justify-center rounded-full bg-blue-500 text-white"><span class="relative text-[10px] font-black">●</span></div>',
  iconSize: [40, 40],
  iconAnchor: [20, 20],
});

const cameraIcon = L.divIcon({
  className: "",
  html: '<div class="flex h-8 w-8 items-center justify-center rounded-full bg-orange-500 text-white text-xs font-bold">CCTV</div>',
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

const cameraOfflineIcon = L.divIcon({
  className: "",
  html: '<div class="flex h-8 w-8 items-center justify-center rounded-full bg-slate-600 text-white text-xs font-bold">CCTV</div>',
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

const incidentIcon = L.divIcon({
  className: "",
  html: '<div class="flex h-8 w-8 items-center justify-center rounded-full bg-yellow-500 text-black text-xl">⚠</div>',
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

export default function DetailMap({ 
  incidents = [], 
  trackingSessions = [], 
  selectedSession = null,
  center = [20.5937, 78.9629], 
  zoom = 5,
  onViewportChange 
}) {
  const hasPoint = center && center.length === 2;

  // Get victim markers from tracking sessions
  const victimMarkers = useMemo(() => {
    return trackingSessions.map((session) => {
      const threatLevel = session.threat || "LOW";
      let icon = victimIcon;
      if (threatLevel === "HIGH" || threatLevel === "CRITICAL" || threatLevel === "EMERGENCY") {
        icon = victimHighIcon;
      } else if (threatLevel === "MEDIUM" || threatLevel === "WARNING") {
        icon = victimMediumIcon;
      } else if (threatLevel === "LOW") {
        icon = victimLowIcon;
      }
      return (
        <Marker key={session.sessionId} position={[session.latitude, session.longitude]} icon={icon}>
          <Popup>
            <div className="text-white min-w-[200px]">
              <strong>{session.fullName}</strong>
              <br />
              Status: {session.status}
              <br />
              Threat: {session.threat}
              <br />
              GPS: {session.gpsStatus}
              <br />
              Speed: {session.speed?.toFixed(1) || 0} m/s
              <br />
              Last: {session.lastUpdate ? new Date(session.lastUpdate).toLocaleTimeString() : "Unknown"}
            </div>
          </Popup>
        </Marker>
      );
    });
  }, [trackingSessions]);

  // Get CCTV markers from nearby cameras of selected session
  const cameraMarkers = useMemo(() => {
    if (!selectedSession?.nearbyCameras?.length) return [];
    return selectedSession.nearbyCameras
      .filter((c) => c.latitude && c.longitude)
      .map((camera) => (
        <Marker key={camera.camera_id || camera.id} position={[camera.latitude, camera.longitude]} icon={camera.online_status === "online" ? cameraIcon : cameraOfflineIcon}>
          <Popup>
            <div className="text-white min-w-[200px]">
              <strong>{camera.camera_name || camera.camera_id}</strong>
              <br />
              Status: {camera.online_status || "unknown"}
              <br />
              Distance: {camera.distance}m
              <br />
              {camera.rtsp_url && <span>RTSP Available</span>}
            </div>
          </Popup>
        </Marker>
      ));
  }, [selectedSession]);

  // Get incident markers
  const incidentMarkers = useMemo(() => {
    return incidents
      .filter((inc) => Number.isFinite(inc.latitude) && Number.isFinite(inc.longitude))
      .map((incident) => (
        <Marker key={incident.id} position={[incident.latitude, incident.longitude]} icon={incidentIcon}>
          <Popup>
            <div className="text-white min-w-[200px]">
              <strong>{incident.title}</strong>
              <br />
              {incident.incidentType || incident.description}
              <br />
              Confidence: {Math.round((incident.confidence || 0) * 100)}%
              <br />
              Threat: {incident.threat_score || 0}/100
              <br />
              Time: {incident.timestamp ? new Date(incident.timestamp).toLocaleTimeString() : "Unknown"}
            </div>
          </Popup>
        </Marker>
      ));
  }, [incidents]);

  // Get tracking routes (from tracking history)
  const trackingRoutes = useMemo(() => {
    return trackingSessions
      .filter((s) => s.path && s.path.length > 1)
      .map((session) => (
        <Polyline
          key={session.sessionId}
          positions={session.path.map((p) => [p.latitude, p.longitude])}
          color="#2f80ff"
          weight={3}
          opacity={0.8}
          dashArray="5, 10"
        />
      ));
  }, [trackingSessions]);

  return (
    <MapContainer 
      center={center} 
      zoom={zoom} 
      scrollWheelZoom 
      className="h-full w-full z-0"
      whenCreated={onViewportChange ? (map) => {
        map.on("moveend", () => {
          onViewportChange(map.getCenter(), map.getZoom());
        });
      } : undefined}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <MapFocus center={center} zoom={zoom} />
      
      {/* Tracking routes */}
      {trackingRoutes}
      
      {/* CCTV markers */}
      {cameraMarkers}
      
      {/* Incident markers */}
      {incidentMarkers}
      
      {/* Victim markers */}
      {victimMarkers}
    </MapContainer>
  );
}

function MapFocus({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (center && center.length === 2) {
      map.setView(center, zoom);
    }
  }, [center, map, zoom]);
  return null;
}
