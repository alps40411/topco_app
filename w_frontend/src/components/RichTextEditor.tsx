// w_frontend/src/components/RichTextEditor.tsx

import React, { useRef, useCallback, useEffect, useState, useMemo } from "react";
import { CKEditor } from "@ckeditor/ckeditor5-react";
import {
  ClassicEditor,
  Essentials,
  Bold,
  Italic,
  Underline,
  Strikethrough,
  List,
  Link,
  Paragraph,
  Image,
  ImageUpload,
  ImageResize,
  FileRepository,
  PasteFromOffice,
  Table,
  TableToolbar,
  Alignment,
} from "ckeditor5";
import "ckeditor5/ckeditor5.css";
import coreTranslations from "ckeditor5/translations/zh.js";
import "../styles/ckeditor-custom.css";
import { useAuth } from "../hooks/useAuth";
import { toast } from "react-hot-toast";
import type { FileForUpload } from "../App";
import { FileTypeModal } from "./FileTypeModal";
import {
  createCustomUploadAdapterPlugin,
  type UploadAdapterContext,
} from "../editor/CustomUploadAdapter";
import { createPaperclipPlugin } from "../editor/PaperclipPlugin";
import { createFileInfoPlugin } from "../editor/FileInfoPlugin";

interface RichTextEditorProps {
  value: string;
  onChange: (content: string) => void;
  onFileUpload?: (file: FileForUpload) => void;
  onFileRemove?: (fileUrl: string) => void;
  files?: FileForUpload[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  docDate?: string; // 日報日期 (YYYYMMDD)
}

/** 從 HTML 中提取所有 <img> 的 src URL */
function extractImageUrls(html: string): Set<string> {
  const urls = new Set<string>();
  const regex = /<img[^>]+src="([^">]+)"/g;
  let match;
  while ((match = regex.exec(html)) !== null) {
    urls.add(match[1]);
  }
  return urls;
}

/** CKEditor 空內容的標準輸出 */
const CKEDITOR_EMPTY_VALUES = ["<p>&nbsp;</p>", "<p></p>", ""];

function isEmptyContent(html: string | undefined | null): boolean {
  if (!html) return true;
  return CKEDITOR_EMPTY_VALUES.includes(html.trim());
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
  docDate,
}) => {
  const { authFetch } = useAuth();
  const editorRef = useRef<ClassicEditor | null>(null);
  const previousImagesRef = useRef<Set<string>>(new Set());
  const [isModalOpen, setIsModalOpen] = useState(false);
  const isInitializedRef = useRef(false);
  // 防止 setData 觸發的 onChange 導致無限迴圈
  const isSettingDataRef = useRef(false);

  // Context Bridge — 讓 CKEditor Plugin 存取最新的 React 狀態
  const editorContextRef = useRef<UploadAdapterContext>({
    authFetch: authFetch,
    docDate:
      docDate || new Date().toISOString().slice(0, 10).replace(/-/g, ""),
    onFileUpload,
    isUploading: false,
  });

  // 每次 render 更新 context ref
  editorContextRef.current.authFetch = authFetch;
  editorContextRef.current.docDate =
    docDate || new Date().toISOString().slice(0, 10).replace(/-/g, "");
  editorContextRef.current.onFileUpload = onFileUpload;

  // 當 value 從外部變化時（如載入資料），同步到 CKEditor
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor || !isInitializedRef.current) return;

    const currentData = editor.getData();
    // 正規化比較：避免空值差異
    const normalizedValue = isEmptyContent(value) ? "" : value;
    const normalizedCurrent = isEmptyContent(currentData) ? "" : currentData;

    if (normalizedValue !== normalizedCurrent) {
      isSettingDataRef.current = true;
      editor.setData(value);
      previousImagesRef.current = extractImageUrls(value);
      // 確保 flag 在下一個事件循環重置
      setTimeout(() => {
        isSettingDataRef.current = false;
      }, 0);
    }
  }, [value]);

  // 建立 CKEditor 配置（穩定引用，Plugin 透過 ref 讀取最新狀態）
  const editorConfig = useMemo(() => {
    const UploadAdapterPlugin =
      createCustomUploadAdapterPlugin(editorContextRef);
    const PaperclipPluginClass = createPaperclipPlugin(editorContextRef);
    const FileInfoPluginClass = createFileInfoPlugin(() =>
      setIsModalOpen(true)
    );

    return {
      licenseKey: "GPL",
      language: "zh",
      translations: [coreTranslations],
      plugins: [
        Essentials,
        Bold,
        Italic,
        Underline,
        Strikethrough,
        List,
        Link,
        Paragraph,
        Image,
        ImageUpload,
        ImageResize,
        FileRepository,
        PasteFromOffice,
        Table,
        TableToolbar,
        Alignment,
        PaperclipPluginClass,
        FileInfoPluginClass,
      ],
      extraPlugins: [UploadAdapterPlugin],
      toolbar: {
        items: [
          "bold",
          "italic",
          "underline",
          "strikethrough",
          "|",
          "numberedList",
          "bulletedList",
          "|",
          "alignment",
          "|",
          "link",
          "insertTable",
          "uploadImage",
          "paperclip",
          "fileinfo",
          "|",
          "removeFormat",
        ],
        shouldNotGroupWhenFull: true,
      },
      placeholder,
      link: {
        addTargetToExternalLinks: false,
        defaultProtocol: "https://",
      },
      image: {
        insert: {
          type: "auto" as const,
        },
      },
      table: {
        contentToolbar: ["tableColumn", "tableRow", "mergeTableCells"],
      },
    };
  }, []); // 空依賴 — Plugin 透過 ref 讀取最新狀態

  const handleEditorReady = useCallback((editor: ClassicEditor) => {
    // React 18 Strict Mode 可能觸發兩次
    if (isInitializedRef.current) return;
    isInitializedRef.current = true;
    editorRef.current = editor;
    previousImagesRef.current = extractImageUrls(editor.getData());
  }, []);

  const handleChange = useCallback(
    (_event: any, editor: ClassicEditor) => {
      // 防止 setData 觸發的 onChange 導致迴圈
      if (isSettingDataRef.current) return;

      const data = editor.getData();
      // 正規化空內容
      const normalizedData = isEmptyContent(data) ? "" : data;
      onChange(normalizedData);

      // 圖片刪除偵測
      if (!editorContextRef.current.isUploading && onFileRemove) {
        const currentImages = extractImageUrls(data);
        const previousImages = previousImagesRef.current;

        if (currentImages.size < previousImages.size) {
          for (const imageUrl of previousImages) {
            if (!currentImages.has(imageUrl)) {
              onFileRemove(imageUrl);
            }
          }
        }

        previousImagesRef.current = currentImages;
      } else {
        previousImagesRef.current = extractImageUrls(data);
      }
    },
    [onChange, onFileRemove]
  );

  // 組件卸載時清理
  useEffect(() => {
    return () => {
      isInitializedRef.current = false;
      editorRef.current = null;
    };
  }, []);

  return (
    <>
      <div className={`ckeditor-wrapper bg-white ${className}`}>
        <CKEditor
          editor={ClassicEditor}
          config={editorConfig}
          data={value}
          onChange={handleChange}
          onReady={handleEditorReady}
          disabled={disabled}
        />
      </div>
      <FileTypeModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </>
  );
};

export default RichTextEditor;
