// frontend/src/components/AttachedFilesManager.tsx

import React from "react";
import { FileText, Trash2, CheckSquare, Square } from "lucide-react";
import type { FileForUpload } from "../App";
import { getFullFileUrl } from "../utils/urlUtils";

interface AttachedFilesManagerProps {
  files: FileForUpload[];
  onRemoveFile: (fileUrl: string) => void;
  onAiSelectionChange: (fileUrl: string, isSelected: boolean) => void;
  isUploading: boolean;
}

const AttachedFilesManager: React.FC<AttachedFilesManagerProps> = ({
  files,
  onRemoveFile,
  onAiSelectionChange,
  isUploading,
}) => {
  // 如果沒有檔案且不在上傳中，則不顯示任何東西
  if (files.length === 0 && !isUploading) {
    return null;
  }

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        附加檔案 (可勾選是否讓AI使用)
      </label>
      <div className="space-y-2">
        {files.map((file) => (
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
              <a
                href={getFullFileUrl(file.url)}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-2 text-sm font-medium text-gray-800 truncate hover:underline"
                title={file.name}
              >
                {file.name}
              </a>
            </div>

            {/* 右側：勾選和刪除按鈕 */}
            <div className="flex items-center flex-shrink-0 ml-4">
              <button
                onClick={() =>
                  onAiSelectionChange(file.url, !file.is_selected_for_ai)
                }
                className="p-1 text-gray-500 hover:text-gray-800"
                title={
                  file.is_selected_for_ai ? "取消 AI 使用" : "勾選給 AI 使用"
                }
              >
                {file.is_selected_for_ai ? (
                  <CheckSquare className="w-5 h-5 text-green-600" />
                ) : (
                  <Square className="w-5 h-5" />
                )}
              </button>
              <button
                onClick={() => onRemoveFile(file.url)}
                className="p-1 text-gray-500 hover:text-red-600"
                title="移除檔案"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
          </div>
        ))}

        {/* 如果正在上傳，顯示一個提示 */}
        {isUploading && (
          <div className="flex items-center p-2 text-sm text-gray-500">
            <svg
              className="animate-spin -ml-1 mr-2 h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              ></circle>
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            檔案處理中...
          </div>
        )}
      </div>
    </div>
  );
};

export default AttachedFilesManager;
