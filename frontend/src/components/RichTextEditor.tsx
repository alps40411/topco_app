// frontend/src/components/RichTextEditor.tsx

import React, { useRef, useCallback, useMemo, useEffect } from "react";
import ReactQuill from "react-quill";
import "react-quill/dist/quill.snow.css";
import "../styles/quill-custom.css";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "react-hot-toast";
import type { FileForUpload } from "../App";

// 在模組載入時註冊 paperclip 圖示（只執行一次）
const icons = ReactQuill.Quill.import("ui/icons");
if (!icons["paperclip"]) {
  icons["paperclip"] = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.59a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>`;
}

interface RichTextEditorProps {
  value: string;
  onChange: (content: string) => void;
  onFileUpload?: (file: FileForUpload) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

const RichTextEditor: React.FC<RichTextEditorProps> = ({
  value,
  onChange,
  onFileUpload,
  placeholder = "記錄您的想法... (可直接貼上圖片)",
  disabled = false,
  className = "",
}) => {
  const quillRef = useRef<ReactQuill>(null);
  const { authFetch } = useAuth();

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
        const range = quill.getSelection(true);
        const imageUrl = uploadedFile.url.startsWith("http")
          ? uploadedFile.url
          : `http://localhost:8000${uploadedFile.url}`;
        quill.insertEmbed(range.index, "image", imageUrl);
        quill.setSelection(range.index + 1, 0);
      } catch (error: any) {
        console.error(error);
        toast.error(error.message);
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
        } catch (error: any) {
          console.error(error);
          toast.error(error.message);
        }
      }
    };
  }, [authFetch, onFileUpload]);

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
            const range = quill.getSelection(true);
            const imageUrl = uploadedFile.url.startsWith("http")
              ? uploadedFile.url
              : `http://localhost:8000${uploadedFile.url}`;
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
