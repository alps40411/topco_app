// frontend/vite.config.production.ts
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// 生產環境配置
export default defineConfig(({ mode }) => {
  // 加載環境變數
  const env = loadEnv(mode, process.cwd(), "");

  return {
    plugins: [
      react(),
      {
        name: 'html-transform',
        transformIndexHtml(html) {
          // 為 index.html 添加 meta 標籤防止快取
          return html.replace(
            '</head>',
            `  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="0">
</head>`
          );
        },
      },
    ],

    optimizeDeps: {
      include: ["lucide-react"],
    },
    build: {
      outDir: "dist",
      sourcemap: false,
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ["react", "react-dom"],
            router: ["react-router-dom"],
            ui: ["lucide-react", "react-hot-toast", "react-datepicker"],
          },
        },
      },
    },
    server: {
      host: "0.0.0.0", // 允許外部訪問
      port: 3000, // 生產環境使用 3000 端口
      strictPort: true,
    },
    preview: {
      host: "0.0.0.0",
      port: 3000,
      strictPort: true,
    },
  };
});
