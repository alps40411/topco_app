// frontend/src/components/AttachedFilesManager.tsx

import React, { useRef } from 'react';
import { Upload, Plus, X, Image, File, BrainCircuit } from 'lucide-react';
import type { FileForUpload } from '../App';

interface AttachedFilesManagerProps {
  files: FileForUpload[];
  onFileUpload: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onRemoveFile: (fileUrl: string) => void;
  onAiSelectionChange: (fileUrl: string, isSelected: boolean) => void;
  isUploading: boolean;
}

const getFileIcon = (type: string) => {
    if (type?.startsWith('image/')) return <Image className="w-4 h-4 text-gray-500" />;
    return <File className="w-4 h-4 text-gray-500" />;
};

const formatFileSize = (bytes: number) => {
    if (!bytes || bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const AttachedFilesManager: React.FC<AttachedFilesManagerProps> = ({
  files,
  onFileUpload,
  onRemoveFile,
  onAiSelectionChange,
  isUploading,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">附加檔案</label>
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-gray-400">
        <input ref={fileInputRef} type="file" multiple onChange={onFileUpload} className="hidden" />
        <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
        <p className="text-sm text-gray-600 mb-2">點擊上傳或拖曳檔案</p>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="inline-flex items-center px-3 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200"
        >
          <Plus className="w-4 h-4 mr-2" /> 選擇檔案
        </button>
      </div>

      {isUploading && <p className="text-sm text-blue-600 mt-2">檔案上傳中...</p>}

      {files && files.length > 0 && (
        <div className="mt-4 space-y-2">
          <div className="flex items-center p-2 bg-green-50 border border-green-200 text-green-800 text-xs font-medium rounded-lg">
            <BrainCircuit className="w-4 h-4 mr-2"/>
            <span>勾選檔案，即可在「AI 日報編輯」中作為參考資料使用。</span>
          </div>
          {files.map((file) => (
            <div key={file.url} className="flex items-center justify-between bg-gray-50 p-2 rounded-lg">
              <div className="flex items-center space-x-3 flex-grow">
                <input
                  type="checkbox"
                  checked={!!file.is_selected_for_ai}
                  onChange={(e) => onAiSelectionChange(file.url, e.target.checked)}
                  className="h-5 w-5 rounded border-gray-300 text-green-600 focus:ring-green-500 cursor-pointer"
                />
                {getFileIcon(file.type)}
                <div>
                  <p className="text-sm font-medium text-gray-900">{file.name}</p>
                  <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                </div>
              </div>
              <button onClick={() => onRemoveFile(file.url)} className="p-1 text-red-400 hover:text-red-600">
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AttachedFilesManager;