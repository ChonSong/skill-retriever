import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";
import { resolve } from "path";

export default defineConfig({
  plugins: [TanStackRouterVite({ autoCodeSplitting: true }), react(), tailwindcss()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "./src"),
    },
  },
  base: "/agent-nestjs-skills/",
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          "react-vendor": ["react", "react-dom"],
          "router": ["@tanstack/react-router"],
          "ui": ["lucide-react", "class-variance-authority", "clsx", "tailwind-merge"],
        },
      },
    },
  },
});
