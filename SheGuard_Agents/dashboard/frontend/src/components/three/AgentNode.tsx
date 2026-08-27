"use client";

import * as React from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { AGENT_DEFINITIONS, type AgentId, getAgentStatusColor } from "../../utils/agents";
import type { AgentHealth } from "../../types";

interface AgentNodeProps {
  agentId: AgentId;
  health: AgentHealth | undefined;
  isSelected: boolean;
  isHovered: boolean;
  onSelect: (id: AgentId) => void;
  onHover: (id: AgentId, hover: boolean) => void;
}

const statusPulseSpeeds: Record<string, number> = {
  HEALTHY: 1.0,
  PROCESSING: 2.5,
  DEGRADED: 1.5,
  WARNING: 2.0,
  ERROR: 3.0,
  OFFLINE: 0,
  UNKNOWN: 0,
};

export const AgentNode = React.memo(function AgentNode({
  agentId,
  health,
  isSelected,
  isHovered,
  onSelect,
  onHover,
}: AgentNodeProps) {
  const def = AGENT_DEFINITIONS[agentId];
  const status = health?.status || "OFFLINE";
  const color = getAgentStatusColor(status);
  const pulseSpeed = statusPulseSpeeds[status] || 0;

  const [pulse, setPulse] = React.useState(0);

  useFrame((_state, delta) => {
    if (pulseSpeed > 0) {
      setPulse((p) => p + delta * pulseSpeed);
    }
  });

  const onClick = () => onSelect(agentId);
  const onPointerOver = () => onHover(agentId, true);
  const onPointerOut = () => onHover(agentId, false);

  const baseScale = isSelected ? 1.35 : isHovered ? 1.15 : 1.0;
  const pulseScale = pulseSpeed > 0 ? 1 + 0.12 * Math.sin(pulse * 3) : 1;

  return (
    <group
      position={[def.x, def.y, def.z]}
      onClick={onClick}
      onPointerOver={onPointerOver}
      onPointerOut={onPointerOut}
      scale={baseScale * pulseScale}
    >
      {/* Outer glow ring for status */}
      <mesh
        position={[0, -0.6, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        <ringGeometry args={[0.7, 0.9, 32]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={isSelected ? 0.5 : isHovered ? 0.35 : 0.2}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Main agent sphere */}
      <mesh
        geometry={new THREE.IcosahedronGeometry(0.55, 8)}
        onClick={onClick}
        onPointerOver={onPointerOver}
        onPointerOut={onPointerOut}
      >
        <meshStandardMaterial
          color={color}
          metalness={0.3}
          roughness={0.4}
          transparent
          opacity={status === "OFFLINE" ? 0.45 : 0.95}
          emissive={color}
          emissiveIntensity={isSelected ? 0.6 : isHovered ? 0.35 : 0.15}
        />
      </mesh>

      {/* Inner core for PROCESSING state */}
      {status === "PROCESSING" && (
        <mesh
          geometry={new THREE.SphereGeometry(0.28, 16, 16)}
          position={[0, 0, 0]}
        >
          <meshBasicMaterial
            color={color}
            transparent
            opacity={0.4 + 0.3 * Math.sin(pulse * 8)}
          />
        </mesh>
      )}

      {/* Selection highlight */}
      {isSelected && (
        <mesh
          geometry={new THREE.IcosahedronGeometry(0.62, 8)}
        >
          <meshBasicMaterial
            color={color}
            transparent
            opacity={0.15 + 0.1 * Math.sin(pulse * 4)}
            wireframe
          />
        </mesh>
      )}

      {/* Label background */}
      <mesh
        position={[0, 1.1, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
        scale={[0.8, 0.8, 0.8]}
      >
        <planeGeometry args={[1.6, 0.5]} />
        <meshBasicMaterial
          color="#0a0e17"
          transparent
          opacity={0.85}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
  );
});

AgentNode.displayName = "AgentNode";
