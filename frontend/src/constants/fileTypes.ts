/**
 * 檔案類型配置
 * 定義系統支援的檔案類型及其分類
 */

export interface FileTypeCategory {
  name: string;
  icon: string;
  extensions: string[];
  description: string;
}

export const SUPPORTED_FILE_TYPES: FileTypeCategory[] = [
  {
    name: '文件類',
    icon: '📄',
    extensions: ['.pdf', '.docx', '.xlsx', '.pptx', '.doc', '.xls', '.ppt', '.rtf', '.odt', '.ods', '.wps', '.pages', '.txt', '.csv'],
    description: '支援各種文件格式'
  },
  {
    name: '圖片類',
    icon: '🖼️',
    extensions: ['.jpg', '.png', '.jpeg', '.webp', '.gif'],
    description: '支援常見圖片格式'
  },
  {
    name: '壓縮檔',
    icon: '📦',
    extensions: ['.zip', '.rar', '.7z'],
    description: '支援壓縮檔案格式'
  },
  {
    name: '設計檔',
    icon: '🎨',
    extensions: ['.ai', '.psd', '.dwg', '.eps', '.vsdx'],
    description: '支援設計軟體格式'
  },
  {
    name: '媒體檔',
    icon: '🎬',
    extensions: ['.mp4', '.avi'],
    description: '支援影片格式'
  },
  {
    name: '其他格式',
    icon: '📋',
    extensions: ['.log', '.eml', '.ics', '.kml', '.xml'],
    description: '支援其他格式'
  }
];

/**
 * 取得所有支援的檔案類型（扁平化陣列）
 */
export const getAllSupportedExtensions = (): string[] => {
  return SUPPORTED_FILE_TYPES.flatMap(category => category.extensions);
};

/**
 * 取得檔案類型總數
 */
export const getTotalFileTypeCount = (): number => {
  return getAllSupportedExtensions().length;
};

/**
 * 檢查檔案類型是否被支援
 */
export const isSupportedFileType = (filename: string): boolean => {
  const ext = filename.toLowerCase().substring(filename.lastIndexOf('.'));
  return getAllSupportedExtensions().includes(ext);
};
