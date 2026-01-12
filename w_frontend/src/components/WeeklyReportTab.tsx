// frontend/src/components/WeeklyReportTab.tsx

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Save,
  Upload,
  Trash2,
  Plus,
  X,
  Edit,
  Wand2,
  ArrowLeft,
} from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { toast } from "react-hot-toast";
import RichTextEditor from "./RichTextEditor";
import AttachedFilesManager from "./AttachedFilesManager";
import AttachedFilesDisplay from "./AttachedFilesDisplay";
import AiEnhanceButton from "./AiEnhanceButton";
import { AiService } from "./AiServiceSelector";
import { getCurrentWeek, formatWeekRange } from "../utils/weekUtils";
import { WeeklyReportApi, WeeklyReportForm } from "../services/weeklyReportApi";
import { blueButtonStyle } from "../utils/colorUtils";
import { TypographyClasses } from "../styles/typography";
import { getFullFileUrl } from "../utils/urlUtils";
import OverdueARTable from "./OverdueARTable";
import RevenueTable from "./RevenueTable";
import { OverdueARData, RevenueData } from "../services/types";

interface FileForUpload {
  name: string;
  type: string;
  size: number;
  url: string;
  file_path?: string;
  is_selected_for_ai?: boolean;
}

interface WeeklyNote {
  id: number;
  work_item_id: number;
  work_item_name: string;
  subject: string;
  content: string;
  files: FileForUpload[];
  ai_content?: string;
  weekly_no?: string;
  seq?: number;
}

interface WeeklyReportTabProps {
  onUploadComplete?: (year: number, week: number) => void;
}

const WeeklyReportTab: React.FC<WeeklyReportTabProps> = ({
  onUploadComplete,
}) => {
  const { authFetch, user } = useAuth();

  // 當前週次（固定）
  const { year: currentYear, week: currentWeek } = getCurrentWeek();
  const weekRangeText = formatWeekRange(currentYear, currentWeek);

  // 新增筆記區域的 ref
  const addNoteRef = useRef<HTMLDivElement>(null);

  // 工作項目列表
  const [workItems, setWorkItems] = useState<
    Array<{ id: number; name: string }>
  >([]);

  // 週報編號
  const [weeklyNo, setWeeklyNo] = useState<string>("");

  // 本週筆記列表
  const [weeklyNotes, setWeeklyNotes] = useState<WeeklyNote[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // 逾期應收帳款和營收達成率資料
  const [overdueARData, setOverdueARData] = useState<OverdueARData[]>([]);
  const [revenueData, setRevenueData] = useState<RevenueData[]>([]);
  const [isLoadingTables, setIsLoadingTables] = useState(false);

  // 新增筆記狀態
  const [isAddingNew, setIsAddingNew] = useState(false);
  const [newWorkItemId, setNewWorkItemId] = useState<number | undefined>();
  const [newSubject, setNewSubject] = useState<string>("");
  const [newContent, setNewContent] = useState<string>("");
  const [newFiles, setNewFiles] = useState<FileForUpload[]>([]);
  const [isSavingNew, setIsSavingNew] = useState(false);

  // 編輯狀態
  const [editingNoteId, setEditingNoteId] = useState<number | null>(null);
  const [editWorkItemId, setEditWorkItemId] = useState<number | undefined>();
  const [editSubject, setEditSubject] = useState<string>("");
  const [editContent, setEditContent] = useState<string>("");
  const [editFiles, setEditFiles] = useState<FileForUpload[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  // AI 相關狀態
  const [selectedAiService, setSelectedAiService] = useState<AiService>("aoai");
  const [isGeneratingAi, setIsGeneratingAi] = useState(false);
  const [isAiViewActive, setIsAiViewActive] = useState(false);
  const [generatingAiFor, setGeneratingAiFor] = useState<Set<number>>(
    new Set()
  );

  // 提交狀態
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 提交/編輯權限狀態
  const [canSubmit, setCanSubmit] = useState<boolean>(true);
  const [hasReplies, setHasReplies] = useState<boolean>(false); // 是否已被主管審閱
  const [submitTimeInfo, setSubmitTimeInfo] = useState<{
    reason: string;
    next_submit_time: string;
  } | null>(null);

  // 載入工作項目列表
  useEffect(() => {
    const loadWorkItems = async () => {
      if (!authFetch) return;

      try {
        const items = await WeeklyReportApi.getWorkItems(authFetch);
        setWorkItems(items);
        if (items.length > 0) {
          setNewWorkItemId(items[0].id);
        }
      } catch (error) {
        console.error("載入工作項目失敗:", error);
        toast.error("載入工作項目失敗");
      }
    };

    loadWorkItems();
  }, [authFetch]);

  // 載入本週筆記列表
  const loadWeeklyNotes = useCallback(async () => {
    if (!authFetch || !user?.employee?.empno) return;

    setIsLoading(true);
    try {
      const result = await WeeklyReportApi.getWeeklyNotes(
        currentYear,
        currentWeek,
        user.employee.empno,
        authFetch
      );
      setWeeklyNo(result.weekly_no);
      setWeeklyNotes(result.notes);

      // 如果有任何筆記包含 AI 內容，啟用 AI 視圖
      if (result.notes.some((note: WeeklyNote) => note.ai_content)) {
        setIsAiViewActive(true);
      }
    } catch (error) {
      console.error("載入本週筆記失敗:", error);
      toast.error("載入本週筆記失敗");
      setWeeklyNotes([]);
    } finally {
      setIsLoading(false);
    }
  }, [authFetch, user, currentYear, currentWeek]);

  useEffect(() => {
    loadWeeklyNotes();
  }, [loadWeeklyNotes]);

  // 載入逾期應收帳款和營收達成率資料
  const loadTableData = useCallback(async () => {
    if (!authFetch) return;

    setIsLoadingTables(true);
    try {
      // 同時載入兩個 API 的資料
      const [overdueARResult, revenueResult] = await Promise.allSettled([
        WeeklyReportApi.getOverdueAR(currentYear, currentWeek, authFetch),
        WeeklyReportApi.getRevenue(currentYear, currentWeek, authFetch),
      ]);

      // 處理逾期應收帳款資料
      if (overdueARResult.status === "fulfilled") {
        const data = overdueARResult.value?.ResponseData || [];
        setOverdueARData(data);
      } else {
        console.warn("載入逾期應收帳款失敗:", overdueARResult.reason);
        setOverdueARData([]);
      }

      // 處理營收達成率資料
      if (revenueResult.status === "fulfilled") {
        const data = revenueResult.value?.ResponseData || [];
        setRevenueData(data);
      } else {
        console.warn("載入營收達成率失敗:", revenueResult.reason);
        setRevenueData([]);
      }
    } catch (error) {
      console.error("載入表格資料失敗:", error);
      // 不顯示錯誤訊息，因為不是所有人都會有這些資料
    } finally {
      setIsLoadingTables(false);
    }
  }, [authFetch, currentYear, currentWeek]);

  useEffect(() => {
    loadTableData();
  }, [loadTableData]);

  // 載入提交時間限制和審閱狀態
  const checkSubmitStatus = useCallback(async () => {
    if (!authFetch || !weeklyNo) return;

    try {
      const response = await authFetch(
        `/api/weekly/can-submit?weekly_no=${weeklyNo}`
      );
      const data = await response.json();
      setCanSubmit(data.can_submit);
      setHasReplies(data.has_replies);
      setSubmitTimeInfo({
        reason: data.reason,
        next_submit_time: data.next_submit_time,
      });
    } catch (error) {
      console.error("檢查提交狀態失敗:", error);
      // 預設允許提交（防止 API 錯誤影響使用）
      setCanSubmit(true);
      setHasReplies(false);
    }
  }, [authFetch, weeklyNo]);

  useEffect(() => {
    if (weeklyNo) {
      checkSubmitStatus();
    }
  }, [weeklyNo, checkSubmitStatus]);

  // 開始新增筆記
  const startAddNew = () => {
    setIsAddingNew(true);
    setNewWorkItemId(workItems.length > 0 ? workItems[0].id : undefined);
    setNewSubject("");
    setNewContent("");
    setNewFiles([]);

    // 滾動到新增筆記區域
    setTimeout(() => {
      addNoteRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 100);
  };

  // 取消新增
  const cancelAddNew = () => {
    setIsAddingNew(false);
    setNewWorkItemId(workItems.length > 0 ? workItems[0].id : undefined);
    setNewSubject("");
    setNewContent("");
    setNewFiles([]);
  };

  // 保存新筆記
  const saveNewNote = async () => {
    if (!authFetch || !user?.employee?.empno) {
      toast.error("無法獲取用戶信息");
      return;
    }

    if (!newWorkItemId) {
      toast.error("請選擇工作項目");
      return;
    }

    if (!newSubject.trim()) {
      toast.error("請填寫主題");
      return;
    }

    if (!newContent.trim() && newFiles.length === 0) {
      toast.error("請填寫內容或上傳附件");
      return;
    }

    setIsSavingNew(true);
    try {
      const formData: WeeklyReportForm = {
        year: currentYear,
        week: currentWeek,
        work_item_id: newWorkItemId,
        subject: newSubject,
        content: newContent,
        files: newFiles,
      };

      await WeeklyReportApi.saveDraft(formData, authFetch, weeklyNo);
      toast.success("筆記已保存");

      await loadWeeklyNotes();
      // 重新檢查提交狀態
      await checkSubmitStatus();
      cancelAddNew();
    } catch (error: any) {
      console.error(error);
      toast.error(`保存失敗: ${error.message}`);
    } finally {
      setIsSavingNew(false);
    }
  };

  // 開始編輯筆記
  const startEdit = (note: WeeklyNote) => {
    setEditingNoteId(note.id);
    setEditWorkItemId(note.work_item_id);
    setEditSubject(note.subject);
    setEditContent(note.content);
    setEditFiles([...note.files]);
  };

  // 取消編輯
  const cancelEdit = () => {
    setEditingNoteId(null);
    setEditWorkItemId(undefined);
    setEditSubject("");
    setEditContent("");
    setEditFiles([]);
  };

  // 保存編輯
  const saveEdit = async () => {
    if (!authFetch || !user?.employee?.empno) {
      toast.error("無法獲取用戶信息");
      return;
    }

    if (!editWorkItemId) {
      toast.error("請選擇工作項目");
      return;
    }

    if (!editSubject.trim()) {
      toast.error("請填寫主題");
      return;
    }

    if (!editContent.trim() && editFiles.length === 0) {
      toast.error("請填寫內容或上傳附件");
      return;
    }

    setIsSaving(true);
    try {
      const formData: WeeklyReportForm = {
        year: currentYear,
        week: currentWeek,
        work_item_id: editWorkItemId,
        subject: editSubject,
        content: editContent,
        files: editFiles,
      };

      if (editingNoteId) {
        await WeeklyReportApi.updateNote(
          weeklyNo,
          editingNoteId,
          formData,
          authFetch
        );
      }

      toast.success("筆記已更新");
      await loadWeeklyNotes();
      // 重新檢查提交狀態
      await checkSubmitStatus();
      cancelEdit();
    } catch (error: any) {
      console.error(error);
      toast.error(`更新失敗: ${error.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  // 刪除筆記
  const deleteNote = async () => {
    if (!editingNoteId || !authFetch) return;

    if (!confirm("確定要刪除這筆記錄嗎？")) return;

    try {
      await WeeklyReportApi.deleteNote(weeklyNo, editingNoteId, authFetch);

      toast.success("筆記已刪除");
      await loadWeeklyNotes();
      // 重新檢查提交狀態
      await checkSubmitStatus();
      cancelEdit();
    } catch (error: any) {
      console.error(error);
      toast.error(`刪除失敗: ${error.message}`);
    }
  };

  // 檔案處理函數
  const handleNewEditorFileUpload = useCallback((file: FileForUpload) => {
    setNewFiles((prev) => [...prev, file]);
  }, []);

  const handleRemoveNewFile = useCallback((urlOrPath: string) => {
    try {
      // ✅ 將 HTML 編碼的 &amp; 轉回 &
      const decodedUrl = urlOrPath.replace(/&amp;/g, "&");

      // ✅ 直接用完整 URL 比對
      const targetUrl = decodedUrl.startsWith("http")
        ? decodedUrl
        : getFullFileUrl(decodedUrl);

      // 1. 從 files 列表中移除該檔案
      setNewFiles((prev) => {
        return prev.filter((file) => {
          const fileFullUrl = file.url.startsWith("http")
            ? file.url
            : getFullFileUrl(file.url);
          return file.url !== targetUrl && fileFullUrl !== targetUrl;
        });
      });

      // 2. 從 RichTextEditor 的內容中移除圖片
      setNewContent((prevContent) => {
        let newContent = prevContent;
        const htmlEncodedUrl = targetUrl.replace(/&/g, "&amp;");

        // 嘗試原始 URL
        const escapedUrl = targetUrl.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const regex1 = new RegExp(`<img[^>]*src="${escapedUrl}"[^>]*>`, "g");
        newContent = newContent.replace(regex1, "");

        // 嘗試 HTML 編碼的 URL
        const escapedHtmlUrl = htmlEncodedUrl.replace(
          /[.*+?^${}()|[\]\\]/g,
          "\\$&"
        );
        const regex2 = new RegExp(
          `<img[^>]*src="${escapedHtmlUrl}"[^>]*>`,
          "g"
        );
        newContent = newContent.replace(regex2, "");

        return newContent;
      });

      toast.success("檔案已移除");
    } catch (error) {
      console.error("移除檔案時發生錯誤:", error);
      toast.error("移除檔案失敗");
    }
  }, []);

  const handleNewAiSelectionChange = (fileUrl: string, isSelected: boolean) => {
    setNewFiles((prev) =>
      prev.map((f) =>
        f.url === fileUrl ? { ...f, is_selected_for_ai: isSelected } : f
      )
    );
  };

  const handleEditEditorFileUpload = useCallback((file: FileForUpload) => {
    setEditFiles((prev) => [...prev, file]);
  }, []);

  const handleRemoveEditFile = useCallback((urlOrPath: string) => {
    try {
      // ✅ 將 HTML 編碼的 &amp; 轉回 &
      const decodedUrl = urlOrPath.replace(/&amp;/g, "&");

      // ✅ 直接用完整 URL 比對
      const targetUrl = decodedUrl.startsWith("http")
        ? decodedUrl
        : getFullFileUrl(decodedUrl);

      // 1. 從 files 列表中移除該檔案
      setEditFiles((prev) => {
        return prev.filter((file) => {
          const fileFullUrl = file.url.startsWith("http")
            ? file.url
            : getFullFileUrl(file.url);
          return file.url !== targetUrl && fileFullUrl !== targetUrl;
        });
      });

      // 2. 從 RichTextEditor 的內容中移除圖片
      setEditContent((prevContent) => {
        let newContent = prevContent;
        const htmlEncodedUrl = targetUrl.replace(/&/g, "&amp;");

        // 嘗試原始 URL
        const escapedUrl = targetUrl.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const regex1 = new RegExp(`<img[^>]*src="${escapedUrl}"[^>]*>`, "g");
        newContent = newContent.replace(regex1, "");

        // 嘗試 HTML 編碼的 URL
        const escapedHtmlUrl = htmlEncodedUrl.replace(
          /[.*+?^${}()|[\]\\]/g,
          "\\$&"
        );
        const regex2 = new RegExp(
          `<img[^>]*src="${escapedHtmlUrl}"[^>]*>`,
          "g"
        );
        newContent = newContent.replace(regex2, "");

        return newContent;
      });

      toast.success("檔案已移除");
    } catch (error) {
      console.error("移除檔案時發生錯誤:", error);
      toast.error("移除檔案失敗");
    }
  }, []);

  const handleEditAiSelectionChange = (
    fileUrl: string,
    isSelected: boolean
  ) => {
    setEditFiles((prev) =>
      prev.map((f) =>
        f.url === fileUrl ? { ...f, is_selected_for_ai: isSelected } : f
      )
    );
  };

  // 套用 AI 建議到編輯內容
  const handleApplyAiSuggestion = (aiContent: string) => {
    console.log("=== 套用 AI 建議 ===");
    console.log("當前 editFiles:", editFiles);
    console.log("當前 editContent 長度:", editContent.length);

    // 提取當前編輯內容中的所有圖片標籤
    const imgRegex = /<img[^>]*>/gi;
    const images = editContent.match(imgRegex) || [];
    console.log("找到的圖片數量:", images.length);

    // 將純文字的換行符轉換為 HTML 的 <br> 標籤
    const htmlContent = aiContent.replace(/\n/g, "<br>");

    // 如果沒有圖片，直接套用轉換後的 AI 建議
    if (images.length === 0) {
      setEditContent(htmlContent);
      toast.success("AI 建議已套用！");
      console.log("套用後 editFiles 應該不變");
      return;
    }

    // 將圖片包裹在段落標籤中，保持編輯器格式一致性
    const imageBlocks = images.map((img) => `<p>${img}</p>`).join("");

    // 組合新內容：AI 建議文字 + 保留的圖片
    const newContent = `${htmlContent}${imageBlocks}`;

    setEditContent(newContent);
    toast.success(`AI 建議已套用，並保留了 ${images.length} 張圖片！`);
    console.log("套用完成，editFiles 應該保持不變");
  };

  // 潤飾單筆筆記
  const handleEnhanceOne = async (note: WeeklyNote) => {
    if (!authFetch || !note.weekly_no) return;

    const noteId = note.id;
    setGeneratingAiFor((prev) => new Set([...prev, noteId]));

    try {
      const result = await WeeklyReportApi.enhanceOne(
        note.weekly_no,
        note.seq!,
        selectedAiService,
        authFetch
      );

      // 更新筆記的 AI 內容
      setWeeklyNotes((prev) =>
        prev.map((n) =>
          n.id === noteId ? { ...n, ai_content: result.ai_content } : n
        )
      );

      if (!isAiViewActive) setIsAiViewActive(true);
      toast.success(`筆記「${note.subject}」已完成 AI 潤飾！`);
    } catch (error: any) {
      console.error(error);
      toast.error(error.message || "AI 潤飾此筆記時發生錯誤");
    } finally {
      setGeneratingAiFor((prev) => {
        const newSet = new Set(prev);
        newSet.delete(noteId);
        return newSet;
      });
    }
  };

  // 潤飾全部
  const handleEnhanceAll = async () => {
    if (!authFetch) return;

    if (weeklyNotes.length === 0) {
      toast.error("沒有可以潤飾的筆記");
      return;
    }

    setIsGeneratingAi(true);
    setIsAiViewActive(true);

    try {
      // 依序潤飾每個筆記
      const enhancePromises = weeklyNotes.map(async (note) => {
        if (!note.weekly_no || !note.seq) {
          console.warn(`跳過筆記 ${note.subject}: 缺少 weekly_no 或 seq`);
          return;
        }

        const noteId = note.id;

        try {
          setGeneratingAiFor((prev) => new Set([...prev, noteId]));

          const result = await WeeklyReportApi.enhanceOne(
            note.weekly_no,
            note.seq,
            selectedAiService,
            authFetch
          );

          // 更新該筆記的 AI 內容
          setWeeklyNotes((prev) =>
            prev.map((n) =>
              n.id === noteId ? { ...n, ai_content: result.ai_content } : n
            )
          );
        } catch (error) {
          console.error(`筆記 ${note.subject} AI 潤飾出錯:`, error);
        } finally {
          setGeneratingAiFor((prev) => {
            const newSet = new Set(prev);
            newSet.delete(noteId);
            return newSet;
          });
        }
      });

      // 等待所有筆記完成
      await Promise.all(enhancePromises);

      toast.success("所有筆記已完成 AI 潤飾！");
    } catch (error: any) {
      console.error(error);
      toast.error(error.message || "批量 AI 潤飾時發生錯誤");
    } finally {
      setIsGeneratingAi(false);
      setGeneratingAiFor(new Set());
    }
  };

  // 提交週報
  const handleSubmitWeekly = async () => {
    if (!authFetch || !user?.employee?.empno) {
      toast.error("無法獲取用戶信息");
      return;
    }

    if (weeklyNotes.length === 0) {
      toast.error("請至少新增一筆記錄後再提交");
      return;
    }

    if (!weeklyNo) {
      toast.error("無法獲取週報編號");
      return;
    }

    if (!confirm("確定要提交本週週報嗎？提交後將無法修改。")) return;

    setIsSubmitting(true);
    try {
      const result = await WeeklyReportApi.submitWeeklyReport(
        weeklyNo,
        currentYear,
        currentWeek,
        authFetch
      );

      if (result.ResponseNa === "週報儲存成功") {
        toast.success("週報已提交成功！");

        // 重新載入筆記列表以更新狀態
        await loadWeeklyNotes();
        // 重新檢查提交狀態
        await checkSubmitStatus();

        if (onUploadComplete) {
          onUploadComplete(currentYear, currentWeek);
        }
      } else {
        toast.error(`提交失敗: ${result.ResponseNa || "未知錯誤"}`);
      }
    } catch (error: any) {
      console.error(error);
      toast.error(`提交失敗: ${error.message || "未知錯誤"}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return <div className="p-6 text-center">載入中...</div>;
  }

  return (
    <div className="p-2 sm:p-4 md:p-6">
      {/* 頂部區域 */}
      <div className="flex flex-col gap-3 sm:gap-4 lg:flex-row lg:items-center lg:justify-between mb-4 sm:mb-6">
        {/* 左側：週次顯示 */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 flex-1 min-w-0">
          <div className="flex-1 min-w-0">
            <h2 className="text-base sm:text-lg md:text-xl lg:text-2xl font-bold text-gray-900">
              週報編輯
            </h2>
            <div className="flex items-center mt-1 text-xs sm:text-sm text-gray-600 gap-2">
              <span>{weekRangeText}</span>
              <span className="text-blue-600">第 {currentWeek} 周</span>
            </div>
          </div>
        </div>

        {/* 右側：三個按鈕 */}
        <div className="flex flex-row flex-wrap items-center gap-2 sm:gap-3">
          {/* 新增筆記 */}
          <button
            onClick={startAddNew}
            disabled={hasReplies || editingNoteId !== null || isAddingNew}
            className={`inline-flex items-center justify-center px-3 sm:px-4 h-10 text-xs sm:text-sm rounded-lg ${blueButtonStyle} disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed flex-shrink-0`}
          >
            <Plus className="w-4 h-4 mr-2" />
            <span className="hidden sm:inline">新增筆記</span>
            <span className="sm:hidden">新增</span>
          </button>

          {/* 潤飾全部 */}
          <AiEnhanceButton
            selectedService={selectedAiService}
            onServiceChange={setSelectedAiService}
            onEnhance={handleEnhanceAll}
            disabled={
              hasReplies ||
              isGeneratingAi ||
              weeklyNotes.length === 0 ||
              editingNoteId !== null ||
              isAddingNew
            }
            isLoading={isGeneratingAi}
          />

          {/* 提交週報 */}
          <button
            onClick={handleSubmitWeekly}
            disabled={
              !canSubmit ||
              isSubmitting ||
              editingNoteId !== null ||
              isAddingNew ||
              weeklyNotes.length === 0
            }
            className={`inline-flex items-center justify-center px-3 sm:px-4 h-10 text-xs sm:text-sm rounded-lg ${blueButtonStyle} disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed flex-shrink-0`}
          >
            <Upload className="w-4 h-4 mr-2" />
            <span className="hidden sm:inline">
              {isSubmitting ? "提交中..." : "提交週報"}
            </span>
            <span className="sm:hidden">
              {isSubmitting ? "提交中..." : "提交"}
            </span>
          </button>
        </div>
      </div>

      {/* 逾期應收帳款和營收達成率表格 */}
      <OverdueARTable data={overdueARData} isLoading={isLoadingTables} />
      <RevenueTable data={revenueData} isLoading={isLoadingTables} />

      {/* 筆記列表區域 */}
      <div className="space-y-4 sm:space-y-6">
        {/* 新增筆記區域 */}
        {isAddingNew && (
          <div
            ref={addNoteRef}
            className="bg-white rounded-lg shadow-sm border-2 border-blue-500 p-4 sm:p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-gray-900">
                新增筆記
              </h3>
              <button
                onClick={cancelAddNew}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              {/* 工作項目選擇 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  工作項目 <span className="text-red-500">*</span>
                </label>
                <select
                  value={newWorkItemId || ""}
                  onChange={(e) =>
                    setNewWorkItemId(
                      e.target.value ? Number(e.target.value) : undefined
                    )
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">請選擇工作項目</option>
                  {workItems.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* 主題輸入 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  主題 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={newSubject}
                  onChange={(e) => setNewSubject(e.target.value)}
                  placeholder="請輸入主題"
                  maxLength={100}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <div className="text-xs text-gray-500 mt-1">
                  {newSubject.length}/100
                </div>
              </div>

              {/* 內容編輯器 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  內容
                </label>
                <RichTextEditor
                  value={newContent}
                  onChange={setNewContent}
                  onFileUpload={handleNewEditorFileUpload}
                  onFileRemove={handleRemoveNewFile}
                  files={newFiles}
                  placeholder="記錄您的想法... (可直接貼上圖片或者附上檔案)"
                  docDate={`${currentYear}${String(currentWeek).padStart(
                    2,
                    "0"
                  )}01`}
                />
              </div>

              {/* 附件管理 */}
              <AttachedFilesManager
                files={newFiles}
                onRemoveFile={handleRemoveNewFile}
                onAiSelectionChange={handleNewAiSelectionChange}
                isUploading={false}
                showUploadButton={false}
              />

              {/* 操作按鈕 */}
              <div className="flex space-x-3">
                <button
                  onClick={saveNewNote}
                  disabled={isSavingNew}
                  className={`flex-1 inline-flex items-center justify-center px-4 py-2 text-sm rounded-lg ${blueButtonStyle} disabled:bg-gray-200`}
                >
                  <Save className="w-4 h-4 mr-2" />
                  {isSavingNew ? "保存中..." : "保存"}
                </button>
                <button
                  onClick={cancelAddNew}
                  className="px-4 py-2 bg-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-300"
                >
                  取消
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 已保存的筆記列表 */}
        {weeklyNotes.map((note) => (
          <div
            key={note.id}
            className={`relative grid grid-cols-1 ${
              isAiViewActive ? "lg:grid-cols-2" : ""
            } gap-x-3 sm:gap-x-4 lg:gap-x-6 gap-y-4 sm:gap-y-6 items-stretch bg-gray-50 p-2 sm:p-3 md:p-4 rounded-xl border overflow-hidden`}
          >
            {/* --- Card 1: 原始內容 --- */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 sm:p-6 w-full flex flex-col h-full relative min-w-0">
              {editingNoteId === note.id ? (
                // 編輯模式
                <div className="space-y-4">
                  {/* 工作項目選擇 */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      工作項目 <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={editWorkItemId || ""}
                      onChange={(e) =>
                        setEditWorkItemId(
                          e.target.value ? Number(e.target.value) : undefined
                        )
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">請選擇工作項目</option>
                      {workItems.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* 主題輸入 */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      主題 <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={editSubject}
                      onChange={(e) => setEditSubject(e.target.value)}
                      placeholder="請輸入主題"
                      maxLength={100}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <div className="text-xs text-gray-500 mt-1">
                      {editSubject.length}/100
                    </div>
                  </div>

                  {/* 內容編輯器 */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      內容
                    </label>
                    <RichTextEditor
                      value={editContent}
                      onChange={setEditContent}
                      onFileUpload={handleEditEditorFileUpload}
                      onFileRemove={handleRemoveEditFile}
                      files={editFiles}
                      placeholder="編輯記錄內容... (可直接貼上圖片)"
                      docDate={`${currentYear}${String(currentWeek).padStart(
                        2,
                        "0"
                      )}01`}
                    />
                  </div>

                  {/* 附件管理 */}
                  <AttachedFilesManager
                    files={editFiles}
                    onRemoveFile={handleRemoveEditFile}
                    onAiSelectionChange={handleEditAiSelectionChange}
                    isUploading={false}
                    showUploadButton={false}
                  />

                  {/* 操作按鈕 */}
                  <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
                    <button
                      onClick={saveEdit}
                      disabled={isSaving}
                      className={`inline-flex items-center justify-center px-4 py-2 text-sm rounded-lg ${blueButtonStyle} disabled:bg-gray-200 order-1`}
                    >
                      <Save className="w-4 h-4 mr-2" />
                      {isSaving ? "儲存中..." : "儲存"}
                    </button>
                    <button
                      onClick={deleteNote}
                      className="px-4 py-2 bg-red-500 text-white text-sm font-medium rounded-lg hover:bg-red-600 order-2 inline-flex items-center justify-center"
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      刪除
                    </button>
                    {/* 套用 AI 建議按鈕 - 只在編輯模式且有 AI 內容時顯示（小螢幕） */}
                    {isAiViewActive && note.ai_content && (
                      <button
                        onClick={() =>
                          handleApplyAiSuggestion(note.ai_content!)
                        }
                        className="lg:hidden inline-flex items-center justify-center px-4 py-2 text-sm rounded-lg bg-gradient-to-r from-purple-500 to-blue-500 text-white hover:from-purple-600 hover:to-blue-600 transition-all duration-200 shadow-md hover:shadow-lg order-3"
                      >
                        <Wand2 className="w-4 h-4 mr-2" />
                        套用 AI 建議
                      </button>
                    )}
                    <button
                      onClick={cancelEdit}
                      className="px-4 py-2 bg-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-300 order-4"
                    >
                      取消
                    </button>
                  </div>
                </div>
              ) : (
                // 顯示模式
                <div>
                  {/* 標題區域 */}
                  <div className="mb-4">
                    <div className="flex items-center justify-between gap-4 mb-2">
                      <div className="flex-1 min-w-0">
                        <div className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-md bg-purple-100 text-purple-800">
                          {note.work_item_name}
                        </div>
                      </div>
                      {/* 右側按鈕組 */}
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <button
                          onClick={() => handleEnhanceOne(note)}
                          disabled={
                            hasReplies ||
                            generatingAiFor.size > 0 ||
                            isGeneratingAi ||
                            editingNoteId !== null ||
                            isAddingNew
                          }
                          className="inline-flex items-center justify-center px-2 py-1 text-xs sm:text-sm font-medium rounded-md bg-gradient-to-r from-purple-100 to-blue-100 text-purple-700 hover:from-purple-200 hover:to-blue-200 transition-all duration-200 border border-purple-200 disabled:from-gray-100 disabled:to-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed disabled:border-gray-300"
                        >
                          {generatingAiFor.has(note.id) ? (
                            <>
                              <div className="w-3 h-3 border-2 border-transparent border-t-purple-500 rounded-full animate-spin mr-1.5"></div>
                              <span className="whitespace-nowrap">潤飾</span>
                            </>
                          ) : (
                            <>
                              <Wand2 className="w-3 h-3 mr-1.5" />
                              <span className="whitespace-nowrap">潤飾</span>
                            </>
                          )}
                        </button>
                        <button
                          onClick={() => startEdit(note)}
                          disabled={
                            hasReplies ||
                            isAddingNew ||
                            generatingAiFor.size > 0 ||
                            isGeneratingAi
                          }
                          className="inline-flex items-center justify-center px-2 py-1 text-xs sm:text-sm font-medium rounded-md bg-green-100 text-green-700 hover:bg-green-200 border border-green-200 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed"
                        >
                          <Edit className="w-3 h-3 mr-1.5" />
                          <span className="whitespace-nowrap">編輯</span>
                        </button>
                      </div>
                    </div>
                    <div className="inline-flex items-center px-1.5 sm:px-2 py-0.5 sm:py-1 text-xs font-medium rounded-md bg-green-100 text-green-800">
                      <span className="truncate max-w-[200px] sm:max-w-none">
                        {note.subject}
                      </span>
                    </div>
                  </div>

                  {/* 內容 */}
                  <div
                    className={TypographyClasses.richTextDisplay}
                    dangerouslySetInnerHTML={{ __html: note.content }}
                  />

                  {/* 附件顯示 */}
                  {note.files && note.files.length > 0 && (
                    <div className="mt-4">
                      <AttachedFilesDisplay
                        files={note.files}
                        content={note.content}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* --- Card 2: AI 參考資料 --- */}
            {isAiViewActive && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 sm:p-6 w-full h-full min-w-0">
                <div className="flex items-center space-x-3 mb-4">
                  <div className="inline-flex items-center px-3 py-1 text-sm font-medium rounded-lg bg-gradient-to-r from-purple-100 to-blue-100 text-purple-700 border border-purple-200">
                    <Wand2 className="w-4 h-4 mr-1.5" /> AI 參考資料
                  </div>
                </div>
                {generatingAiFor.has(note.id) ? (
                  <p className="text-base text-gray-500 italic">
                    AI 正在為此筆記生成潤飾內容...
                  </p>
                ) : note.ai_content ? (
                  <div
                    className={`${TypographyClasses.richTextDisplay} whitespace-pre-wrap`}
                  >
                    <div
                      dangerouslySetInnerHTML={{
                        __html: note.ai_content.replace(/\n/g, "<br />"),
                      }}
                    />
                  </div>
                ) : (
                  <p className="text-base text-gray-400 italic">
                    此筆記無 AI 潤飾內容。點擊魔法棒按鈕開始生成。
                  </p>
                )}
              </div>
            )}

            {/* --- Apply AI Suggestion Button (中間浮動按鈕 - 只在 lg 以上且編輯模式顯示) --- */}
            {editingNoteId === note.id && isAiViewActive && note.ai_content && (
              <div className="hidden lg:block absolute z-10 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                <button
                  onClick={() => handleApplyAiSuggestion(note.ai_content!)}
                  className="flex items-center justify-center w-12 h-12 bg-white rounded-full shadow-lg hover:bg-gray-100 border border-gray-300 text-gray-600 hover:text-gray-800 hover:border-gray-400 transition-all duration-200 ease-in-out transform hover:scale-110"
                  title="套用 AI 建議"
                >
                  <ArrowLeft className="w-6 h-6" />
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default WeeklyReportTab;
