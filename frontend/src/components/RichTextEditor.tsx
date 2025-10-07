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

  // 追蹤 handleImageUpload 的創建
  console.log('[RichTextEditor] handleImageUpload useCallback 被評估');

  // 處理圖片上傳並插入編輯器
  const handleImageUpload = useCallback(() => {
    console.log('[RichTextEditor] ========== handleImageUpload 被呼叫 ==========');
    console.log('[RichTextEditor] 當前時間戳:', new Date().toISOString());
    console.time('[RichTextEditor] 總上傳時間');

    const t0 = performance.now();
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    console.log(`[RichTextEditor] 創建 input 元素: ${(performance.now() - t0).toFixed(2)}ms`);

    const t1 = performance.now();

    // 使用 addEventListener 而不是 onchange，避免同步阻塞
    console.log('[RichTextEditor] 註冊 change 事件監聽器...');

    // ⚠️ 關鍵測試：記錄用戶打開對話框的時間
    let dialogOpenTime = 0;

    input.addEventListener('change', (event) => {
      const dialogCloseTime = performance.now();
      const userSelectionTime = dialogCloseTime - dialogOpenTime;
      console.log(`[RichTextEditor] ⏱️ 對話框打開到關閉的時間: ${userSelectionTime.toFixed(2)}ms`);
      console.log(`[RichTextEditor] 📁 如果這個時間 > 10秒，問題是 Windows 檔案對話框`);

      const t2 = performance.now();
      console.log(`[RichTextEditor] ===== change 事件觸發 =====`);
      console.log(`[RichTextEditor] 距離 click: ${(t2 - t1).toFixed(2)}ms`);
      console.log(`[RichTextEditor] Event 物件:`, event);
      console.log(`[RichTextEditor] Event.isTrusted:`, event.isTrusted);
      console.log(`[RichTextEditor] Event.timeStamp:`, event.timeStamp);

      const t2_1 = performance.now();
      const file = input.files?.[0];
      console.log(`[RichTextEditor] 讀取 input.files 時間: ${(performance.now() - t2_1).toFixed(2)}ms`);

      if (!file) {
        console.log('[RichTextEditor] 沒有選擇檔案，結束');
        return;
      }

      console.log(`[RichTextEditor] 檔案資訊:`, {
        name: file.name,
        size: `${(file.size / 1024).toFixed(2)}KB`,
        type: file.type,
        lastModified: new Date(file.lastModified).toISOString()
      });

      const t2_2 = performance.now();
      const quill = quillRef.current?.getEditor();
      console.log(`[RichTextEditor] 取得 Quill 實例時間: ${(performance.now() - t2_2).toFixed(2)}ms`);

      if (!quill || !authFetch) {
        console.log('[RichTextEditor] Quill 或 authFetch 不存在，結束');
        return;
      }

      const t3 = performance.now();
      console.log(`[RichTextEditor] 準備進入 queueMicrotask`);
      console.log(`[RichTextEditor] 從 change 觸發到這裡總時間: ${(t3 - t2).toFixed(2)}ms`);

      // 立即返回，不阻塞 UI
      // 使用 queueMicrotask 將上傳邏輯推遲，比 setTimeout 更快
      queueMicrotask(async () => {
        const t4 = performance.now();
        console.log(`[RichTextEditor] queueMicrotask 執行開始 (距離 queueMicrotask 呼叫: ${(t4 - t3).toFixed(2)}ms)`);

        const formData = new FormData();
        formData.append("file", file);
        console.log(`[RichTextEditor] FormData 建立完成: ${(performance.now() - t4).toFixed(2)}ms`);

        const range = quill.getSelection(true) || { index: quill.getLength() - 1, length: 0 };
        const placeholderIndex = range.index;

        try {
          isUploadingRef.current = true;
          toast.loading('上傳中...', { id: 'image-upload' });
          console.log('[RichTextEditor] 開始上傳到伺服器...');

          const t5 = performance.now();
          const response = await authFetch("/api/records/upload", {
            method: "POST",
            body: formData,
          });
          const t6 = performance.now();
          console.log(`[RichTextEditor] 伺服器回應時間: ${(t6 - t5).toFixed(2)}ms, 狀態: ${response.status}`);

          if (!response.ok) throw new Error(`圖片 ${file.name} 上傳失敗`);

          const t7 = performance.now();
          const uploadedFile = await response.json();
          const t8 = performance.now();
          console.log(`[RichTextEditor] JSON 解析時間: ${(t8 - t7).toFixed(2)}ms`);
          console.log('[RichTextEditor] 上傳結果:', uploadedFile);

          // 回調通知父元件
          const t9 = performance.now();
          if (onFileUpload) {
            onFileUpload({
              name: uploadedFile.name,
              type: uploadedFile.type,
              size: uploadedFile.size,
              url: uploadedFile.url,
              is_selected_for_ai: false,
            });
          }
          const t10 = performance.now();
          console.log(`[RichTextEditor] onFileUpload 回調時間: ${(t10 - t9).toFixed(2)}ms`);

          // 插入圖片到編輯器
          const t11 = performance.now();
          const imageUrl = getFullFileUrl(uploadedFile.url);
          quill.insertEmbed(placeholderIndex, "image", imageUrl);
          quill.setSelection(placeholderIndex + 1, 0);
          const t12 = performance.now();
          console.log(`[RichTextEditor] 插入圖片到編輯器時間: ${(t12 - t11).toFixed(2)}ms`);

          // 更新 previousContentRef
          setTimeout(() => {
            previousContentRef.current = quill.root.innerHTML;
            console.log('[RichTextEditor] previousContentRef 已更新');
          }, 50);

          toast.success('圖片上傳成功', { id: 'image-upload' });
          console.timeEnd('[RichTextEditor] 總上傳時間');
          console.log('[RichTextEditor] ========== 圖片上傳流程結束 ==========');
        } catch (error: any) {
          console.error('[RichTextEditor] 上傳錯誤:', error);
          toast.error(error.message, { id: 'image-upload' });
        } finally {
          setTimeout(() => {
            isUploadingRef.current = false;
            console.log('[RichTextEditor] isUploadingRef 已重置為 false');
          }, 100);
        }
      });

      const t13 = performance.now();
      console.log(`[RichTextEditor] change 事件處理完畢 (總時間: ${(t13 - t2).toFixed(2)}ms)`);
    }, { once: true }); // 只監聽一次

    const t1_1 = performance.now();
    console.log('[RichTextEditor] 準備觸發 input.click()...');

    // 使用 Performance API 標記
    performance.mark('input-click-start');

    dialogOpenTime = performance.now(); // 記錄對話框打開時間
    input.click();

    performance.mark('input-click-end');
    performance.measure('input-click-duration', 'input-click-start', 'input-click-end');

    const clickMeasure = performance.getEntriesByName('input-click-duration')[0];
    console.log(`[RichTextEditor] input.click() 執行時間: ${clickMeasure.duration.toFixed(2)}ms`);
    console.log(`[RichTextEditor] 檔案選擇對話框已觸發: ${(performance.now() - t1_1).toFixed(2)}ms`);
  }, [authFetch, onFileUpload]);

  // 處理一般檔案上傳（不插入編輯器）
  const handlePaperclipUpload = useCallback(() => {
    const input = document.createElement("input");
    input.setAttribute("type", "file");
    input.setAttribute("multiple", "true");

    input.addEventListener('change', () => {
      const files = input.files;
      if (!files || files.length === 0 || !authFetch) return;

      // 立即返回，不阻塞 UI
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
        } finally {
          setTimeout(() => {
            isUploadingRef.current = false;
          }, 100);
        }
      });
    }, { once: true });

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
              // 從完整 URL 中提取相對路徑
              let fileUrl = imageUrl;
              if (imageUrl.startsWith("http")) {
                try {
                  const url = new URL(imageUrl);
                  fileUrl = url.pathname;
                } catch (e) {
                  console.error('Invalid image URL:', imageUrl);
                }
              }

              console.log('[RichTextEditor] 偵測到圖片被刪除，呼叫 onFileRemove:', fileUrl);
              // 通知父元件並刪除檔案
              onFileRemove(fileUrl);
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
  console.log('[RichTextEditor] modules useMemo 被評估');
  const modules = useMemo(
    () => {
      console.log('[RichTextEditor] modules useMemo 計算中...');
      const config = {
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
      };
      console.log('[RichTextEditor] modules useMemo 計算完成');
      return config;
    },
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
