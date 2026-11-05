import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Phase 0 owns this file. The dev server proxies /api to the FastAPI backend.
// Each worktree runs its own pair of servers: set API_PORT / WEB_PORT (see docs/WORKSTREAMS.md).
const apiPort = process.env.API_PORT ?? "8000";
const webPort = Number(process.env.WEB_PORT ?? 5173);

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: webPort,
    strictPort: true,
    proxy: { "/api": `http://127.0.0.1:${apiPort}` },
  },
});
