import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react({jsxImportSource:"@scamshield/i18n"})],
  resolve:{alias:{"@scamshield/i18n":new URL("./src/i18n",import.meta.url).pathname}},
  server: {
    host: "0.0.0.0",
    allowedHosts: true,
    proxy: { "/api": process.env.VITE_PROXY_TARGET || "http://127.0.0.1:8000" },
  },
  test: {
    include: ["src/**/*.test.{js,jsx,ts,tsx}"],
    environment: "jsdom",
    setupFiles: "./src/test-setup.js",
  },
});
