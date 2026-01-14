import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { getAllSupportedExtensions } from '../constants/fileTypes';

export interface FileTypeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * 檔案類型 Modal 組件
 * 顯示所有支援的檔案類型
 */
export const FileTypeModal: React.FC<FileTypeModalProps> = ({ isOpen, onClose }) => {
  const supportedExtensions = getAllSupportedExtensions();

  // ESC 鍵關閉 modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // 鎖定背景滾動
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }

    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
      onClick={onClose}
    >
      <div
        className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            支援的檔案類型
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="關閉"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto max-h-[60vh]">
          <p className="text-sm text-gray-600 mb-3">
            目前支援上傳以下 <span className="font-semibold text-gray-900">{supportedExtensions.length}</span> 種檔案格式：
          </p>
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <p className="text-sm text-gray-700 leading-relaxed">
              {supportedExtensions.join(', ')}
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            確定
          </button>
        </div>
      </div>
    </div>
  );
};

export default FileTypeModal;
