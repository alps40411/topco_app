// frontend/src/editor/PaperclipPlugin.ts

import { Plugin, ButtonView } from "ckeditor5";
import { toast } from "react-hot-toast";
import type { FileForUpload } from "../App";
import { isSupportedFileType } from "../constants/fileTypes";

export interface PaperclipContext {
  authFetch: ((url: string, options?: RequestInit) => Promise<Response>) | null;
  docDate: string;
  onFileUpload?: (file: FileForUpload) => void;
  isUploading: boolean;
}

// 與現有 Quill 版本相同的迴紋針 SVG 圖示
const PAPERCLIP_ICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.59a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>`;

/**
 * 建立迴紋針附件上傳 Plugin 的工廠函式
 * 上傳檔案但不插入編輯器，僅透過 onFileUpload 通知父組件
 */
export function createPaperclipPlugin(
  contextRef: { current: PaperclipContext }
) {
  return class PaperclipPluginClass extends Plugin {
    static get pluginName() {
      return "PaperclipPlugin" as const;
    }

    init() {
      const editor = this.editor;

      editor.ui.componentFactory.add("paperclip", (locale) => {
        const buttonView = new ButtonView(locale);

        buttonView.set({
          label: "附加檔案",
          icon: PAPERCLIP_ICON,
          tooltip: true,
        });

        buttonView.on("execute", () => {
          const input = document.createElement("input");
          input.type = "file";
          input.accept = "*/*";
          input.multiple = true;
          input.style.display = "none";

          input.onchange = () => {
            const files = input.files ? Array.from(input.files) : [];
            input.remove();

            if (files.length === 0) return;

            const { authFetch, docDate, onFileUpload } = contextRef.current;
            if (!authFetch) return;

            contextRef.current.isUploading = true;

            (async () => {
              try {
                for (const file of files) {
                  const toastId = `file-upload-${file.name}`;

                  // 檢查副檔名是否支援
                  if (!isSupportedFileType(file.name)) {
                    const ext = file.name.substring(file.name.lastIndexOf('.'));
                    toast.error(`不支援的檔案格式: ${ext}，請點擊工具列的檔案資訊按鈕查看支援的格式`, { id: toastId, duration: 5000 });
                    continue;
                  }

                  const formData = new FormData();
                  formData.append("file", file);

                  try {
                    toast.loading(`上傳 ${file.name}...`, { id: toastId });

                    const response = await authFetch(
                      `/api/records/upload?doc_date=${docDate}`,
                      { method: "POST", body: formData }
                    );

                    if (!response.ok) {
                      const errorData = await response.json().catch(() => null);
                      const reason =
                        errorData?.detail || `HTTP ${response.status}`;
                      throw new Error(reason);
                    }

                    const uploadedFile = await response.json();

                    if (onFileUpload) {
                      onFileUpload({
                        name: uploadedFile.name,
                        type: uploadedFile.type,
                        size: uploadedFile.size,
                        url: uploadedFile.url,
                        file_path: uploadedFile.file_path,
                        is_selected_for_ai: false,
                      });
                    }

                    toast.success(`${file.name} 上傳成功`, { id: toastId });
                  } catch (error: any) {
                    console.error(error);
                    toast.error(error.message, { id: toastId });
                  }
                }
              } finally {
                setTimeout(() => {
                  contextRef.current.isUploading = false;
                }, 100);
              }
            })();
          };

          document.body.appendChild(input);
          input.click();
        });

        return buttonView;
      });
    }
  };
}
