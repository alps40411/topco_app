import React from 'react';
import { Info } from 'lucide-react';
import { Tooltip } from './ui/Tooltip';
import { SUPPORTED_FILE_TYPES, getTotalFileTypeCount } from '../constants/fileTypes';

export interface FileTypeInfoProps {
  className?: string;
}

/**
 * 檔案類型資訊提示組件
 * 顯示支援的檔案類型及其分類
 */
export const FileTypeInfo: React.FC<FileTypeInfoProps> = ({ className = '' }) => {
  const totalCount = getTotalFileTypeCount();

  // 生成 Tooltip 內容
  const tooltipContent = (
    <div className="text-left whitespace-normal max-w-md">
      <div className="font-semibold mb-2 text-white">支援的檔案類型</div>
      <div className="space-y-2">
        {SUPPORTED_FILE_TYPES.map((category, index) => (
          <div key={index} className="text-xs">
            <div className="font-medium text-gray-200 mb-1">
              <span className="mr-1">{category.icon}</span>
              {category.name}
            </div>
            <div className="text-gray-300 pl-5">
              {category.extensions.join(', ')}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div
      className={`
        flex items-center gap-2 px-3 py-2 mb-2
        bg-blue-50 border border-blue-200 rounded-lg
        text-sm text-blue-800
        ${className}
      `}
    >
      <Info className="w-4 h-4 flex-shrink-0" />
      <span className="flex-1">
        支援上傳 <span className="font-semibold">{totalCount}</span> 種檔案格式
      </span>
      <Tooltip content={tooltipContent} position="bottom" className="max-w-md whitespace-normal">
        <button
          type="button"
          className="
            flex items-center justify-center
            w-5 h-5 rounded-full
            bg-blue-200 hover:bg-blue-300
            text-blue-700
            transition-colors
            focus:outline-none focus:ring-2 focus:ring-blue-400
          "
          aria-label="查看支援的檔案類型"
        >
          <Info className="w-3 h-3" />
        </button>
      </Tooltip>
    </div>
  );
};

export default FileTypeInfo;
