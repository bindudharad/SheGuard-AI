import { useEffect, useMemo, useState } from "react";
import { Search, Filter, Calendar, ChevronDown, ChevronUp, FileText } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useIncidents } from "../hooks/useIncidents";
import { formatTime, confidenceLabel } from "../lib/incidents";
import StatusBadge from "../components/StatusBadge";
import IncidentArticleCard from "../components/IncidentArticleCard";

export default function ArchivePage() {
  const { incidents, isLoading, error, refresh } = useIncidents();
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [threatFilter, setThreatFilter] = useState("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sortBy, setSortBy] = useState("newest");
  const [showFilters, setShowFilters] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const filteredIncidents = useMemo(() => {
    let result = [...incidents];

    // Search
    if (query.trim()) {
      const search = query.trim().toLowerCase();
      result = result.filter((incident) =>
        [incident.title, incident.description, incident.address, incident.id, incident.sessionId, incident.userId]
          .some((val) => String(val || "").toLowerCase().includes(search))
      );
    }

    // Status filter
    if (statusFilter !== "all") {
      if (statusFilter === "active") result = result.filter((i) => !i.isResolved);
      else if (statusFilter === "resolved") result = result.filter((i) => i.isResolved);
      else if (statusFilter === "high") result = result.filter((i) => i.severity === "critical");
    }

    // Threat filter
    if (threatFilter !== "all") {
      result = result.filter((i) => i.severity === threatFilter);
    }

    // Date range
    if (dateFrom) {
      const from = new Date(dateFrom).getTime();
      result = result.filter((i) => new Date(i.timestamp).getTime() >= from);
    }
    if (dateTo) {
      const to = new Date(dateTo).getTime() + 86400000; // End of day
      result = result.filter((i) => new Date(i.timestamp).getTime() <= to);
    }

    // Sort
    result.sort((a, b) => {
      const aTime = new Date(a.timestamp).getTime();
      const bTime = new Date(b.timestamp).getTime();
      if (sortBy === "newest") return bTime - aTime;
      if (sortBy === "oldest") return aTime - bTime;
      if (sortBy === "threat") return (b.threat_score || 0) - (a.threat_score || 0);
      if (sortBy === "confidence") return (b.confidence || 0) - (a.confidence || 0);
      return 0;
    });

    return result;
  }, [incidents, query, statusFilter, threatFilter, dateFrom, dateTo, sortBy]);

  const paginatedIncidents = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredIncidents.slice(start, start + pageSize);
  }, [filteredIncidents, page]);

  const totalPages = Math.ceil(filteredIncidents.length / pageSize);

  return (
    <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8">
      <section className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/12 px-4 py-2 text-xs font-black uppercase tracking-[0.16em] text-amber-100">
            <FileText className="h-4 w-4" />
            Incident Archive
          </div>
          <h1 className="mt-4 text-4xl font-black tracking-tight text-white sm:text-5xl">
            Historical Incident Records
          </h1>
          <p className="mt-2 text-lg text-slate-300">
            {filteredIncidents.length} incident{filteredIncidents.length !== 1 ? "s" : ""} found
            {incidents.length > filteredIncidents.length && (
              <span className="text-slate-500 ml-2">({incidents.length} total)</span>
            )}
          </p>
        </div>

        {/* Search & Filters */}
        <div className="mb-6">
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="space-y-4">
            {/* Main search */}
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="text"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setPage(1);
                }}
                placeholder="Search incident ID, user, location, type, camera..."
                className="w-full h-12 pl-12 pr-4 rounded-xl border border-white/10 bg-white/[0.055] text-white placeholder:text-slate-500 outline-none focus:border-alert-500/50 transition"
              />
            </div>

            {/* Advanced filters toggle */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.055] px-4 py-2 text-sm font-medium text-slate-300 hover:border-white/20 hover:text-white transition"
            >
              <Filter className="h-4 w-4" />
              Advanced Filters
              {showFilters ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>

            {/* Advanced filters */}
            <AnimatePresence>
              {showFilters && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="grid gap-4 md:grid-cols-2 lg:grid-cols-5"
                >
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Status</label>
                    <select
                      value={statusFilter}
                      onChange={(e) => {
                        setStatusFilter(e.target.value);
                        setPage(1);
                      }}
                      className="w-full h-10 rounded-xl border border-white/10 bg-white/[0.055] text-white outline-none focus:border-alert-500/50"
                    >
                      <option value="all">All Status</option>
                      <option value="active">Active</option>
                      <option value="resolved">Resolved</option>
                      <option value="high">High Risk</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Threat Level</label>
                    <select
                      value={threatFilter}
                      onChange={(e) => {
                        setThreatFilter(e.target.value);
                        setPage(1);
                      }}
                      className="w-full h-10 rounded-xl border border-white/10 bg-white/[0.055] text-white outline-none focus:border-alert-500/50"
                    >
                      <option value="all">All Levels</option>
                      <option value="critical">Critical</option>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Date From</label>
                    <input
                      type="date"
                      value={dateFrom}
                      onChange={(e) => {
                        setDateFrom(e.target.value);
                        setPage(1);
                      }}
                      className="w-full h-10 rounded-xl border border-white/10 bg-white/[0.055] text-white outline-none focus:border-alert-500/50"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Date To</label>
                    <input
                      type="date"
                      value={dateTo}
                      onChange={(e) => {
                        setDateTo(e.target.value);
                        setPage(1);
                      }}
                      className="w-full h-10 rounded-xl border border-white/10 bg-white/[0.055] text-white outline-none focus:border-alert-500/50"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Sort By</label>
                    <select
                      value={sortBy}
                      onChange={(e) => {
                        setSortBy(e.target.value);
                        setPage(1);
                      }}
                      className="w-full h-10 rounded-xl border border-white/10 bg-white/[0.055] text-white outline-none focus:border-alert-500/50"
                    >
                      <option value="newest">Newest First</option>
                      <option value="oldest">Oldest First</option>
                      <option value="threat">Highest Threat</option>
                      <option value="confidence">Highest Confidence</option>
                    </select>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 rounded-xl border border-alert-500/30 bg-alert-500/12 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        )}

        {/* Incident List */}
        <div className="space-y-4">
          {isLoading ? (
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="h-[440px] animate-pulse rounded-[1.7rem] border border-white/10 bg-white/[0.055]" />
              ))}
            </div>
          ) : paginatedIncidents.length > 0 ? (
            <>
              {paginatedIncidents.map((incident, index) => (
                <IncidentArticleCard
                  key={incident.id}
                  incident={incident}
                  featured={false}
                  onView={() => (window.location.href = `/incident/${incident.id}`)}
                />
              ))}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-8 flex items-center justify-center gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.055] text-slate-300 disabled:opacity-50 disabled:cursor-not-allowed hover:text-white transition"
                  >
                    <ChevronDown className="h-5 w-5 rotate-180" />
                  </button>
                  <span className="text-sm font-medium text-white px-4">Page {page} of {totalPages}</span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.055] text-slate-300 disabled:opacity-50 disabled:cursor-not-allowed hover:text-white transition"
                  >
                    <ChevronDown className="h-5 w-5" />
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-20">
              <FileText className="h-16 w-16 mx-auto text-slate-600" />
              <h2 className="mt-6 text-xl font-bold text-white">No incidents found</h2>
              <p className="mt-2 text-slate-400">Try adjusting your filters or search terms</p>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
