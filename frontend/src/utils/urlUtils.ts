// frontend/src/utils/urlUtils.ts

/**
 * 取得完整的檔案 URL
 * 自動處理開發環境和生產環境的 URL
 */
export const getFullFileUrl = (url: string): string => {
  if (!url) {
    console.error("❌ getFullFileUrl - 空的URL");
    return "";
  }

  // 如果 URL 已經是完整的，直接返回
  if (url.startsWith("http")) {
    return url;
  }

  // 檢查是否為開發環境
  const isDevelopment =
    window.location.port === "5173" ||
    window.location.port === "5174" ||
    window.location.port === "3000" ||
    window.location.hostname === "localhost";

  // 建立後端 URL
  const protocol = window.location.protocol; // http: 或 https:
  const hostname = window.location.hostname;
  const backendPort = isDevelopment ? "8000" : "8000"; // 可根據需求調整

  const backendUrl = `${protocol}//${hostname}:${backendPort}`;

  // 處理相對路徑
  const fullUrl = url.startsWith("/")
    ? `${backendUrl}${url}`
    : `${backendUrl}/${url}`;

  return fullUrl;
};
