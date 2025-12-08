// frontend/src/utils/urlUtils.ts

/**
 * 取得完整的檔案 URL
 * 所有檔案都使用 CommonAPI 格式
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

  // ✅ 所有檔案都使用 CommonAPI 格式
  // CommonAPI 格式: /CommonApi/api/SharedFile?FileId=xxx&Type=upimages&CoCode=A&FileName=xxx.png
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;

  // 檢查是否為開發環境
  const isDevelopment =
    window.location.port === "5173" ||
    window.location.port === "5174" ||
    window.location.port === "3000" ||
    window.location.hostname === "localhost";

  // 開發環境使用 :8000 port，正式環境使用當前域名
  const backendUrl = isDevelopment
    ? `${protocol}//${hostname}:8001`
    : `${protocol}//${hostname}`;

  return url.startsWith("/") ? `${backendUrl}${url}` : `${backendUrl}/${url}`;
};
