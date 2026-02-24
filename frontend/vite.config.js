import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/review": "http://localhost:8000",
      "/comment": "http://localhost:8000",
      "/health": "http://localhost:8000"
    }
  },
  build: {
    outDir: "dist",
    sourcemap: false
  }
});

