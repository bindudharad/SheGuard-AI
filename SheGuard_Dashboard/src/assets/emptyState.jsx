export default function EmptyStateArt() {
  return (
    <svg viewBox="0 0 520 300" role="img" aria-label="No active incidents" className="mx-auto h-52 w-full max-w-lg">
      <defs>
        <linearGradient id="empty-red" x1="0" x2="1">
          <stop offset="0%" stopColor="#ff3148" stopOpacity="0.95" />
          <stop offset="100%" stopColor="#9f1239" stopOpacity="0.55" />
        </linearGradient>
        <linearGradient id="empty-glass" x1="0" x2="1">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#ffffff" stopOpacity="0.05" />
        </linearGradient>
      </defs>
      <rect x="68" y="48" width="384" height="204" rx="28" fill="url(#empty-glass)" stroke="rgba(255,255,255,.16)" />
      <circle cx="260" cy="150" r="62" fill="rgba(255,49,72,.08)" stroke="rgba(255,49,72,.28)" />
      <circle cx="260" cy="150" r="34" fill="url(#empty-red)" opacity=".88" />
      <path d="M260 112v44l28 18" fill="none" stroke="#fff" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M118 104h76M326 104h76M118 198h118M306 198h96" stroke="rgba(255,255,255,.24)" strokeWidth="10" strokeLinecap="round" />
      <path d="M92 78l-34-20M428 78l34-20M92 222l-34 20M428 222l34 20" stroke="rgba(255,49,72,.45)" strokeWidth="8" strokeLinecap="round" />
    </svg>
  );
}
