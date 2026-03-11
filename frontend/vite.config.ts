// frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  base: "/MyReportAI/",
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

  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // CKEditor 最大，獨立拆出（~500KB+）
          ckeditor: ['ckeditor5', '@ckeditor/ckeditor5-react'],
          // React 核心
          react: ['react', 'react-dom', 'react-router-dom'],
          // 其他工具庫
          utils: ['date-fns', 'lucide-react'],
        },
      },
    },
  },
  optimizeDeps: {
    include: ["lucide-react"],
  },
  server: {
    host: "0.0.0.0",
    port: 5000,
    allowedHosts: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
      },
      "/storage": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
      },
    },
  },
});
