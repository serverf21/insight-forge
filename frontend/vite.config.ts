import dns from "node:dns";
import { defineConfig } from "vite";

dns.setDefaultResultOrder("ipv4first");

export default defineConfig({
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
