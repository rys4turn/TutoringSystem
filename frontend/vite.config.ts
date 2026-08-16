import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [tailwindcss()],
  server: {
    proxy: {
      "/api": {
        // 后端默认 5000；若本机 5000 被 Windows 保留或占用，可用 VITE_PROXY_TARGET 指向实际端口
        target: process.env.VITE_PROXY_TARGET || "http://127.0.0.1:5000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
