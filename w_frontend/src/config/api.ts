// frontend/src/config/api.ts

// 開發環境和生產環境的 API 基礎 URL 配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

// 除錯資訊

// 自動偵測模式：
// 開發模式：使用代理
// 生產模式：使用當前頁面的主機地址

export const apiConfig = {
  baseURL: API_BASE_URL,
  endpoints: {
    // === 新的組織化 API ===
    auth: {
      token: "/api/auth/token",
      me: "/api/auth/me",
    },
    users: {
      profile: "/api/users/profile",
    },
    weekly: {
      jobItems: "/api/weekly/job-items",
      weeklyNo: "/api/weekly/weekly-no",
      drafts: "/api/weekly/drafts",
      upload: "/api/weekly/drafts/upload",
      deleteFile: (weeklyNo: string, seq: number, filename: string) =>
        `/api/weekly/drafts/files/${weeklyNo}/${seq}/${filename}`,
      deleteDraft: (weeklyNo: string, seq: number) =>
        `/api/weekly/drafts/${weeklyNo}/${seq}`,
      reportList: "/api/weekly/report-list", // 週報列表
      reply: "/api/weekly/reply", // 回覆週報
      init: "/api/weekly/init", // 一次取得當前週次 + 草稿
      weekPeriod: "/api/weekly/week-period", // 週次→日期區間（後端有 cache）
      weekList: "/api/weekly/week-list", // 週次列表（給 WeekSelector）
      autoSubmit: "/api/weekly/auto-submit", // 自動繳交設定
    },
  },
};

// 輔助函數：構建完整的 API URL
export const buildApiUrl = (endpoint: string): string => {
  if (API_BASE_URL) {
    const baseUrl = API_BASE_URL.replace(/\/+$/, ""); // 移除末尾所有斜線
    const path = endpoint.replace(/^\/+/, "/"); // 確保開頭只有一個斜線
    return `${baseUrl}${path}`;
  }

  // 如果沒有設定 API_BASE_URL，使用當前頁面的主機和端口
  if (typeof window !== "undefined") {
    const currentHost = window.location.hostname;
    const currentPort = window.location.port;
    const currentProtocol = window.location.protocol; // http: 或 https:

    // 如果是開發環境或使用代理，直接返回 endpoint
    if (
      import.meta.env.MODE === "development" ||
      currentPort === "3000" ||
      currentPort === "5000"
    ) {
      return endpoint;
    }

    // 生產環境：使用 HTTPS 協議和主機的 8000 端口作為後端
    return `https://${currentHost}:8001${endpoint}`;
  }

  return endpoint; // 開發環境使用代理
};
