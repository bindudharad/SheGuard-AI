"use client";

import * as React from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import { AgentNode } from "./AgentNode";
import { Connections } from "./Connections";
import { PIPELINE_ORDER, AGENT_DEFINITIONS, type AgentId } from "../../utils/agents";
import type { AgentHealth, AgentEvent } from "../../types";

interface AgentNetworkSceneProps {
  agentsHealth: Record<string, AgentHealth>;
  selectedAgent: AgentId | null;
  onSelectAgent: (id: AgentId | null) => void;
  recentEvents?: AgentEvent[];
}

const CAMERA_DISTANCE = 12;

function SceneContent({ agentsHealth, selectedAgent, onSelectAgent, hoveredAgent, setHoveredAgent, eventFlows, shakeKey }: any) {
  return (
    <>
      <fog attach="fog" args={["#0a0f1a", 5, 25]} />
      <color attach="background" args={["#0a0f1a"]} />

      <OrbitControls
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        minDistance={5}
        maxDistance={30}
        target={[0, 0.5, 0]}
      />

      <ambientLight intensity={0.6} />
      <directionalLight position={[5, 10, 5]} intensity={1.2} />
      <directionalLight position={[-5, 5, -5]} intensity={0.5} />

      <Connections agentsHealth={agentsHealth} eventFlow={eventFlows} />

      {PIPELINE_ORDER.map((agentId) => (
        <AgentNode
          key={agentId}
          agentId={agentId}
          health={agentsHealth[agentId]}
          isSelected={selectedAgent === agentId}
          isHovered={hoveredAgent === agentId}
          onSelect={onSelectAgent}
          onHover={setHoveredAgent}
        />
      ))}

      <Html
        position={[0, -3.5, 0]}
        fullscreen
        style={{ pointerEvents: "none", zIndex: 10 }}
      >
        <div className="text-center pointer-events-none">
          <p className="text-xs text-slate-500 font-mono tracking-wider uppercase">SheGuard AI+</p>
          <p className="text-[10px] text-slate-700 mt-1">Agent Operations Center</p>
        </div>
      </Html>
    </>
  );
}

export const AgentNetworkScene = React.memo(function AgentNetworkScene({
  agentsHealth,
  selectedAgent,
  onSelectAgent,
  recentEvents = [],
}: AgentNetworkSceneProps) {
  const [hoveredAgent, setHoveredAgent] = React.useState<AgentId | null>(null);
  const [cameraPos, setCameraPos] = React.useState<[number, number, number]>([0, 0, CAMERA_DISTANCE]);
  const [shakeKey, setShakeKey] = React.useState(0);

  const eventFlows = React.useMemo(() => {
    const flows: Array<{ from: AgentId; to: AgentId; timestamp: number; eventType: string }> = [];
    recentEvents.forEach((e) => {
      const agent = (e.agent_id || e.agent) as AgentId;
      if (!agent) return;
      const def = AGENT_DEFINITIONS[agent];
      if (!def) return;
      def.communicatesWith.forEach((target: AgentId) => {
        flows.push({
          from: agent,
          to: target,
          timestamp: Date.parse(e.timestamp) || Date.now(),
          eventType: e.event_type || "EVENT",
        });
      });
    });
    return flows;
  }, [recentEvents]);

  React.useEffect(() => {
    const critical = recentEvents.some(
      (e) => e.severity === "CRITICAL" || e.event_type?.includes("EMERGENCY") || e.event_type?.includes("CRITICAL")
    );
    if (critical) {
      setShakeKey((k) => k + 1);
    }
  }, [recentEvents]);

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <Canvas
        camera={{ position: [0, 0, CAMERA_DISTANCE], fov: 45 }}
        gl={{ antialias: true, alpha: true, preserveDrawingBuffer: false }}
        onCreated={({ gl }) => { gl.setPixelRatio(Math.min(window.devicePixelRatio, 2)); }}
      >
        <SceneContent
          agentsHealth={agentsHealth}
          selectedAgent={selectedAgent}
          onSelectAgent={onSelectAgent}
          hoveredAgent={hoveredAgent}
          setHoveredAgent={setHoveredAgent}
          eventFlows={eventFlows}
          shakeKey={shakeKey}
        />
      </Canvas>

      <div className="absolute bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-64">
        <div className="bg-slate-900/80 backdrop-blur rounded-xl border border-slate-800/50 p-4 space-y-2">
          <p className="font-medium text-slate-100 text-sm">Legend</p>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="w-3 h-3 rounded-full bg-green-400" /> Healthy
            <span className="w-3 h-3 rounded-full bg-amber-400" /> Degraded
            <span className="w-3 h-3 rounded-full bg-red-400" /> Error
            <span className="w-3 h-3 rounded-full bg-slate-500" /> Offline
            <span className="w-3 h-3 rounded-full bg-blue-400 animate-pulse" /> Processing
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400 mt-1">
            <span className="w-3 h-3 rounded-full border-2 border-sky-400" /> Selected
          </div>
          {selectedAgent && (
            <div className="pt-2 border-t border-slate-800/50">
              <p className="text-xs text-slate-300 font-mono">{AGENT_DEFINITIONS[selectedAgent]?.name || selectedAgent}</p>
              <p className="text-[10px] text-slate-500">Click empty space to deselect</p>
            </div>
          )}
        </div>
      </div>

      <div className="absolute bottom-4 right-4 md:bottom-auto md:top-4 md:right-auto md:left-4 md:w-64">
        <div className="bg-slate-900/80 backdrop-blur rounded-xl border border-slate-800/50 p-4 space-y-1.5">
          <p className="font-medium text-slate-100 text-sm">System Status</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="p-2 rounded bg-slate-800/50">
              <p className="text-slate-500">Agents Online</p>
              <p className="font-mono text-green-400">{Object.values(agentsHealth).filter((a) => a?.status === "HEALTHY").length} / 7</p>
            </div>
            <div className="p-2 rounded bg-slate-800/50">
              <p className="text-slate-500">Events (1min)</p>
              <p className="font-mono text-sky-400">{recentEvents.length}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});
