// frontend/src/components/AttachedFilesManager.tsx

import React, { useRef, useState } from 'react';
import { Upload, Plus, X, Image, File, BrainCircuit, Loader2 } from 'lucide-react';
import type { FileForUpload } from '../App';

interface AttachedFilesManagerProps {
  files: FileForUpload[];
  onFileUpload: (files: FileList) => void;
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
  const [isDragging, setIsDragging] = useState(false);
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);
  const dragCounter = useRef(0);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      onFileUpload(event.target.files);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragIn = (e: React.DragEvent) => {
    handleDrag(e);
    dragCounter.current++;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  };

  const handleDragOut = (e: React.DragEvent) => {
    handleDrag(e);
    dragCounter.current--;
    if (dragCounter.current === 0) {
      setIsDragging(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    handleDrag(e);
    setIsDragging(false);
    dragCounter.current = 0;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileUpload(e.dataTransfer.files);
      e.dataTransfer.clearData();
    }
  };

  const getFullUrl = (url: string) => url.startsWith('http') ? url : `/${url}`;

  return (
    <>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">附加檔案</label>
        <div 
          onDragEnter={handleDragIn}
          onDragLeave={handleDragOut}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors duration-200 ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}`}>
          <input ref={fileInputRef} type="file" multiple onChange={handleFileSelect} className="hidden" />
          <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
          <p className="text-sm text-gray-600 mb-2">點擊上傳或拖曳檔案到此處</p>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center px-3 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200"
          >
            <Plus className="w-4 h-4 mr-2" /> 選擇檔案
          </button>
        </div>

        {isUploading && (
            <div className="flex items-center text-sm text-blue-600 mt-2">
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                <span>檔案上傳中...</span>
            </div>
        )}

        {files && files.length > 0 && (
          <div className="mt-4 space-y-2">
            <div className="flex items-center p-2 bg-green-50 border border-green-200 text-green-800 text-xs font-medium rounded-lg">
              <BrainCircuit className="w-4 h-4 mr-2"/>
              <span>勾選檔案，即可在「AI 日報編輯」中作為參考資料使用。</span>
            </div>
            {files.map((file) => (
              <div key={file.url} className="flex items-center justify-between bg-gray-50 p-2 rounded-lg">
                <div className="flex items-center space-x-3 flex-grow overflow-hidden">
                  <input
                    type="checkbox"
                    checked={!!file.is_selected_for_ai}
                    onChange={(e) => onAiSelectionChange(file.url, e.target.checked)}
                    className="h-5 w-5 rounded border-gray-300 text-green-600 focus:ring-green-500 cursor-pointer flex-shrink-0"
                  />
                  {file.type.startsWith('image/') ? (
                    <img 
                      src={getFullUrl(file.url)} 
                      alt={file.name}
                      onClick={() => setPreviewImageUrl(getFullUrl(file.url))}
                      className="w-12 h-12 object-cover rounded-md cursor-pointer flex-shrink-0"
                    />
                  ) : (
                    <div className="w-12 h-12 flex items-center justify-center bg-gray-200 rounded-md flex-shrink-0">
                      {getFileIcon(file.type)}
                    </div>
                  )}
                  <div className="overflow-hidden">
                    <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
                    <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                  </div>
                </div>
                <button onClick={() => onRemoveFile(file.url)} className="p-1 text-red-400 hover:text-red-600 flex-shrink-0 ml-2">
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
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

export default AttachedFilesManager;
