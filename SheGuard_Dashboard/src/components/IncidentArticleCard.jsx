import { ArrowUpRight, Clock, MapPin, AlertTriangle, Users, Target, TrendingUp, Shield, CreditCard } from "lucide-react";
import { motion } from "framer-motion";
import { fadeUp } from "../animations/variants";
import { confidenceLabel, formatTime } from "../lib/incidents";
import StatusBadge from "./StatusBadge";
import VideoPreview from "./VideoPreview";

export default function IncidentArticleCard({ incident, featured = false, onView }) {
  // Check if this is a following incident
  const isFollowing = incident.following_relationship && incident.following_relationship.target_id;
  const following = incident.following_relationship || {};
  const riskScore = incident.risk_score || incident.threat_score || 0;
  const riskLevel = incident.risk_level || incident.threat_level || "SAFE";

  const getRiskColor = (level) => {
    switch (level) {
      case "EMERGENCY": return "text-red-400 bg-red-400/20 border-red-400/30";
      case "CRITICAL": return "text-orange-400 bg-orange-400/20 border-orange-400/30";
      case "HIGH": return "text-yellow-400 bg-yellow-400/20 border-yellow-400/30";
      case "WARNING": return "text-blue-400 bg-blue-400/20 border-blue-400/30";
      default: return "text-green-400 bg-green-400/20 border-green-400/30";
    }
  };

  return (
    <motion.article
      variants={fadeUp}
      whileHover={{ y: -8 }}
      className={`group overflow-hidden rounded-[1.7rem] border border-white/10 bg-white/[0.055] shadow-panel backdrop-blur-2xl ${
        featured ? "lg:col-span-2" : ""
      }`}
    >
      <VideoPreview incident={incident} className={featured ? "aspect-[16/9] sm:aspect-[2.05/1]" : "aspect-[16/11]"} />
      <div className="p-5 sm:p-6">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge tone={incident.isResolved ? "resolved" : "live"} pulse={!incident.isResolved}>
            {incident.isResolved ? "Resolved" : "Live"}
          </StatusBadge>
          <StatusBadge tone={incident.severity === "critical" ? "high risk" : "active"}>
            {incident.severity === "critical" ? "High Risk" : incident.emergencyStatus}
          </StatusBadge>
          <span className="rounded-full border border-white/10 bg-white/[0.06] px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.12em] text-slate-200">
            {confidenceLabel(incident.confidence)}
          </span>
          {/* Risk Level Badge */}
          <span className={`rounded-full border px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.12em] ${getRiskColor(riskLevel)}`}>
            {riskLevel}
          </span>
        </div>

        <h2 className={`${featured ? "text-3xl sm:text-5xl" : "text-2xl"} mt-5 max-w-3xl font-black leading-[0.98] tracking-tight text-white`}>
          {incident.title}
        </h2>

        <p className="mt-4 line-clamp-2 max-w-2xl text-sm leading-6 text-slate-300">{incident.description}</p>

        {/* Following Incident Details - F2 */}
        {isFollowing && (
          <div className="mt-6 p-4 rounded-xl border border-white/10 bg-white/[0.03]">
            <div className="flex items-center gap-2 text-sm font-bold text-amber-400 mb-3">
              <Users className="h-4 w-4" />
              SUSPICIOUS FOLLOWING DETECTED
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-slate-500">TARGET</span>
                <div className="font-mono text-white">Track #{following.target_id}</div>
              </div>
              <div>
                <span className="text-slate-500">FOLLOWER</span>
                <div className="font-mono text-white">Track #{following.follower_id}</div>
              </div>
              <div>
                <span className="text-slate-500">Following Score</span>
                <div className="font-bold text-amber-400">{following.score}%</div>
              </div>
              <div>
                <span className="text-slate-500">Duration</span>
                <div className="font-mono text-white">{following.duration_seconds}s</div>
              </div>
              <div>
                <span className="text-slate-500">Distance</span>
                <div className="font-mono text-white">{following.distance_meters}m</div>
              </div>
              <div>
                <span className="text-slate-500">Distance Trend</span>
                <div className="font-mono text-red-400">{following.distance_trend?.toUpperCase()}</div>
              </div>
              <div>
                <span className="text-slate-500">Direction Match</span>
                <div className="font-bold text-green-400">{(following.direction_similarity * 100).toFixed(0)}%</div>
              </div>
              <div>
                <span className="text-slate-500">Trajectory Match</span>
                <div className="font-bold text-green-400">{(following.trajectory_similarity * 100).toFixed(0)}%</div>
              </div>
              <div>
                <span className="text-slate-500">Turn Match</span>
                <div className="font-bold text-green-400">{(following.turn_match_score * 100).toFixed(0)}%</div>
              </div>
              <div className="col-span-2">
                <span className="text-slate-500">Threat Risk</span>
                <div className="font-bold text-red-400 text-lg">{riskScore}/100</div>
              </div>
            </div>
          </div>
        )}

        <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-slate-300">
          <span className="inline-flex min-w-0 items-center gap-2">
            <MapPin className="h-4 w-4 shrink-0 text-alert-500" />
            <span className="truncate">{incident.address}</span>
          </span>
          <span className="inline-flex items-center gap-2">
            <Clock className="h-4 w-4 text-slate-500" />
            {formatTime(incident.timestamp)}
          </span>
        </div>

        <button
          type="button"
          onClick={onView}
          className="mt-6 inline-flex h-11 items-center gap-2 rounded-full bg-white px-5 text-sm font-black text-black transition hover:bg-alert-500 hover:text-white"
        >
          View Details
          <ArrowUpRight className="h-4 w-4" />
        </button>
      </div>
    </motion.article>
  );
}
