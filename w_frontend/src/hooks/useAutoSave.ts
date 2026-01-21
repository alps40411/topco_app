import { useEffect, useRef, useCallback } from "react";
import { toast } from "react-hot-toast";

interface AutoSaveOptions {
  /** 自動儲存間隔（毫秒），預設 60000 (1 分鐘) */
  interval?: number;
  /** 儲存函數 */
  onSave: () => Promise<void>;
  /** 是否啟用自動儲存 */
  enabled?: boolean;
  /** 檢查是否有內容可儲存 */
  hasContent: () => boolean;
}

/**
 * 自動儲存 Hook
 * 每隔指定時間自動呼叫儲存函數
 */
export function useAutoSave({
  interval = 60000,
  onSave,
  enabled = true,
  hasContent,
}: AutoSaveOptions) {
  const isSavingRef = useRef<boolean>(false);
  const lastContentRef = useRef<string>("");

  const save = useCallback(async () => {
    // 防止重複儲存
    if (isSavingRef.current) return;

    // 檢查是否有內容
    if (!hasContent()) return;

    try {
      isSavingRef.current = true;
      await onSave();
      toast.success("已自動儲存", { duration: 2000 });
    } catch (error) {
      console.error("自動儲存失敗:", error);
      // 儲存失敗不顯示錯誤提示，避免干擾用戶
    } finally {
      isSavingRef.current = false;
    }
  }, [onSave, hasContent]);

  useEffect(() => {
    if (!enabled) return;

    const timer = setInterval(() => {
      save();
    }, interval);

    return () => clearInterval(timer);
  }, [enabled, interval, save]);

  // 回傳手動觸發儲存的函數
  return { saveNow: save, isSaving: isSavingRef.current };
}
