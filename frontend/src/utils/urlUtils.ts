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

  // 在開發環境中，後端服務在 8000 port；在正式環境中，API 和前端在同一個 domain 下，不需指定 port
  const backendUrl = isDevelopment
    ? `${protocol}//${hostname}:8000`
    : `${protocol}//${hostname}`;

  // 處理相對路徑
  const fullUrl = url.startsWith("/")
    ? `${backendUrl}${url}`
    : `${backendUrl}/${url}`;

  return fullUrl;
};
