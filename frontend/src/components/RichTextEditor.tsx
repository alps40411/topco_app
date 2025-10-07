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

  // 處理圖片上傳並插入編輯器
  const handleImageUpload = useCallback(() => {
    const input = document.createElement("input");
    input.setAttribute("type", "file");
    input.setAttribute("accept", "image/*");
    input.click();

    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;

      const quill = quillRef.current?.getEditor();
      if (!quill || !authFetch) return;

      const formData = new FormData();
      formData.append("file", file);

      try {
        toast.loading('上傳中...', { id: 'image-upload' });

        const response = await authFetch("/api/records/upload", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) throw new Error(`圖片 ${file.name} 上傳失敗`);

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

        toast.success('圖片上傳成功', { id: 'image-upload' });
      } catch (error: any) {
        console.error(error);
        toast.error(error.message, { id: 'image-upload' });
      }
    };
  }, [authFetch, onFileUpload]);

  // 處理一般檔案上傳（不插入編輯器）
  const handlePaperclipUpload = useCallback(() => {
    const input = document.createElement("input");
    input.setAttribute("type", "file");
    input.setAttribute("multiple", "true");
    input.click();

    input.onchange = async () => {
      const files = input.files;
      if (!files || files.length === 0 || !authFetch) return;

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

          toast.success(`${file.name} 上傳成功`, { id: `file-upload-${file.name}` });
        } catch (error: any) {
          console.error(error);
          toast.error(error.message, { id: `file-upload-${file.name}` });
        }
      }
    };
  }, [authFetch, onFileUpload]);

  // 偵測編輯器內圖片被刪除（透過退格鍵或其他方式）
  useEffect(() => {
    console.log('[RichTextEditor] Setting up text-change listener');
    const quill = quillRef.current?.getEditor();
    if (!quill || !authFetch || !onFileRemove) {
      console.log('[RichTextEditor] Skip setup - missing:', {
        quill: !!quill,
        authFetch: !!authFetch,
        onFileRemove: !!onFileRemove
      });
      return;
    }

    let isProcessing = false;

    const handleTextChange = (delta: any, oldContents: any, source: string) => {
      console.log('[RichTextEditor] text-change event:', { source, isProcessing });

      // 只處理用戶操作，忽略 API 或程式碼觸發的變更
      if (source !== "user") return;
      if (isProcessing) return;

      // ⚠️ 關鍵：用 oldContents 來重建之前的 HTML，而不是依賴 ref
      // 因為 ref 可能已經被其他 useEffect 更新了
      const tempDiv = document.createElement('div');
      const tempQuill = new (quill.constructor as any)(tempDiv);
      tempQuill.setContents(oldContents);
      const previousContent = tempDiv.querySelector('.ql-editor')?.innerHTML || previousContentRef.current;

      console.log('[RichTextEditor] Previous content from oldContents:', previousContent);

      // 使用 setTimeout 確保 DOM 已更新
      setTimeout(() => {
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

        console.log('[RichTextEditor] Image count:', {
          current: currentImages.size,
          previous: previousImages.size,
          currentUrls: Array.from(currentImages),
          previousUrls: Array.from(previousImages)
        });

        // 只有在圖片數量減少時才檢查刪除（拖移不會改變數量）
        if (currentImages.size < previousImages.size) {
          isProcessing = true;
          // 找出被刪除的圖片
          for (const imageUrl of previousImages) {
            if (!currentImages.has(imageUrl)) {
              // 圖片從編輯器中被移除了
              // 從完整 URL 中提取相對路徑
              let fileUrl = imageUrl;
              if (imageUrl.startsWith("http")) {
                const url = new URL(imageUrl);
                fileUrl = url.pathname;
              }

              console.log('[RichTextEditor] 偵測到圖片被刪除，呼叫 onFileRemove:', fileUrl);
              // 通知父元件並刪除檔案
              onFileRemove(fileUrl);
            }
          }
          setTimeout(() => {
            isProcessing = false;
          }, 100);
        }

        // 更新 ref
        previousContentRef.current = currentContent;
      }, 0);
    };

    quill.on("text-change", handleTextChange);
    console.log('[RichTextEditor] text-change listener added');

    return () => {
      console.log('[RichTextEditor] Removing text-change listener');
      quill.off("text-change", handleTextChange);
    };
  }, [authFetch, onFileRemove]);

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
          } catch (error: any) {
            console.error(error);
            toast.error(error.message);
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
