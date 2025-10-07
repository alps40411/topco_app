// frontend/src/components/RichTextEditor.tsx

import React, { useRef, useCallback, useMemo, useEffect } from "react";
import ReactQuill from "react-quill";
import "react-quill/dist/quill.snow.css";
import "../styles/quill-custom.css";
import { useAuth } from "../hooks/useAuth";
import { toast } from "react-hot-toast";
import type { FileForUpload } from "../App";
import { getFullFileUrl } from "../utils/urlUtils";

// 在模組載入時註冊 paperclip 圖示（只執行一次）
const icons = ReactQuill.Quill.import("ui/icons");
if (!icons["paperclip"]) {
  icons[
    "paperclip"
  ] = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.59a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>`;
}

interface RichTextEditorProps {
  value: string;
  onChange: (content: string) => void;
  onFileUpload?: (file: FileForUpload) => void;
  onFileRemove?: (fileUrl: string) => void;
  files?: FileForUpload[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

const RichTextEditor: React.FC<RichTextEditorProps> = ({
  value,
  onChange,
  onFileUpload,
  onFileRemove,
  files = [],
  placeholder = "記錄您的想法... (可直接貼上圖片或者附上檔案)",
  disabled = false,
  className = "",
}) => {
  const quillRef = useRef<ReactQuill>(null);
  const { authFetch } = useAuth();
  const previousContentRef = useRef<string>(value);
  const isUploadingRef = useRef<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // 在組件掛載時創建一個可重用的 file input
  useEffect(() => {
    const input = document.createElement('input');
    input.type = 'file';
    input.style.display = 'none';
    document.body.appendChild(input);
    fileInputRef.current = input;

    // 組件卸載時清理
    return () => {
      if (input.parentNode) {
        input.parentNode.removeChild(input);
      }
      fileInputRef.current = null;
    };
  }, []);

  // 處理圖片上傳並插入編輯器
  const handleImageUpload = useCallback(() => {
    const input = fileInputRef.current;
    if (!input) return;

    // 配置 input
    input.accept = 'image/*';
    input.multiple = false;

    input.onchange = (event) => {
      const file = input.files?.[0];
      
      // 重置 onchange 以便下次觸發
      input.onchange = null;
      // 清空 value 允相同檔案可以再次上傳
      input.value = '';

      if (!file) {
        return;
      }

      const quill = quillRef.current?.getEditor();
      if (!quill || !authFetch) {
        return;
      }

      queueMicrotask(async () => {
        const formData = new FormData();
        formData.append("file", file);
        const range = quill.getSelection(true) || { index: quill.getLength() - 1, length: 0 };
        const placeholderIndex = range.index;

        try {
          isUploadingRef.current = true;
          toast.loading('上傳中...', { id: 'image-upload' });

          const response = await authFetch("/api/records/upload", {
            method: "POST",
            body: formData,
          });

          if (!response.ok) throw new Error(`圖片 ${file.name} 上傳失敗`);

          const uploadedFile = await response.json();

          if (onFileUpload) {
            onFileUpload({
              name: uploadedFile.name,
              type: uploadedFile.type,
              size: uploadedFile.size,
              url: uploadedFile.url,
              is_selected_for_ai: false,
            });
          }

          const imageUrl = getFullFileUrl(uploadedFile.url);
          quill.insertEmbed(placeholderIndex, "image", imageUrl);
          quill.setSelection(placeholderIndex + 1, 0);

          setTimeout(() => {
            previousContentRef.current = quill.root.innerHTML;
          }, 50);

          toast.success('圖片上傳成功', { id: 'image-upload' });
        } catch (error: any) {
          console.error('[RichTextEditor] 上傳錯誤:', error);
          toast.error(error.message, { id: 'image-upload' });
        } finally {
          setTimeout(() => {
            isUploadingRef.current = false;
          }, 100);
        }
      });
    };

    input.click();
  }, [authFetch, onFileUpload]);

  // 處理一般檔案上傳（不插入編輯器）
  const handlePaperclipUpload = useCallback(() => {
    const input = fileInputRef.current;
    if (!input) return;

    // 配置 input
    input.accept = '*/*'; // 接受所有檔案
    input.multiple = true;

    input.onchange = () => {
      const files = input.files;
      
      // 重置 onchange 和 value
      input.onchange = null;
      input.value = '';

      if (!files || files.length === 0 || !authFetch) return;

      queueMicrotask(async () => {
        isUploadingRef.current = true;
        try {
          for (const file of Array.from(files)) {
            const formData = new FormData();
            formData.append("file", file);

            try {
              toast.loading(`上傳 ${file.name}...`, { id: `file-upload-${file.name}` });

              const response = await authFetch("/api/records/upload", {
                method: "POST",
                body: formData,
              });

              if (!response.ok) throw new Error(`檔案 ${file.name} 上傳失敗`);

              const uploadedFile = await response.json();

              if (onFileUpload) {
                onFileUpload({
                  name: uploadedFile.name,
                  type: uploadedFile.type,
                  size: uploadedFile.size,
                  url: uploadedFile.url,
                  is_selected_for_ai: false,
                });
              }

              toast.success(`${file.name} 上傳成功`, { id: `file-upload-${file.name}` });
            } catch (error: any) {
              console.error(error);
              toast.error(error.message, { id: `file-upload-${file.name}` });
            }
          }
        } finally {
          setTimeout(() => {
            isUploadingRef.current = false;
          }, 100);
        }
      });
    };

    input.click();
  }, [authFetch, onFileUpload]);

  // 偵測編輯器內圖片被刪除（透過退格鍵或其他方式）
  useEffect(() => {
    const quill = quillRef.current?.getEditor();
    if (!quill || !onFileRemove) {
      return;
    }

    let deleteCheckTimeout: NodeJS.Timeout | null = null;

    const handleTextChange = (delta: any, oldContents: any, source: string) => {
      // 只處理用戶操作，忽略 API 或程式碼觸發的變更
      if (source !== "user") return;

      // 如果正在上傳，跳過檢查（避免誤刪）
      if (isUploadingRef.current) return;

      // 清除之前的延遲檢查
      if (deleteCheckTimeout) {
        clearTimeout(deleteCheckTimeout);
      }

      // 使用 oldContents 重建之前的 HTML
      const tempDiv = document.createElement('div');
      const tempQuill = new (quill.constructor as any)(tempDiv);
      tempQuill.setContents(oldContents);
      const previousContent = tempDiv.querySelector('.ql-editor')?.innerHTML || previousContentRef.current;

      // 延遲 200ms 檢查，避免誤判移動為刪除
      deleteCheckTimeout = setTimeout(() => {
        const currentContent = quill.root.innerHTML;

        // 提取當前內容中的所有圖片 URL
        const currentImages = new Set<string>();
        const imgRegex = /<img[^>]+src="([^">]+)"/g;
        let match;
        while ((match = imgRegex.exec(currentContent)) !== null) {
          currentImages.add(match[1]);
        }

        // 提取之前內容中的所有圖片 URL
        const previousImages = new Set<string>();
        const imgRegex2 = /<img[^>]+src="([^">]+)"/g;
        while ((match = imgRegex2.exec(previousContent)) !== null) {
          previousImages.add(match[1]);
        }

        // 只有在圖片數量減少時才檢查刪除（移動不會減少數量）
        if (currentImages.size < previousImages.size) {
          // 找出被刪除的圖片
          for (const imageUrl of previousImages) {
            if (!currentImages.has(imageUrl)) {
              // 圖片從編輯器中被移除了
              // 直接將從 <img> 標籤 src 中獲取的完整 URL 傳遞給父元件
              onFileRemove(imageUrl);
            }
          }
        }

        // 更新 ref
        previousContentRef.current = currentContent;
      }, 200); // 延遲 200ms，讓移動操作有時間完成
    };

    quill.on("text-change", handleTextChange);

    return () => {
      quill.off("text-change", handleTextChange);
      if (deleteCheckTimeout) {
        clearTimeout(deleteCheckTimeout);
      }
    };
  }, [onFileRemove]);

  // 當 value 從外部改變時同步 previousContentRef
  useEffect(() => {
    previousContentRef.current = value;
  }, [value]);

  // 處理剪貼簿圖片貼上
  useEffect(() => {
    const quill = quillRef.current?.getEditor();
    if (!quill || !authFetch) return;

    const handlePaste = async (event: ClipboardEvent) => {
      const clipboardData = event.clipboardData;
      if (!clipboardData) return;

      const items = clipboardData.items;
      for (let i = 0; i < items.length; i++) {
        if (items[i].kind === "file" && items[i].type.startsWith("image/")) {
          event.preventDefault();

          const file = items[i].getAsFile();
          if (!file) continue;

          const formData = new FormData();
          formData.append("file", file);

          try {
            isUploadingRef.current = true;
            toast.loading('上傳中...', { id: 'paste-upload' });

            const response = await authFetch("/api/records/upload", {
              method: "POST",
              body: formData,
            });

            if (!response.ok) throw new Error("圖片上傳失敗");

            const uploadedFile = await response.json();

            // 回調通知父元件
            if (onFileUpload) {
              onFileUpload({
                name: uploadedFile.name,
                type: uploadedFile.type,
                size: uploadedFile.size,
                url: uploadedFile.url,
                is_selected_for_ai: false,
              });
            }

            // 插入圖片到編輯器
            const range = quill.getSelection(true) || { index: quill.getLength() - 1, length: 0 };
            const imageUrl = getFullFileUrl(uploadedFile.url);
            quill.insertEmbed(range.index, "image", imageUrl);
            quill.setSelection(range.index + 1, 0);

            // 更新 previousContentRef
            setTimeout(() => {
              previousContentRef.current = quill.root.innerHTML;
            }, 50);

            toast.success('圖片上傳成功', { id: 'paste-upload' });
          } catch (error: any) {
            console.error(error);
            toast.error(error.message, { id: 'paste-upload' });
          } finally {
            setTimeout(() => {
              isUploadingRef.current = false;
            }, 100);
          }

          break;
        }
      }
    };

    quill.root.addEventListener("paste", handlePaste);

    return () => {
      quill.root.removeEventListener("paste", handlePaste);
    };
  }, [authFetch, onFileUpload]);

  // 工具列模組配置
  const modules = useMemo(
    () => ({
      toolbar: {
        container: [
          ["bold", "italic", "underline", "strike"],
          [{ list: "ordered" }, { list: "bullet" }],
          ["link", "image", "paperclip"],
          ["clean"],
        ],
        handlers: {
          image: handleImageUpload,
          paperclip: handlePaperclipUpload,
        },
      },
    }),
    [handleImageUpload, handlePaperclipUpload]
  );

  // 格式配置
  const formats = [
    "header",
    "bold",
    "italic",
    "underline",
    "strike",
    "list",
    "bullet",
    "link",
    "image",
  ];

  return (
    <ReactQuill
      ref={quillRef}
      theme="snow"
      value={value}
      onChange={onChange}
      modules={modules}
      formats={formats}
      placeholder={placeholder}
      readOnly={disabled}
      className={`bg-white ${className}`}
    />
  );
};

export default RichTextEditor;
