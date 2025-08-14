// frontend/src/components/AttachedFilesDisplay.tsx

import React, { useState } from 'react';
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
    const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);

    if (!files || files.length === 0) return null;

    const getFullUrl = (url: string) => url.startsWith('http') ? url : `/${url}`;

    return (
      <>
        <div className="mt-3 border-t border-gray-200 pt-3">
          <h4 className="text-xs font-bold text-gray-500 mb-2">附件:</h4>
          <div className="flex flex-wrap gap-2">
            {files.map((file) => (
              <div
                key={file.id || file.url}
                onClick={() => file.type.startsWith('image/') && setPreviewImageUrl(getFullUrl(file.url))}
                className={`relative group inline-flex items-center border rounded text-xs transition-colors overflow-hidden cursor-pointer ${
                  file.is_selected_for_ai
                    ? 'bg-green-100 border-green-200 text-green-800'
                    : 'bg-white border-gray-200 text-gray-600'
                }`}
              >
                {file.type.startsWith('image/') ? (
                  <img src={getFullUrl(file.url)} alt={file.name} className="w-10 h-10 object-cover" />
                ) : (
                  <div className="w-10 h-10 flex items-center justify-center bg-gray-100">
                    {getFileIcon(file.type)}
                  </div>
                )}
                <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 text-white text-[10px] px-1 py-0.5 truncate group-hover:visible invisible">
                  {file.name}
                </div>
                {file.is_selected_for_ai && <BrainCircuit className="absolute top-1 right-1 w-3 h-3 text-white drop-shadow-md" />}
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