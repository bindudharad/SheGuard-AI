import * as React from "react";
import { Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Overview } from "./pages/Overview";
import { LivePipeline } from "./pages/LivePipeline";
import { Events } from "./pages/Events";
import { Incidents, IncidentDetail } from "./pages/Incidents";
import { Responses } from "./pages/Responses";
import { X402Page } from "./pages/X402Page";
import { Health } from "./pages/Health";
import { Performance } from "./pages/Performance";
import { Logs } from "./pages/Logs";
import { Tests } from "./pages/Tests";
import { Settings } from "./pages/Settings";
import { AgentDetail } from "./pages/AgentDetail";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Overview />} />
        <Route path="/pipeline" element={<LivePipeline />} />
        <Route path="/agents" element={<Overview />} />
        <Route path="/agents/:agentId" element={<AgentDetail />} />
        <Route path="/events" element={<Events />} />
        <Route path="/incidents" element={<Incidents />} />
        <Route path="/incidents/:incidentId" element={<IncidentDetail />} />
        <Route path="/responses" element={<Responses />} />
        <Route path="/x402" element={<X402Page />} />
        <Route path="/performance" element={<Performance />} />
        <Route path="/health" element={<Health />} />
        <Route path="/logs" element={<Logs />} />
        <Route path="/tests" element={<Tests />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
