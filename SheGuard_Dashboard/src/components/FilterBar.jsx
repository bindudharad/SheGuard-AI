import { Filter, Search } from 'lucide-react';
import { motion } from 'framer-motion';

export default function FilterBar({ query, setQuery, statusFilter, setStatusFilter, confidenceFilter, setConfidenceFilter, timeFilter, setTimeFilter }) {
  return (
    <motion.form
      id="incident-filters"
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-8 grid gap-3 rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-3 backdrop-blur-2xl md:grid-cols-[minmax(0,1fr)_180px_180px_170px]"
    >
      <label className="flex h-12 items-center gap-3 rounded-full border border-white/10 bg-black/28 px-4 text-slate-400">
        <Search className="h-4 w-4" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search location, status, confidence..."
          className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
        />
      </label>
      <Select icon={Filter} value={statusFilter} onChange={setStatusFilter}>
        <option value="all">All status</option>
        <option value="active">Active</option>
        <option value="resolved">Resolved</option>
        <option value="live">Live</option>
        <option value="high">High risk</option>
      </Select>
      <Select value={confidenceFilter} onChange={setConfidenceFilter}>
        <option value="all">All confidence</option>
        <option value="70">70%+</option>
        <option value="85">85%+</option>
        <option value="95">95%+</option>
      </Select>
      <Select value={timeFilter} onChange={setTimeFilter}>
        <option value="all">Any time</option>
        <option value="1">Last hour</option>
        <option value="24">Last 24h</option>
        <option value="168">This week</option>
      </Select>
    </motion.form>
  );
}

function Select({ value, onChange, children, icon: Icon }) {
  return (
    <label className="relative flex h-12 items-center rounded-full border border-white/10 bg-black/28 px-4 text-slate-400">
      {Icon && <Icon className="mr-2 h-4 w-4" />}
      <select value={value} onChange={(event) => onChange(event.target.value)} className="w-full bg-transparent text-sm font-semibold text-white outline-none">
        {children}
      </select>
    </label>
  );
}
