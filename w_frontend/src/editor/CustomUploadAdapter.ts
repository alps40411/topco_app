// w_frontend/src/editor/CustomUploadAdapter.ts

import type { FileLoader } from "ckeditor5";
import { getFullFileUrl } from "../utils/urlUtils";
import { toast } from "react-hot-toast";
import type { FileForUpload } from "../App";

export interface UploadAdapterContext {
  authFetch: ((url: string, options?: RequestInit) => Promise<Response>) | null;
  docDate: string;
  onFileUpload?: (file: FileForUpload) => void;
  isUploading: boolean;
}

class CustomImageUploadAdapter {
  private loader: FileLoader;
  private ctx: { current: UploadAdapterContext };
  private abortController: AbortController | null = null;

  constructor(loader: FileLoader, ctx: { current: UploadAdapterContext }) {
    this.loader = loader;
    this.ctx = ctx;
  }

  async upload(): Promise<{ default: string }> {
    const file = await this.loader.file;
    if (!file) throw new Error("沒有檔案可上傳");

    const { authFetch, docDate, onFileUpload } = this.ctx.current;
    if (!authFetch) throw new Error("尚未登入");

    this.ctx.current.isUploading = true;

    const formData = new FormData();
    formData.append("file", file);

    this.abortController = new AbortController();
    const toastId = `img-upload-${Date.now()}`;

    try {
      toast.loading("上傳中...", { id: toastId });

      const response = await authFetch(
        `/api/records/upload?doc_date=${docDate}`,
        { method: "POST", body: formData, signal: this.abortController.signal }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        const reason = errorData?.detail || `HTTP ${response.status}`;
        throw new Error(reason);
      }

      const uploadedFile = await response.json();

      // 通知父組件
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

      toast.success("圖片上傳成功", { id: toastId });

      // 回傳 URL 讓 CKEditor 自動插入圖片
      const imageUrl = getFullFileUrl(uploadedFile.url);
      return { default: imageUrl };
    } catch (error: any) {
      if (error?.name === "AbortError") {
        toast.dismiss(toastId);
        throw error;
      }
      console.error("[CustomUploadAdapter] 上傳錯誤:", error);
      toast.error(error.message, { id: toastId });
      throw error;
    } finally {
      setTimeout(() => {
        this.ctx.current.isUploading = false;
      }, 100);
    }
  }

  abort(): void {
    this.abortController?.abort();
  }
}

/**
 * 建立 CKEditor Upload Adapter Plugin 的工廠函式
 * 統一處理圖片按鈕上傳、剪貼簿貼上、拖放上傳
 */
export function createCustomUploadAdapterPlugin(
  contextRef: { current: UploadAdapterContext }
) {
  return function CustomUploadAdapterPlugin(editor: any) {
    editor.plugins.get("FileRepository").createUploadAdapter = (
      loader: FileLoader
    ) => {
      return new CustomImageUploadAdapter(loader, contextRef);
    };
  };
}
