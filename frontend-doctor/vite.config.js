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
      // The main FastAPI backend (auth, queue, encounters, prescribing, public
      // visit pages). Not the ml_backend vision/OCR microservice, which runs
      // separately on :8001 and is only reached indirectly, via the backend.
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
