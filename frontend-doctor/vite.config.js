import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@shared": path.resolve(__dirname, "../shared") },
  },
  server: {
    port: 5174,
    proxy: {
      // Point at Kartik's FastAPI once it is up; until then VITE_USE_MOCKS=1.
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
