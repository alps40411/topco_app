// frontend/src/components/AttachedFilesDisplay.tsx

import React from "react";
import { FileText, Download, BrainCircuit } from "lucide-react";
import type { FileForUpload } from "../App";
import { getFullFileUrl } from "../utils/urlUtils";

interface AttachedFilesDisplayProps {
  files?: FileForUpload[];
  content?: string; // 編輯器內容，用於判斷圖片是否已在編輯器中
}

const AttachedFilesDisplay: React.FC<AttachedFilesDisplayProps> = ({
  files,
  content = "",
}) => {
  // 智慧過濾：顯示非圖片檔案，以及未插入編輯器的圖片檔案
  const displayFiles = files?.filter((file) => {
    // 非圖片檔案總是顯示
    if (!file.type?.startsWith("image/")) {
      return true;
    }

    // 對於圖片檔案，檢查是否在編輯器內容中
    // 如果圖片在編輯器中，則不在附加檔案區顯示（避免重複）
    const fullUrl = getFullFileUrl(file.url);

    // ✅ 修正：同時檢查 HTML 編碼和未編碼的 URL
    // HTML 中的 & 會被編碼為 &amp;
    const htmlEncodedUrl = fullUrl.replace(/&/g, '&amp;');
    const htmlEncodedFileUrl = file.url.replace(/&/g, '&amp;');

    const isInEditor =
      content.includes(fullUrl) ||
      content.includes(file.url) ||
      content.includes(htmlEncodedUrl) ||
      content.includes(htmlEncodedFileUrl);

    return !isInEditor;
  });

  if (!displayFiles || displayFiles.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 border-t pt-3">
      <h4 className="text-sm font-semibold text-gray-600 mb-2">附加檔案</h4>
      <div className="space-y-2">
        {displayFiles.map((file) => (
          <div
            key={file.url}
            className={`flex items-center justify-between p-2 rounded-lg border transition-colors duration-200 ${
              file.is_selected_for_ai
                ? "bg-green-50 border-green-200"
                : "bg-gray-50 border-gray-200"
            }`}
          >
            {/* 左側：圖示和檔名 */}
            <div className="flex items-center min-w-0">
              <FileText
                className={`w-5 h-5 flex-shrink-0 ${
                  file.is_selected_for_ai ? "text-green-600" : "text-gray-500"
                }`}
              />
              <span
                className="ml-2 text-sm font-medium text-gray-800 truncate"
                title={file.name}
              >
                {file.name}
              </span>
            </div>

            {/* 右側：AI 圖示和下載按鈕 */}
            <div className="flex items-center flex-shrink-0 ml-4 space-x-2">
              {file.is_selected_for_ai && (
                <BrainCircuit
                  className="w-5 h-5 text-green-600"
                  title="此檔案已被選取給 AI 使用"
                />
              )}
              <a
                href={getFullFileUrl(file.url)}
                download={file.name} // 使用 download 屬性來觸發下載
                className="inline-flex items-center p-1 text-gray-500 hover:text-blue-600"
                title={`下載 ${file.name}`}
              >
                <Download className="w-5 h-5" />
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AttachedFilesDisplay;
