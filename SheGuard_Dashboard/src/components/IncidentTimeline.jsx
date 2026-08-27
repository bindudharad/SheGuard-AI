import { CheckCircle2, CircleDot, Radio, Siren } from 'lucide-react';
import { formatTime } from '../lib/incidents';

export default function IncidentTimeline({ incident }) {
  const events = [
    { label: 'Signal received', body: 'Emergency signal ingested by SheGuard monitoring.', icon: Radio, time: incident.timestamp },
    { label: 'AI detection', body: incident.description, icon: CircleDot, time: incident.timestamp },
    { label: incident.isResolved ? 'Case resolved' : 'Dispatch active', body: incident.isResolved ? 'Incident marked as resolved.' : 'Incident remains open for response team review.', icon: incident.isResolved ? CheckCircle2 : Siren, time: incident.updated_at || incident.timestamp },
  ];

  return (
    <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.055] p-5 backdrop-blur-xl">
      <h3 className="text-xl font-black tracking-tight text-white">Incident Timeline</h3>
      <div className="mt-5 space-y-0">
        {events.map((event, index) => {
          const Icon = event.icon;
          return (
            <div key={event.label} className="relative flex gap-4 pb-6 last:pb-0">
              {index !== events.length - 1 && <div className="absolute left-5 top-11 h-[calc(100%-2rem)] w-px bg-white/10" />}
              <div className="z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-alert-500/30 bg-alert-500/12 text-alert-500">
                <Icon className="h-5 w-5" />
              </div>
              <div>
                <p className="font-bold text-white">{event.label}</p>
                <p className="mt-1 text-xs uppercase tracking-[0.14em] text-slate-500">{formatTime(event.time)}</p>
                <p className="mt-2 text-sm leading-6 text-slate-300">{event.body}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
