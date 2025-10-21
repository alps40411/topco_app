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
    drafts: {
      base: "/api/drafts",
      save: "/api/drafts",
      get: (empno: string) => `/api/drafts/${empno}`,
      update: (dailyNo: string, planno: string, sopno: string) =>
        `/api/drafts/by-daily-planno-sopno/${dailyNo}/${planno}/${sopno}`,
      delete: (id: string) => `/api/drafts/${id}`,
      ai: "/api/drafts/ai",
    },
    records: {
      base: "/api/records",
      consolidatedToday: "/api/records/consolidated/today",
      upload: "/api/records/upload",
      deleteFile: (yearMonth: string, filename: string) =>
        `/api/records/files/${yearMonth}/${filename}`,
      submit: "/api/records/submit",
    },
    reports: {
      base: "/api/reports",
      get: (reportId: string) => `/api/reports/${reportId}`,
      comments: (reportId: string) => `/api/reports/${reportId}/comments`,
      approvals: (reportId: string) => `/api/reports/${reportId}/approvals`,
      delete: (reportId: string) => `/api/reports/${reportId}`,
    },
    workData: {
      base: "/api/work-data",
      all: "/api/work-data",
    },
    dates: {
      range: "/api/dates/range",
      // nextDailyNo 已棄用 - daily_no 現在由後端 /api/drafts 自動生成
    },
    supervisor: {
      base: "/api/supervisor",
      dailyHomepage: "/api/supervisor/daily-homepage",
      forwardCandidates: "/api/supervisor/forward/candidates",
      aiSuggestions: (reportId: string) =>
        `/api/supervisor/reports/${reportId}/ai-suggestions`,
    },

    // === 保留用於向後兼容 ===
    projects: "/api/projects",
    comments: "/api/reports",
    legacy: {
      reports: "/api/legacy/reports",
      reportContent: "/api/legacy/reports",
      workPlans: "/api/legacy/work-plans",
      companies: "/api/legacy/companies",
      drafts: "/api/drafts", // 已遷移
      attachments: "/api/legacy/attachments",
      submit: "/api/records/submit", // 已遷移到 records.submit
      workItems: "/api/legacy/work-items",
      serviceCompanies: "/api/legacy/service-companies",
      // nextDailyNo 已棄用 - daily_no 現在由後端 /api/drafts 自動生成
      executionWorks: "/api/work-data", // 已遷移到 workData
      serviceTargets: "/api/work-data", // 已遷移到 workData
      workData: "/api/work-data", // 已遷移到 workData
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
    if (import.meta.env.MODE === "development" || currentPort === "3000") {
      return endpoint;
    }

    // 生產環境：使用 HTTPS 協議和主機的 8000 端口作為後端
    return `https://${currentHost}:8000${endpoint}`;
  }

  return endpoint; // 開發環境使用代理
};
