import { confidenceLabel } from '../lib/incidents';

export default function ConfidenceGraph({ value }) {
  const percent = Math.max(0, Math.min(100, Math.round(Number(value) <= 1 ? Number(value) * 100 : Number(value) || 0)));
  const bars = [Math.max(18, percent - 26), Math.max(24, percent - 12), percent, Math.max(28, percent - 8), Math.max(34, percent - 3)];

  return (
    <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">AI Confidence</p>
          <h3 className="mt-2 text-4xl font-black text-white">{confidenceLabel(value)}</h3>
        </div>
        <div className="flex h-28 items-end gap-2">
          {bars.map((bar, index) => (
            <div key={index} className="w-7 rounded-full bg-white/10">
              <div className="rounded-full bg-gradient-to-t from-alert-700 via-alert-500 to-white" style={{ height: `${bar}%` }} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
