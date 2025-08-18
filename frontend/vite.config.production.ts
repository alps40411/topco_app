// frontend/vite.config.production.ts
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// 生產環境配置
export default defineConfig(({ mode }) => {
  // 加載環境變數
  const env = loadEnv(mode, process.cwd(), '');
  
  console.log('🔧 生產環境配置:');
  console.log('   VITE_API_BASE_URL:', env.VITE_API_BASE_URL);
  
  return {
    plugins: [react()],
    optimizeDeps: {
      exclude: ["lucide-react"],
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['react', 'react-dom'],
            router: ['react-router-dom'],
            ui: ['lucide-react', 'react-hot-toast', 'react-datepicker']
          }
        }
      }
    },
    server: {
      host: '0.0.0.0', // 允許外部訪問
      port: 3000, // 生產環境使用 3000 端口
      strictPort: true
    },
    preview: {
      host: '0.0.0.0',
      port: 3000,
      strictPort: true
    }
  };
});