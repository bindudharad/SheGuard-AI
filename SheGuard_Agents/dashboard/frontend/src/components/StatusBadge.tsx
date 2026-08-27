import type { AgentStatus } from "../types";

interface StatusBadgeProps {
  status: AgentStatus | string;
  size?: "sm" | "md" | "lg" | "xl";
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  HEALTHY: { label: "HEALTHY", color: "bg-green-500", icon: "●" },
  DEGRADED: { label: "DEGRADED", color: "bg-amber-500", icon: "◐" },
  WARNING: { label: "WARNING", color: "bg-orange-500", icon: "▲" },
  ERROR: { label: "ERROR", color: "bg-red-500", icon: "✕" },
  OFFLINE: { label: "OFFLINE", color: "bg-slate-500", icon: "○" },
  PROCESSING: { label: "PROCESSING", color: "bg-sky-500", icon: "◉" },
  READY: { label: "READY", color: "bg-green-500", icon: "✓" },
  RUNNING: { label: "RUNNING", color: "bg-sky-500", icon: "▶" },
  INITIALIZING: { label: "INITIALIZING", color: "bg-amber-500", icon: "◐" },
  STOPPED: { label: "STOPPED", color: "bg-slate-500", icon: "■" },
  UNKNOWN: { label: "UNKNOWN", color: "bg-slate-500", icon: "?" },
  CRITICAL: { label: "CRITICAL", color: "bg-red-500", icon: "⚠" },
  SAFE: { label: "SAFE", color: "bg-green-500", icon: "✓" },
  HIGH: { label: "HIGH", color: "bg-orange-500", icon: "▲" },
};

const SIZE_CLASSES = {
  sm: "text-xs px-2 py-0.5 gap-1",
  md: "text-sm px-2.5 py-1 gap-1.5",
  lg: "text-base px-3 py-1.5 gap-2",
  xl: "text-lg px-4 py-2 gap-2.5",
};

export function StatusBadge({ status, size = "md" }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.UNKNOWN;
  const sizeClass = SIZE_CLASSES[size];

  return (
    <span
      className={`inline-flex items-center ${sizeClass} rounded-full border border-transparent font-medium`}
      style={{ backgroundColor: `${config.color}20`, color: config.color }}
    >
      <span aria-hidden="true">{config.icon}</span>
      <span>{config.label}</span>
    </span>
  );
}
