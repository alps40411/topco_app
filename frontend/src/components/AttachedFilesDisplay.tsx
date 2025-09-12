// frontend/src/components/AttachedFilesDisplay.tsx

import React, { useState } from "react";
import {
  Image,
  File,
  BrainCircuit,
  FileText,
  FileSpreadsheet,
  FileVideo,
  FileAudio,
  Archive,
  Download,
} from "lucide-react";
import type { FileAttachment } from "../App";

interface AttachedFilesDisplayProps {
  files: FileAttachment[];
}

const getFileIcon = (type: string, filename: string) => {
  const iconSize = "w-8 h-8";

  // 根據檔案類型返回不同顏色和圖標
  if (type?.startsWith("image/")) {
    return <Image className={`${iconSize} text-green-500`} />;
  }

  // 根據檔案副檔名判斷
  const ext = filename.split(".").pop()?.toLowerCase();

  switch (ext) {
    case "pdf":
      return <FileText className={`${iconSize} text-red-500`} />;
    case "doc":
    case "docx":
      return <FileText className={`${iconSize} text-blue-500`} />;
    case "xls":
    case "xlsx":
      return <FileSpreadsheet className={`${iconSize} text-green-600`} />;
    case "ppt":
    case "pptx":
      return <FileText className={`${iconSize} text-orange-500`} />;
    case "txt":
      return <FileText className={`${iconSize} text-gray-600`} />;
    case "zip":
    case "rar":
    case "7z":
      return <Archive className={`${iconSize} text-purple-500`} />;
    case "mp4":
    case "avi":
    case "mov":
      return <FileVideo className={`${iconSize} text-pink-500`} />;
    case "mp3":
    case "wav":
    case "flac":
      return <FileAudio className={`${iconSize} text-yellow-500`} />;
    default:
      return <File className={`${iconSize} text-gray-500`} />;
  }
};

const getFileTypeColor = (filename: string) => {
  const ext = filename.split(".").pop()?.toLowerCase();

  switch (ext) {
    case "pdf":
      return "border-red-200 bg-red-50";
    case "doc":
    case "docx":
      return "border-blue-200 bg-blue-50";
    case "xls":
    case "xlsx":
      return "border-green-200 bg-green-50";
    case "ppt":
    case "pptx":
      return "border-orange-200 bg-orange-50";
    case "zip":
    case "rar":
    case "7z":
      return "border-purple-200 bg-purple-50";
    case "mp4":
    case "avi":
    case "mov":
      return "border-pink-200 bg-pink-50";
    case "mp3":
    case "wav":
    case "flac":
      return "border-yellow-200 bg-yellow-50";
    default:
      return "border-gray-200 bg-gray-50";
  }
};

const AttachedFilesDisplay: React.FC<AttachedFilesDisplayProps> = ({
  files,
}) => {
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);

  if (!files || files.length === 0) return null;

  const getFullUrl = (url: string) => {
    if (!url) {
      console.error("❌ AttachedFilesDisplay - 空的URL");
      return "";
    }

    if (url.startsWith("http")) {
      return url;
    }

    // 檢查是否為開發環境
    const isDevelopment =
      window.location.port === "5173" ||
      window.location.port === "3000" ||
      window.location.hostname === "localhost";

    const backendUrl = isDevelopment
      ? `http://${window.location.hostname}:8000`
      : "";

    const fullUrl = url.startsWith("/")
      ? `${backendUrl}${url}`
      : `${backendUrl}/${url}`;

    return fullUrl;
  };

  return (
    <>
      <div className="mt-3 border-t border-gray-200 pt-3">
        <h4 className="text-sm font-bold text-gray-700 mb-3">
          📎 附件 ({files.length})
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {files.map((file) => (
            <div
              key={file.id || file.url}
              className={`relative group border-2 rounded-lg p-3 transition-all duration-200 hover:shadow-md ${
                file.is_selected_for_ai
                  ? "bg-green-100 border-green-200 text-green-800"
                  : getFileTypeColor(file.name)
              }`}
            >
              {/* 檔案圖標和資訊 */}
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 p-2 rounded-lg bg-white/50">
                  {file.type.startsWith("image/") ? (
                    <img
                      src={getFullUrl(file.url)}
                      alt={file.name}
                      className="w-12 h-12 object-cover rounded-md cursor-pointer hover:opacity-80"
                      onClick={() => setPreviewImageUrl(getFullUrl(file.url))}
                      onError={(e) => {
                        console.error("❌ 圖片載入失敗:", {
                          url: file.url,
                          fullUrl: getFullUrl(file.url),
                          error: e,
                        });
                        // 可以設置一個預設圖片或顯示錯誤狀態
                      }}
                    />
                  ) : (
                    getFileIcon(file.type, file.name)
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <p
                    className="text-sm font-medium text-gray-900 truncate"
                    title={file.name}
                  >
                    {file.name}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {file.size > 0
                      ? `${(file.size / 1024).toFixed(1)} KB`
                      : "檔案"}
                  </p>
                </div>
              </div>

              {/* 操作按鈕 */}
              <div className="flex justify-end space-x-2 mt-3">
                <button
                  onClick={() => {
                    try {
                      const link = document.createElement("a");
                      link.href = getFullUrl(file.url);
                      link.download = file.name;
                      link.style.display = "none";
                      document.body.appendChild(link);
                      link.click();
                      // 使用 setTimeout 確保點擊事件完成後再移除
                      setTimeout(() => {
                        if (link.parentNode) {
                          link.parentNode.removeChild(link);
                        }
                      }, 100);
                    } catch (error) {
                      console.error("下載檔案時發生錯誤:", error);
                    }
                  }}
                  className="p-1.5 rounded-md bg-white/70 hover:bg-white text-gray-600 hover:text-gray-800 transition-colors"
                  title="下載檔案"
                >
                  <Download className="w-4 h-4" />
                </button>
              </div>

              {file.is_selected_for_ai && (
                <BrainCircuit className="absolute top-2 right-2 w-5 h-5 text-green-600 drop-shadow-md" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Image Preview Modal */}
      {previewImageUrl && (
        <div
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-[100] animate-fade-in"
          onClick={() => setPreviewImageUrl(null)}
        >
          <img
            src={previewImageUrl}
            alt="Preview"
            className="max-w-[90vw] max-h-[90vh] rounded-lg shadow-xl"
            onClick={(e) => e.stopPropagation()} // Prevent closing modal when clicking on image
          />
        </div>
      )}
    </>
  );
};
export default AttachedFilesDisplay;
