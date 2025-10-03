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
    auth: {
      token: "/api/auth/token",
      me: "/api/auth/me",
    },
    records: {
      base: "/api/records",
      upload: "/api/records/upload",
      writingStatus: "/api/records/writing-status",
      today: "/api/records/today",
      consolidated: "/api/records/consolidated/today",
    },
    projects: "/api/projects",
    supervisor: "/api/supervisor",
    comments: "/api/reports",
    legacy: {
      reports: "/api/legacy/reports",
      reportContent: "/api/legacy/reports",
      workPlans: "/api/legacy/work-plans",
      companies: "/api/legacy/companies",
      nextDailyNo: "/api/legacy/next-daily-no",
      drafts: "/api/drafts",
      attachments: "/api/legacy/attachments",
      submit: "/api/legacy/submit",
      executionWorks: "/api/legacy/execution-works",
      workItems: "/api/legacy/work-items",
      serviceCompanies: "/api/legacy/service-companies",
      serviceTargets: "/api/legacy/service-targets",
      workData: "/api/legacy/work-data",
    },
  },
};

// 輔助函數：構建完整的 API URL
export const buildApiUrl = (endpoint: string): string => {
  if (API_BASE_URL) {
    return `${API_BASE_URL}${endpoint}`;
  }

  // 如果沒有設定 API_BASE_URL，使用當前頁面的主機和端口
  if (typeof window !== "undefined") {
    const currentHost = window.location.hostname;
    const currentPort = window.location.port;

    // 如果是開發環境或使用代理，直接返回 endpoint
    if (import.meta.env.MODE === "development" || currentPort === "3000") {
      return endpoint;
    }

    // 生產環境：使用當前主機的 8000 端口作為後端
    return `http://${currentHost}:8000${endpoint}`;
  }

  return endpoint; // 開發環境使用代理
};
