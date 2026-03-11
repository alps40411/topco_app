// frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  base: "/MyReportAI_Weekly/",
  plugins: [
    react(),
    {
      name: "html-transform",
      transformIndexHtml(html) {
        // 為 index.html 添加 meta 標籤防止快取
        return html.replace(
          "</head>",
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
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks: {
          ckeditor: ['ckeditor5', '@ckeditor/ckeditor5-react'],
          react: ['react', 'react-dom', 'react-router-dom'],
          utils: ['date-fns', 'lucide-react'],
        },
      },
    },
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
