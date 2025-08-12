// frontend/src/components/AttachedFilesDisplay.tsx

import React from 'react';
import { Image, File, BrainCircuit } from 'lucide-react';
import type { FileAttachment } from '../App';

interface AttachedFilesDisplayProps {
  files: FileAttachment[];
}

const getFileIcon = (type: string) => {
    if (type?.startsWith('image/')) return <Image className="w-4 h-4 text-gray-500" />;
    return <File className="w-4 h-4 text-gray-500" />;
};

const AttachedFilesDisplay: React.FC<AttachedFilesDisplayProps> = ({ files }) => {
    if (!files || files.length === 0) return null;
    return (
      <div className="mt-3 border-t border-gray-200 pt-2">
        <h4 className="text-xs font-bold text-gray-500 mb-2">附件:</h4>
        <div className="flex flex-wrap gap-2">
          {files.map((file) => (
            <div
              key={file.id || file.url} // <-- 使用 id 或 url 作為 key
              className={`inline-flex items-center px-2 py-1 border rounded text-xs transition-colors ${
                file.is_selected_for_ai
                  ? 'bg-green-100 border-green-200 text-green-800'
                  : 'bg-white border-gray-200 text-gray-600'
              }`}
            >
              {file.is_selected_for_ai && <BrainCircuit className="w-3 h-3 mr-1" />}
              {getFileIcon(file.type)}
              <span className="ml-1 truncate max-w-20">{file.name}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };
  export default AttachedFilesDisplay;