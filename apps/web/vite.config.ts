import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "node",
    globals: true,
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
  server: {
    host: "0.0.0.0",
    port: 3000,
    proxy: {
      "/api": {
        target: process.env.VITE_API_URL || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Split heavy libraries out of the main bundle so the initial load
        // stays fast.  Each group is loaded lazily when the first page that
        // needs it is rendered.
        manualChunks(id) {
          // Recharts + D3 dependencies  (~300 KB gz uncompressed)
          if (id.includes("node_modules/recharts") || id.includes("node_modules/d3-")) {
            return "vendor-charts";
          }
          // Framer Motion  (~50 KB gz)
          if (id.includes("node_modules/framer-motion")) {
            return "vendor-motion";
          }
          // TanStack Virtual  (~6 KB gz) — keep with other tanstack libs
          if (
            id.includes("node_modules/@tanstack/react-virtual") ||
            id.includes("node_modules/@tanstack/virtual-core")
          ) {
            return "vendor-virtual";
          }
          // DnD Kit (Kanban board)
          if (id.includes("node_modules/@dnd-kit")) {
            return "vendor-dnd";
          }
          // Radix UI primitives  (many small packages — group them)
          if (id.includes("node_modules/@radix-ui")) {
            return "vendor-radix";
          }
          // React core — Vite already handles this, but be explicit
          if (id.includes("node_modules/react") || id.includes("node_modules/react-dom")) {
            return "vendor-react";
          }
        },
      },
    },
    // Warn when any chunk exceeds 500 KB (uncompressed)
    chunkSizeWarningLimit: 500,
  },
});
