"use client";

import * as React from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { AGENT_DEFINITIONS, PIPELINE_ORDER, type AgentId } from "../../utils/agents";
import type { AgentHealth } from "../../types";

interface ConnectionsProps {
  agentsHealth: Record<string, AgentHealth>;
  activeTraceId?: string | null;
  eventFlow?: Array<{ from: AgentId; to: AgentId; timestamp: number; eventType: string }>;
}

const PIPELINE_EDGES: Array<[AgentId, AgentId]> = [
  ["vision_agent", "context_agent"],
  ["vision_agent", "threat_agent"],
  ["audio_agent", "threat_agent"],
  ["context_agent", "threat_agent"],
  ["threat_agent", "decision_agent"],
  ["decision_agent", "x402_agent"],
  ["decision_agent", "response_agent"],
  ["x402_agent", "threat_agent"],
];

export const Connections = React.memo(function Connections({
  agentsHealth,
  activeTraceId,
  eventFlow = [],
}: ConnectionsProps) {
  const [pulse, setPulse] = React.useState(0);
  const [activeFlows, setActiveFlows] = React.useState<
    Array<{ from: AgentId; to: AgentId; progress: number; eventType: string }>
  >([]);

  useFrame((_state, delta) => {
    setPulse((p) => (p + delta * 0.5) % (Math.PI * 2));
  });

  React.useEffect(() => {
    const now = Date.now();
    setActiveFlows((prev) => {
      const next = prev.map((f) => ({
        ...f,
        progress: Math.min(1, f.progress + 0.015),
      })).filter((f) => f.progress < 1);

      eventFlow.forEach((ef) => {
        if (now - ef.timestamp < 100) {
          const exists = next.some((f) => f.from === ef.from && f.to === ef.to && f.progress < 0.05);
          if (!exists) {
            next.push({ from: ef.from, to: ef.to, progress: 0, eventType: ef.eventType });
          }
        }
      });
      return next;
    });
  }, [eventFlow]);

  return (
    <group>
      {/* Static pipeline connections */}
      {PIPELINE_EDGES.map(([fromId, toId], idx) => {
        const from = AGENT_DEFINITIONS[fromId];
        const to = AGENT_DEFINITIONS[toId];
        const fromHealth = agentsHealth[fromId];
        const toHealth = agentsHealth[toId];
        const fromStatus = fromHealth?.status || "OFFLINE";
        const toStatus = toHealth?.status || "OFFLINE";
        const isActive = fromStatus === "PROCESSING" || toStatus === "PROCESSING";

        const color = isActive ? "#38bdf8" : "#334155";
        const opacity = isActive ? 0.5 + 0.3 * Math.sin(pulse * 2) : 0.25;

        const start = new THREE.Vector3(from.x, from.y, from.z);
        const end = new THREE.Vector3(to.x, to.y, to.z);
        const mid = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
        mid.y += 0.3;

        const points = [start, mid, end];

        return (
          <primitive
            key={idx}
            object={new THREE.Line(
              new THREE.BufferGeometry().setFromPoints(points),
              new THREE.LineDashedMaterial({
                color: new THREE.Color(color),
                transparent: true,
                opacity,
                dashSize: 0.3,
                gapSize: 0.3,
              })
            )}
            onUpdate={(line: THREE.Line) => {
              const mat = line.material as THREE.Material & { dashOffset?: number };
              if (mat && typeof mat.dashOffset !== "undefined") {
                mat.dashOffset = isActive ? pulse * 5 : 0;
              }
              line.geometry.setFromPoints(points);
            }}
          />
        );
      })}

      {/* Animated event flow particles */}
      {activeFlows.map((flow, idx) => {
        const from = AGENT_DEFINITIONS[flow.from];
        const to = AGENT_DEFINITIONS[flow.to];
        const start = new THREE.Vector3(from.x, from.y, from.z);
        const end = new THREE.Vector3(to.x, to.y, to.z);
        const mid = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
        mid.y += 0.4;

        const t = flow.progress;
        const pos = new THREE.Vector3();
        pos.x = (1 - t) * (1 - t) * start.x + 2 * (1 - t) * t * mid.x + t * t * end.x;
        pos.y = (1 - t) * (1 - t) * start.y + 2 * (1 - t) * t * mid.y + t * t * end.y;
        pos.z = (1 - t) * (1 - t) * start.z + 2 * (1 - t) * t * mid.z + t * t * end.z;

        return (
          <mesh
            key={idx}
            position={pos}
            geometry={new THREE.SphereGeometry(0.08, 8, 8)}
          >
            <meshBasicMaterial color="#38bdf8" transparent opacity={1 - flow.progress * 0.5} />
          </mesh>
        );
      })}
    </group>
  );
});

Connections.displayName = "Connections";
