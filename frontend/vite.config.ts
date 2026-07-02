import { execSync } from "node:child_process";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

function resolveBackendTarget(): string {
  const explicitTarget = process.env.VITE_BACKEND_PROXY_TARGET?.trim();
  if (explicitTarget) {
    return explicitTarget;
  }

  try {
    const rawIp = execSync(
      'wsl.exe -d Ubuntu-24.04 -- bash -lc "hostname -I"',
      { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] },
    );
    const ip = rawIp.trim().split(/\s+/)[0];
    if (ip) {
      return `http://${ip}:8000`;
    }
  } catch {
    // Fall back to localhost if WSL lookup is unavailable.
  }

  return "http://127.0.0.1:8000";
}

const backendTarget = resolveBackendTarget();

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/health": {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
});
