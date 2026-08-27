const statusStyles = {
  active: 'border-alert-500/35 bg-alert-500/16 text-red-100',
  live: 'border-emerald-400/35 bg-emerald-400/14 text-emerald-100',
  resolved: 'border-slate-300/25 bg-white/10 text-slate-100',
  'high risk': 'border-amber-300/35 bg-amber-300/14 text-amber-100',
};

export default function StatusBadge({ children, tone = 'active', pulse = false }) {
  const key = String(tone || children || 'active').toLowerCase();
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.12em] ${statusStyles[key] || statusStyles.active}`}>
      {pulse && <span className="h-1.5 w-1.5 rounded-full bg-current animate-sos-pulse" />}
      {children}
    </span>
  );
}
