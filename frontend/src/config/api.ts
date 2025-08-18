// frontend/src/config/api.ts

// 開發環境和生產環境的 API 基礎 URL 配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// 除錯資訊
console.log('🔧 API 配置除錯:');
console.log('   VITE_API_BASE_URL:', import.meta.env.VITE_API_BASE_URL);
console.log('   API_BASE_URL:', API_BASE_URL);
console.log('   MODE:', import.meta.env.MODE);

// 自動偵測模式：
// 開發模式：使用代理
// 生產模式：使用當前頁面的主機地址

export const apiConfig = {
  baseURL: API_BASE_URL,
  endpoints: {
    auth: {
      token: '/api/auth/token',
      me: '/api/auth/me'
    },
    records: {
      base: '/api/records',
      upload: '/api/records/upload',
      writingStatus: '/api/records/writing-status',
      today: '/api/records/today',
      consolidated: '/api/records/consolidated/today'
    },
    projects: '/api/projects',
    supervisor: '/api/supervisor',
    comments: '/api/reports'
  }
};

// 輔助函數：構建完整的 API URL
export const buildApiUrl = (endpoint: string): string => {
  if (API_BASE_URL) {
    return `${API_BASE_URL}${endpoint}`;
  }
  
  // 如果沒有設定 API_BASE_URL，自動使用當前主機:8000
  if (typeof window !== 'undefined' && import.meta.env.MODE === 'production') {
    const currentHost = window.location.hostname;
    return `http://${currentHost}:8000${endpoint}`;
  }
  
  return endpoint; // 開發環境使用代理
};