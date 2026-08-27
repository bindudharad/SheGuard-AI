/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DASHBOARD_MODE: "live" | "demo";
  readonly VITE_API_BASE: string;
  readonly VITE_WS_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
