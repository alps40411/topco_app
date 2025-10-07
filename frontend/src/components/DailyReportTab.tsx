// frontend/src/components/DailyReportTab.tsx

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Upload,
  Edit,
  Save,
  Wand2,
  Plus,
  X,
  ArrowUp,
  ArrowLeft,
} from "lucide-react";
import type {
  ConsolidatedReport,
  FileAttachment,
  FileForUpload,
  Project,
  WorkRecordCreate,
} from "../App";
import { getProjectColors, blueButtonStyle } from "../utils/colorUtils";
import { useAuth } from "../hooks/useAuth";
import AttachedFilesManager from "./AttachedFilesManager";
import AttachedFilesDisplay from "./AttachedFilesDisplay";
import ExecutionTimeSelector from "./ExecutionTimeSelector";
import CascadingWorkSelector from "./CascadingWorkSelector";
import { getFullFileUrl } from "../utils/urlUtils";
import ServiceSelector from "./ServiceSelector";
import DateSelector from "./DateSelector";
import RichTextEditor from "./RichTextEditor";
import { toast } from "react-hot-toast";
import { TypographyClasses } from "../styles/typography";
import { formatMinutesToHours } from "../utils/timeUtils";

interface DailyRecordCreate
  extends Omit<WorkRecordCreate, "service_company_id" | "service_target_id"> {
  service_cocode?: string;
  service_empno?: string;
}

interface WritingStatus {
  allowed: boolean;
  message: string;
  current_time: string;
  has_other_writable_dates?: boolean;
}

interface DailyReportTabProps {
  selectedDate: string | null;
  onDateChange: (date: string) => void;
  onUploadComplete?: (uploadedDate: string) => void;
  onSwitchToDaily?: () => void;
}

const DailyReportTab: React.FC<DailyReportTabProps> = ({
  selectedDate,
  onDateChange,
  onUploadComplete,
  onSwitchToDaily,
}) => {
  const [reports, setReports] = useState<ConsolidatedReport[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [writingStatus, setWritingStatus] = useState<WritingStatus | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingSopno, setEditingSopno] = useState<string | null>(null);
  const [editContent, setEditContent] = useState<string>("");
  const [editFiles, setEditFiles] = useState<FileForUpload[]>([]);
  const { authFetch, user } = useAuth();

  const [isAiViewActive, setIsAiViewActive] = useState(false);
  const [isGeneratingAllAi, setIsGeneratingAllAi] = useState(false);
  const [generatingAiFor, setGeneratingAiFor] = useState<Set<string>>(
    new Set()
  );

  // --- Modal and New Record State ---
  const [isAddNoteModalOpen, setIsAddNoteModalOpen] = useState(false);
  const [newRecord, setNewRecord] = useState<Partial<DailyRecordCreate>>({
    content: "",
    project_id: undefined,
    execution_work_id: undefined,
    work_item_id: undefined,
    service_cocode: undefined,
    service_empno: undefined,
    files: [],
    execution_time_minutes: 0,
  });
  const [isSavingNewRecord, setIsSavingNewRecord] = useState(false);
  const [isUploadingNewFile, setIsUploadingNewFile] = useState(false);
  // 追蹤新增筆記中臨時上傳的檔案（用於取消時清理）
  const newRecordTempFilesRef = useRef<string[]>([]);
  const [serviceCompanies, setServiceCompanies] = useState<any[]>([]);
  const [serviceTargets, setServiceTargets] = useState<any[]>([]);

  // 移除未使用的資料同步hook（避免不必要的性能開銷）

  // DateSelector刷新函數的ref
  const dateRefreshRef = useRef<(() => Promise<void>) | null>(null);

  // 服務資料載入回調
  const handleServiceDataLoaded = useCallback(
    (companies: any[], targets: any[]) => {
      setServiceCompanies(companies);
      setServiceTargets(targets);
    },
    []
  );

  // 新增記錄的回調函數
  const handleProjectChange = useCallback((projectId?: string) => {
    setNewRecord((prev) => ({
      ...prev,
      project_id: projectId ? parseInt(projectId) : undefined,
      execution_work_id: undefined,
      work_item_id: undefined,
    }));
  }, []);

  const handleExecutionWorkChange = useCallback((executionWorkId?: string) => {
    setNewRecord((prev) => ({
      ...prev,
      execution_work_id: executionWorkId
        ? parseInt(executionWorkId)
        : undefined,
      work_item_id: undefined,
    }));
  }, []);

  const handleWorkItemChange = useCallback((workItemId?: string[]) => {
    setNewRecord((prev) => ({
      ...prev,
      work_item_id:
        workItemId && workItemId.length > 0
          ? parseInt(workItemId[0])
          : undefined,
    }));
  }, []);

  const fetchReports = async (docDate?: string) => {
    if (!authFetch) return;
    setIsLoading(true);
    try {
      const url = docDate
        ? `/api/records/consolidated/today?doc_date=${docDate}`
        : "/api/records/consolidated/today";
      const response = await authFetch(url);
      if (response.ok) {
        const data: ConsolidatedReport[] = await response.json();
        setReports(data);
        if (data.some((report) => report.ai_content)) {
          setIsAiViewActive(true);
        }
      }
    } catch (error) {
      console.error("無法取得彙整報告:", error);
      toast.error("無法取得彙整報告");
    } finally {
      setIsLoading(false);
    }
  };

  const fetchWritingStatus = async (docDate?: string) => {
    if (!authFetch) return;
    try {
      const url = docDate
        ? `/api/records/writing-status?doc_date=${docDate}`
        : "/api/records/writing-status";
      const response = await authFetch(url);
      if (response.ok) {
        const status: WritingStatus = await response.json();
        setWritingStatus(status);
      }
    } catch (error) {
      console.error("無法獲取填寫狀態:", error);
    }
  };

  const fetchProjects = async () => {
    if (!authFetch) return;
    try {
      const response = await authFetch("/api/projects/");
      if (response.ok) {
        setProjects(await response.json());
      }
    } catch (error) {
      console.error("無法獲取專案列表:", error);
      toast.error("無法獲取專案列表");
    }
  };

  // ✅ 修復: 合併兩個 useEffect，避免重複 API 呼叫
  useEffect(() => {
    if (!authFetch) return;

    // 只在初始化時載入專案列表
    fetchProjects();

    const docDate = selectedDate ? selectedDate.replace(/-/g, "") : undefined;

    // 載入報告
    const loadReports = async () => {
      setIsLoading(true);
      try {
        const url = docDate
          ? `/api/records/consolidated/today?doc_date=${docDate}`
          : "/api/records/consolidated/today";
        const response = await authFetch(url);
        if (response.ok) {
          const data: ConsolidatedReport[] = await response.json();
          setReports(data);
          if (data.some((report) => report.ai_content)) {
            setIsAiViewActive(true);
          }
        }
      } catch (error) {
        console.error("無法取得彙整報告:", error);
        toast.error("無法取得彙整報告");
      } finally {
        setIsLoading(false);
      }
    };

    // 載入 writing status
    const loadWritingStatus = async () => {
      try {
        const url = docDate
          ? `/api/records/writing-status?doc_date=${docDate}`
          : "/api/records/writing-status";
        const response = await authFetch(url);
        if (response.ok) {
          const status: WritingStatus = await response.json();
          setWritingStatus(status);
        }
      } catch (error) {
        console.error("無法獲取填寫狀態:", error);
      }
    };

    loadReports();
    loadWritingStatus();
  }, [authFetch, selectedDate]); // ✅ 只依賴真正需要的變數

  // 處理日期變更
  const handleDateChange = (newDate: string) => {
    onDateChange(newDate);
  };

  const handleEnhanceOne = async (sopno: string) => {
    if (!authFetch || !user?.employee?.empno) return;

    // 找到對應的報告 - 使用 sopno 精確識別
    const report = reports.find((r) => r.sopno === sopno);
    if (!report) {
      throw new Error("找不到對應的報告");
    }

    // 使用 daily_no + sopno 作為唯一識別符
    const reportKey = `${report.daily_no}-${report.sopno}`;
    setGeneratingAiFor((prev) => new Set([...prev, reportKey]));

    try {
      // 驗證必要字段
      if (!report.daily_no) {
        throw new Error("找不到該報告的daily_no");
      }

      if (!report.sopno) {
        throw new Error("找不到執行工作編號(sopno)，無法進行AI增強");
      }

      // 檢查 planno 是否存在，如果不存在則使用 "NULL" 作為佔位符
      const planno = report.project?.planno || "NULL";

      const response = await authFetch(
        `/api/ai/enhance_one/${report.daily_no}/${planno}/${report.sopno}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) {
        throw new Error("AI 潤飾失敗");
      }

      const enhancedReport = await response.json();

      // 更新報告內容 - 使用 daily_no + sopno 精確識別
      setReports((prev) =>
        prev.map((r) =>
          r.daily_no === report.daily_no && r.sopno === report.sopno
            ? { ...r, ai_content: enhancedReport.ai_content }
            : r
        )
      );

      if (!isAiViewActive) setIsAiViewActive(true);
      toast.success(`專案 ${report.project.plan_subj_c} 已完成 AI 潤飾！`);
    } catch (error: any) {
      console.error(error);
      toast.error(error.message || "AI 潤飾此專案時發生錯誤");
    } finally {
      setGeneratingAiFor((prev) => {
        const newSet = new Set(prev);
        newSet.delete(reportKey);
        return newSet;
      });
    }
  };

  const handleEnhanceAll = async () => {
    if (!authFetch) return;
    setIsGeneratingAllAi(true);

    // 立即顯示AI視圖並設置所有專案為生成中狀態
    setIsAiViewActive(true);

    try {
      // 為每個專案依序調用單獨的AI增強API，以保持UI一致性
      const enhancePromises = reports.map(async (report) => {
        if (!report.sopno || !report.daily_no) {
          console.warn(
            `跳過專案 ${report.project.plan_subj_c}: 缺少sopno或daily_no`
          );
          return;
        }

        // 檢查 planno 是否存在，如果不存在則使用 "NULL" 作為佔位符
        const planno = report.project?.planno || "NULL";

        // 使用 daily_no + sopno 作為唯一識別符
        const reportKey = `${report.daily_no}-${report.sopno}`;

        try {
          // 設置該專案為生成中狀態
          setGeneratingAiFor((prev) => new Set([...prev, reportKey]));

          const response = await authFetch(
            `/api/ai/enhance_one/${report.daily_no}/${planno}/${report.sopno}`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
            }
          );

          if (response.ok) {
            const enhancedReport = await response.json();

            // 更新該專案的AI內容 - 使用 daily_no + sopno 精確識別
            setReports((prev) =>
              prev.map((r) =>
                r.daily_no === report.daily_no && r.sopno === report.sopno
                  ? { ...r, ai_content: enhancedReport.ai_content }
                  : r
              )
            );
          } else {
            console.error(`專案 ${report.project.plan_subj_c} AI增強失敗`);
          }
        } catch (error) {
          console.error(
            `專案 ${report.project.plan_subj_c} AI增強出錯:`,
            error
          );
        } finally {
          // 清除該專案的生成中狀態
          setGeneratingAiFor((prev) => {
            const newSet = new Set(prev);
            newSet.delete(reportKey);
            return newSet;
          });
        }
      });

      // 等待所有專案完成
      await Promise.all(enhancePromises);

      toast.success("所有報告皆已完成 AI 潤飾！");
    } catch (error: any) {
      console.error(error);
      toast.error(error.message || "批量AI潤飾時發生錯誤");
    } finally {
      setIsGeneratingAllAi(false);
      setGeneratingAiFor(new Set()); // 確保清除任何剩餘的生成狀態
    }
  };

  const startEdit = (report: ConsolidatedReport) => {
    if (!report.sopno) {
      toast.error("無法編輯：缺少執行工作編號");
      return;
    }
    setEditingSopno(report.sopno);
    setEditContent(report.content);
    setEditFiles(
      report.files.map((f) => ({
        ...f,
        id: f.id || f.url,
        is_selected_for_ai: !!f.is_selected_for_ai,
      }))
    );
  };

  const cancelEdit = () => {
    setEditingSopno(null);
    setEditContent("");
    setEditFiles([]);
  };

  const saveEdit = async () => {
    if (editingSopno === null || !authFetch) return;
    setIsSaving(true);
    try {
      const reportToUpdate = reports.find((r) => r.sopno === editingSopno);
      if (!reportToUpdate) throw new Error("找不到原始報告");

      // 使用sopno來精確識別要更新的記錄
      if (!reportToUpdate.sopno) {
        throw new Error("找不到執行工作編號，無法更新記錄");
      }

      // 檢查 planno 是否存在，如果不存在則使用 "NULL" 作為佔位符
      const planno = reportToUpdate.project?.planno || "NULL";

      const response = await authFetch(
        `/api/drafts/by-daily-planno-sopno/${reportToUpdate.daily_no}/${planno}/${reportToUpdate.sopno}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            content: editContent,
            files: editFiles,
          }),
        }
      );

      if (!response.ok) throw new Error("更新報告失敗");

      // 重新獲取最新內容
      const docDate = selectedDate ? selectedDate.replace(/-/g, "") : undefined;
      await fetchReports(docDate);
      toast.success("報告草稿更新成功！");
      cancelEdit();
    } catch (error) {
      console.error(error);
      toast.error("更新失敗，請稍後再試。");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSubmitReport = async () => {
    if (!authFetch) return;
    if (reports.length === 0) {
      toast.error("沒有可提交的報告內容。");
      return;
    }
    if (!selectedDate) {
      toast.error("請先選擇日期。");
      return;
    }
    if (!window.confirm("確定要提交此版本作為今日的最終日報嗎？")) return;

    setIsSubmitting(true);
    try {
      // 將選中的日期轉換為 YYYYMMDD 格式
      const docDate = selectedDate.replace(/-/g, "");
      const response = await authFetch(
        `/api/legacy/upload-daily-report?doc_date=${docDate}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );
      if (!response.ok) {
        const errData = await response
          .json()
          .catch(() => ({ detail: "提交失敗" }));
        throw new Error(errData.detail);
      }
      const result = await response.json();
      toast.success(`日報已成功上傳！日報編號: ${result.daily_no}`);

      // 立即跳轉到日報首頁
      if (onSwitchToDaily) {
        onSwitchToDaily();
      }

      // 重新獲取日期範圍（因為補教只會補教一次，當天就會從可用日期中移除）
      if (dateRefreshRef.current) {
        await dateRefreshRef.current();
      }

      // 用戶將跳轉到日報首頁，不需要重新獲取狀態
    } catch (error: any) {
      console.error(error);
      toast.error(`上傳日報時發生錯誤: ${error.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditFileUpload = async (filesToUpload: FileList) => {
    if (!filesToUpload || filesToUpload.length === 0 || !authFetch) return;
    const uploadPromises = Array.from(filesToUpload).map(async (file) => {
      const formData = new FormData();
      formData.append("file", file);
      try {
        const response = await authFetch("/api/records/upload", {
          method: "POST",
          body: formData,
        });
        if (!response.ok) throw new Error(`檔案 ${file.name} 上傳失敗`);
        const uploadedFile: FileAttachment = await response.json();
        const newFile: FileForUpload = {
          name: uploadedFile.name,
          type: uploadedFile.type,
          size: uploadedFile.size,
          url: uploadedFile.url,
          is_selected_for_ai: false,
        };
        setEditFiles((prev) => [...prev, newFile]);
      } catch (error: any) {
        console.error(error);
        toast.error(error.message);
      }
    });
    await Promise.all(uploadPromises);
  };

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

  const handleRemoveEditFile = useCallback(
    async (imageUrl: string) => {
      try {
        let relativePath: string;

        if (imageUrl.startsWith("http")) {
          const url = new URL(imageUrl);
          relativePath = url.pathname;
        } else {
          relativePath = imageUrl;
        }

        const filename = relativePath.split("/").pop();

        if (!filename) {
          throw new Error("無法從 URL 中解析檔案名稱");
        }

        await authFetch(`/api/records/delete/${filename}`, {
          method: "DELETE",
        });

        setEditFiles((prev) =>
          prev.filter((file) => file.url !== relativePath)
        );

        setEditContent((prev) =>
          (prev || "").replace(
            new RegExp(`<img[^>]*src="${imageUrl}"[^>]*>`, "g"),
            ""
          )
        );
      } catch (error) {
        console.error("刪除編輯檔案時發生錯誤:", error);
        toast.error("檔案刪除失敗");
      }
    },
    [authFetch]
  );

  // 處理來自編輯用 RichTextEditor 的檔案上傳回調
  const handleEditEditorFileUpload = useCallback((file: FileForUpload) => {
    setEditFiles((prev) => [...prev, file]);
  }, []);

  const handleNewRecordUpload = async (filesToUpload: FileList) => {
    if (!filesToUpload || filesToUpload.length === 0 || !authFetch) return;
    setIsUploadingNewFile(true);
    const uploadPromises = Array.from(filesToUpload).map(async (file) => {
      const formData = new FormData();
      formData.append("file", file);
      try {
        const response = await authFetch("/api/records/upload", {
          method: "POST",
          body: formData,
        });
        if (!response.ok) throw new Error(`檔案 ${file.name} 上傳失敗`);
        const uploadedFile: FileAttachment = await response.json();
        const newFile: FileForUpload = {
          name: uploadedFile.name,
          type: uploadedFile.type,
          size: uploadedFile.size,
          url: uploadedFile.url,
          is_selected_for_ai: false,
        };
        setNewRecord((prev) => ({
          ...prev,
          files: [...(prev.files || []), newFile],
        }));
      } catch (error: any) {
        console.error(error);
        toast.error(error.message);
      }
    });
    await Promise.all(uploadPromises);
    setIsUploadingNewFile(false);
  };

  const handleNewRecordAiSelectionChange = (
    fileUrl: string,
    isSelected: boolean
  ) => {
    setNewRecord((prev) => ({
      ...prev,
      files: (prev.files || []).map((f) =>
        f.url === fileUrl ? { ...f, is_selected_for_ai: isSelected } : f
      ),
    }));
  };

  const handleRemoveNewRecordFile = useCallback(
    async (imageUrl: string) => {
      try {
        let relativePath: string;

        if (imageUrl.startsWith("http")) {
          const url = new URL(imageUrl);
          relativePath = url.pathname;
        } else {
          relativePath = imageUrl;
        }

        const filename = relativePath.split("/").pop();

        if (!filename) {
          throw new Error("無法從 URL 中解析檔案名稱");
        }

        await authFetch(`/api/records/delete/${filename}`, {
          method: "DELETE",
        });

        setNewRecord((prev) => ({
          ...prev,
          files: (prev.files || []).filter((file) => file.url !== relativePath),
        }));

        setNewRecord((prev) => ({
          ...prev,
          content: (prev.content || "").replace(
            new RegExp(`<img[^>]*src="${imageUrl}"[^>]*>`, "g"),
            ""
          ),
        }));
      } catch (error) {
        console.error("刪除新記錄檔案時發生錯誤:", error);
        toast.error("檔案刪除失敗");
      }
    },
    [authFetch]
  );

  // 清理新增筆記中的臨時檔案
  const cleanupNewRecordTempFiles = useCallback(async () => {
    if (!authFetch || newRecordTempFilesRef.current.length === 0) return;

    // 刪除所有臨時檔案
    for (const fileUrl of newRecordTempFilesRef.current) {
      try {
        let filename = fileUrl;
        if (fileUrl.startsWith("http")) {
          const url = new URL(fileUrl);
          filename = url.pathname;
        }
        filename = filename.replace("/uploads/", "");

        // 解碼文件名（如果已經編碼），然後再編碼一次以確保正確傳遞
        // 避免雙重編碼問題
        try {
          filename = decodeURIComponent(filename);
        } catch (e) {
          // 如果解碼失敗，說明可能未編碼，直接使用原始文件名
        }

        await authFetch(`/api/records/delete/${encodeURIComponent(filename)}`, {
          method: "DELETE",
        });
      } catch (error) {
        console.error("Failed to delete temp file:", fileUrl, error);
      }
    }

    // 清空追蹤列表
    newRecordTempFilesRef.current = [];
  }, [authFetch]);

  // 組件卸載時清理臨時檔案
  useEffect(() => {
    return () => {
      // 在卸載時觸發清理，但不等待完成（避免 DOM 操作錯誤）
      if (newRecordTempFilesRef.current.length > 0) {
        // 使用 void 表示故意不等待 Promise
        void cleanupNewRecordTempFiles();
      }
    };
  }, [cleanupNewRecordTempFiles]);

  // 處理關閉新增筆記 Modal（清理臨時檔案並重置狀態）
  const handleCloseNewRecordModal = useCallback(async () => {
    // 清理臨時上傳的檔案
    await cleanupNewRecordTempFiles();

    // 重置表單狀態
    setNewRecord({
      content: "",
      project_id: undefined,
      execution_work_id: undefined,
      work_item_id: undefined,
      service_cocode: undefined,
      service_empno: undefined,
      files: [],
      execution_time_minutes: 0,
    });

    // 關閉 Modal
    setIsAddNoteModalOpen(false);
  }, [cleanupNewRecordTempFiles]);

  // 處理來自新增用 RichTextEditor 的檔案上傳回調
  const handleNewRecordEditorFileUpload = useCallback((file: FileForUpload) => {
    // 記錄臨時檔案 URL（用於取消時刪除）
    newRecordTempFilesRef.current.push(file.url);

    setNewRecord((prev) => {
      const updatedFiles = [...(prev.files || []), file];
      return {
        ...prev,
        files: updatedFiles,
      };
    });
  }, []);

  const handleSaveNewRecord = async () => {
    if (!authFetch) return;
    // 工作計畫現在為非必選項
    // if (!newRecord.project_id) {
    //   toast.error("請選擇工作計劃");
    //   return;
    // }
    if (!newRecord.execution_work_id) {
      toast.error("請選擇執行工作");
      return;
    }
    // 工作項目現在根據執行工作是否有項目來決定是否必選
    // if (!newRecord.work_item_id) {
    //   toast.error("請選擇工作項目");
    //   return;
    // }
    // 服務公司和服務對象現在為非必填項目
    // if (!newRecord.service_company_id) {
    //   toast.error("請選擇服務公司");
    //   return;
    // }
    // if (!newRecord.service_target_id) {
    //   toast.error("請選擇服務對象");
    //   return;
    // }
    if (
      !newRecord.content?.trim() &&
      (!newRecord.files || newRecord.files.length === 0)
    ) {
      toast.error("請填寫內容或附加檔案");
      return;
    }
    if (
      !newRecord.execution_time_minutes ||
      newRecord.execution_time_minutes === 0
    ) {
      toast.error("請設定執行時間");
      return;
    }
    setIsSavingNewRecord(true);
    try {
      // 保存到 tdr_draft 資料表
      if (!user?.employee?.empno) {
        toast.error("無法獲取用戶信息");
        return;
      }

      // 檢查今天是否已經有暫存記錄
      let daily_no;
      try {
        const docDate = selectedDate
          ? selectedDate.replace(/-/g, "")
          : new Date().toISOString().slice(0, 10).replace(/-/g, "");
        const existingDraftsResponse = await authFetch(
          `/api/drafts/${user.employee.empno}?doc_date=${docDate}&draft_type=TEMP`
        );
        if (existingDraftsResponse.ok) {
          const existingDrafts = await existingDraftsResponse.json();
          if (existingDrafts.length > 0) {
            // 使用現有記錄的daily_no
            daily_no = existingDrafts[0].daily_no;
          }
        }
      } catch (error) {
        console.warn("檢查現有暫存失敗:", error);
      }

      // 如果沒有找到現有的 daily_no，才取得新的
      if (!daily_no) {
        const dailyNoResponse = await authFetch("/api/legacy/next-daily-no");
        const { daily_no: newDailyNo } = await dailyNoResponse.json();
        daily_no = newDailyNo;
      }

      // 準備暫存數據
      const draftData = {
        daily_no,
        empno: user.employee.empno,
        cocode: user.employee.cocode || "001", // 預設公司代碼
        doc_date: selectedDate
          ? selectedDate.replace(/-/g, "")
          : new Date().toISOString().slice(0, 10).replace(/-/g, ""), // YYYYMMDD
        draft_type: "TEMP",
        draft_content: {
          content: newRecord.content || "",
          planno: newRecord.project_id?.toString(),
          plan_subj_c: undefined,
          sopno: newRecord.execution_work_id?.toString(),
          sop_desc_c: undefined,
          work_item_seq: newRecord.work_item_id
            ? [newRecord.work_item_id.toString()]
            : [],
          work_item_name: undefined,
          service_cocode: newRecord.service_cocode,
          service_empno: newRecord.service_empno,
          service_empnamec: undefined,
          service_deptno: undefined,
          files: newRecord.files || [],
          execution_time_minutes: newRecord.execution_time_minutes || 0,
        },
      };

      // 保存暫存
      const saveResponse = await authFetch("/api/drafts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(draftData),
      });

      if (!saveResponse.ok) {
        throw new Error("保存暫存失敗");
      }

      // 重新獲取最新內容
      const docDate = selectedDate ? selectedDate.replace(/-/g, "") : undefined;
      await fetchReports(docDate);

      setNewRecord({
        content: "",
        project_id: undefined,
        execution_work_id: undefined,
        work_item_id: undefined,
        service_cocode: undefined,
        service_empno: undefined,
        files: [],
        execution_time_minutes: 0,
      });
      // 保存成功後清空臨時檔案追蹤（這些檔案已經被記錄引用）
      newRecordTempFilesRef.current = [];
      setIsAddNoteModalOpen(false);
      toast.success("記錄儲存成功！");
    } catch (error) {
      console.error("儲存筆記時發生錯誤:", error);
      toast.error("儲存失敗，請稍後再試。");
    } finally {
      setIsSavingNewRecord(false);
    }
  };

  const handleApplyAiSuggestion = (aiContent: string) => {
    console.log("=== 套用 AI 建議 ===");
    console.log("當前 editFiles:", editFiles);
    console.log("當前 editContent 長度:", editContent.length);

    // 提取當前編輯內容中的所有圖片標籤
    const imgRegex = /<img[^>]*>/gi;
    const images = editContent.match(imgRegex) || [];
    console.log("找到的圖片數量:", images.length);

    // 將純文字的換行符轉換為 HTML 的 <br> 標籤
    // 保持原始的換行格式（單換行和雙換行都保留）
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

  if (isLoading) {
    return <div className="p-6 text-center">載入中...</div>;
  }

  // 只有在完全沒有其他可填寫日期時才顯示禁用提示
  if (
    writingStatus &&
    !writingStatus.allowed &&
    selectedDate &&
    !writingStatus.has_other_writable_dates
  ) {
    return (
      <div className="p-6">
        <div className="max-w-2xl mx-auto text-center">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
            <div className="flex items-center justify-center mb-4">
              <div className="flex-shrink-0">
                <svg
                  className="h-12 w-12 text-yellow-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
                  />
                </svg>
              </div>
            </div>
            <h3 className="text-lg font-semibold text-yellow-800 mb-2">
              無法填寫此日期的日報
            </h3>
            <p className="text-yellow-700 mb-4">{writingStatus.message}</p>
            <p className="text-sm text-yellow-600 mb-4">
              請等待隔天8:30後填寫新的日報。
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between mb-4 sm:mb-6 space-y-4 lg:space-y-0">
          <div className="flex flex-col lg:flex-row lg:items-center lg:space-x-4">
            <div>
              <h2 className="text-xl sm:text-2xl font-bold text-gray-900 h-6 sm:h-8 flex items-center">
                日報編輯
              </h2>
              {writingStatus && (
                <div className="flex flex-col sm:flex-row sm:items-center mt-1 text-base text-gray-600">
                  <span className="mr-0 sm:mr-2">
                    🕐 {writingStatus.current_time}
                  </span>
                  <span className="text-blue-600">{writingStatus.message}</span>
                </div>
              )}
            </div>
            <DateSelector
              selectedDate={selectedDate || ""}
              onDateChange={handleDateChange}
              className="mt-2 lg:mt-0"
              onRefreshRef={dateRefreshRef}
              showOnlyWritableDates={false}
            />
          </div>
          <div className="flex flex-row items-center gap-3">
            <button
              onClick={() => setIsAddNoteModalOpen(true)}
              disabled={editingSopno !== null || generatingAiFor.size > 0}
              className={`inline-flex items-center justify-center px-3 sm:px-4 h-10 text-xs sm:text-sm rounded-lg ${blueButtonStyle} disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed flex-shrink-0`}
            >
              <Plus className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">新增筆記</span>
              <span className="sm:hidden">新增</span>
            </button>
            <button
              onClick={handleEnhanceAll}
              disabled={
                isGeneratingAllAi ||
                reports.length === 0 ||
                editingSopno !== null ||
                generatingAiFor.size > 0
              }
              className="inline-flex items-center justify-center px-3 sm:px-4 h-10 text-xs sm:text-sm font-medium rounded-lg bg-gradient-to-r from-purple-100 to-blue-100 text-purple-700 hover:from-purple-200 hover:to-blue-200 transition-all duration-200 border border-purple-200 disabled:from-gray-100 disabled:to-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed disabled:border-gray-300 flex-shrink-0"
            >
              {isGeneratingAllAi ? (
                <div className="w-4 h-4 border-2 border-transparent border-t-purple-500 rounded-full animate-spin mr-2"></div>
              ) : (
                <Wand2 className="w-4 h-4 mr-2" />
              )}
              <span className="whitespace-nowrap">
                {isGeneratingAllAi ? (
                  "AI 處理中..."
                ) : (
                  <>
                    <span className="hidden sm:inline">✨ AI 潤飾全部</span>
                    <span className="sm:hidden">AI 潤飾</span>
                  </>
                )}
              </span>
            </button>
            <button
              onClick={handleSubmitReport}
              disabled={isSubmitting || editingSopno !== null}
              className={`inline-flex items-center justify-center px-3 sm:px-4 h-10 text-xs sm:text-sm rounded-lg ${blueButtonStyle} disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed flex-shrink-0`}
            >
              <Upload className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">
                {isSubmitting ? "提交中..." : "上傳最終版"}
              </span>
              <span className="sm:hidden">
                {isSubmitting ? "提交中..." : "上傳"}
              </span>
            </button>
          </div>
        </div>

        <div className="space-y-6 sm:space-y-8 mt-6">
          {reports.map((report) => (
            <div
              key={report.project.id}
              className={`relative grid grid-cols-1 ${
                isAiViewActive ? "xl:grid-cols-2" : ""
              } gap-x-4 sm:gap-x-6 gap-y-6 sm:gap-y-12 items-stretch bg-gray-50 p-3 sm:p-4 rounded-xl border`}
            >
              {/* --- Card 1: Original Report --- */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 sm:p-6 w-full flex flex-col h-full">
                <div className="mb-4">
                  {/* 第一行：工作計畫 + 按鈕 */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <div
                        className={`inline-flex items-center px-3 py-1 text-base font-medium rounded-md ${
                          getProjectColors(report.project.plan_subj_c).tag
                        }`}
                      >
                        {report.project.plan_subj_c}
                      </div>
                      {report.total_execution_time_minutes !== undefined &&
                        report.total_execution_time_minutes > 0 && (
                          <span className="text-base text-blue-600 bg-blue-50 px-2 py-1 rounded font-medium">
                            {formatMinutesToHours(
                              report.total_execution_time_minutes
                            )}
                          </span>
                        )}
                    </div>
                    {editingSopno !== report.sopno && (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleEnhanceOne(report.sopno!)}
                          disabled={
                            generatingAiFor.size > 0 ||
                            isGeneratingAllAi ||
                            editingSopno !== null
                          }
                          className="inline-flex items-center justify-center px-3 py-2 text-xs sm:text-sm font-medium rounded-lg bg-gradient-to-r from-purple-100 to-blue-100 text-purple-700 hover:from-purple-200 hover:to-blue-200 transition-all duration-200 border border-purple-200 disabled:from-gray-100 disabled:to-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed disabled:border-gray-300"
                        >
                          {generatingAiFor.has(
                            `${report.daily_no}-${report.sopno}`
                          ) ? (
                            <div className="w-4 h-4 border-2 border-transparent border-t-purple-500 rounded-full animate-spin mr-2"></div>
                          ) : (
                            <Wand2 className="w-4 h-4 mr-2" />
                          )}
                          <span className="whitespace-nowrap">潤飾</span>
                        </button>
                        <button
                          onClick={() => startEdit(report)}
                          disabled={
                            generatingAiFor.size > 0 || isGeneratingAllAi
                          }
                          className={`inline-flex items-center justify-center px-3 py-2 text-xs sm:text-sm font-medium rounded-lg ${
                            getProjectColors(report.project.plan_subj_c).button
                          } disabled:bg-gray-300 disabled:cursor-not-allowed`}
                        >
                          <Edit className="w-4 h-4 mr-2" /> 編輯
                        </button>
                      </div>
                    )}
                  </div>

                  {/* 第二行：執行工作 */}
                  {report.execution_work_name && (
                    <div className="mb-2">
                      <div className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-md bg-green-100 text-green-800">
                        {report.execution_work_name}
                      </div>
                    </div>
                  )}

                  {/* 第三行：工作項目 */}
                  {report.work_item_name && (
                    <div>
                      <div className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-md bg-purple-100 text-purple-800">
                        {report.work_item_name}
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex-grow">
                  {editingSopno === report.sopno ? (
                    <div className="space-y-4">
                      <RichTextEditor
                        value={editContent}
                        onChange={setEditContent}
                        onFileUpload={handleEditEditorFileUpload}
                        onFileRemove={handleRemoveEditFile}
                        files={editFiles}
                        placeholder="編輯記錄內容... (可直接貼上圖片)"
                      />
                      <AttachedFilesManager
                        files={editFiles}
                        onRemoveFile={handleRemoveEditFile}
                        onAiSelectionChange={handleEditAiSelectionChange}
                        isUploading={false}
                        showUploadButton={false}
                      />
                      <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
                        <button
                          onClick={saveEdit}
                          disabled={isSaving}
                          className={`inline-flex items-center justify-center px-4 py-2 text-sm rounded-lg ${blueButtonStyle} disabled:bg-gray-200 order-1`}
                        >
                          <Save className="w-4 h-4 mr-2" />
                          {isSaving ? "儲存中..." : "儲存草稿"}
                        </button>
                        <button
                          onClick={cancelEdit}
                          className="px-4 py-2 bg-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-300 order-2"
                        >
                          取消
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {/* 報告內容 */}
                      <div>
                        <div className="flex items-start space-x-2">
                          <div
                            className={`${TypographyClasses.richTextDisplay} flex-1`}
                            dangerouslySetInnerHTML={{ __html: report.content }}
                          />
                          {/* {report.files && report.files.length > 0 && (
                            <img
                              src="/attached.gif"
                              alt="有附件"
                              className="w-4 h-4 mt-1 flex-shrink-0"
                              title="此日報包含附件"
                            />
                          )} */}
                        </div>
                        <AttachedFilesDisplay files={report.files} />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* --- Card 2: AI Reference --- */}
              {isAiViewActive && (
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 w-full h-full">
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="inline-flex items-center px-3 py-1 text-sm font-medium rounded-lg bg-gradient-to-r from-purple-100 to-blue-100 text-purple-700 border border-purple-200">
                      <Wand2 className="w-4 h-4 mr-1.5" /> AI 參考資料
                    </div>
                  </div>
                  {generatingAiFor.has(`${report.daily_no}-${report.sopno}`) ? (
                    <p className="text-base text-gray-500 italic">
                      AI 正在為此專案生成潤飾內容...
                    </p>
                  ) : report.ai_content ? (
                    <div
                      className={`${TypographyClasses.richTextDisplay} whitespace-pre-wrap`}
                    >
                      <div
                        dangerouslySetInnerHTML={{
                          __html: report.ai_content.replace(/\n/g, "<br />"),
                        }}
                      />
                    </div>
                  ) : (
                    <p className="text-base text-gray-400 italic">
                      此專案無 AI 潤飾內容。點擊魔法棒按鈕開始生成。
                    </p>
                  )}
                </div>
              )}

              {/* --- Apply AI Suggestion Button (FINAL - Corrected Position) --- */}
              {editingSopno === report.sopno &&
                isAiViewActive &&
                report.ai_content && (
                  <div className="absolute z-10 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                    <button
                      onClick={() =>
                        handleApplyAiSuggestion(report.ai_content!)
                      }
                      className="flex items-center justify-center w-12 h-12 bg-white rounded-full shadow-lg hover:bg-gray-100 border border-gray-300 text-gray-600 hover:text-gray-800 hover:border-gray-400 transition-all duration-200 ease-in-out transform hover:scale-110"
                      title="套用 AI 建議"
                    >
                      <ArrowUp className="w-6 h-6 lg:hidden" />
                      <ArrowLeft className="w-6 h-6 hidden lg:block" />
                    </button>
                  </div>
                )}
            </div>
          ))}

          {reports.length === 0 && !isLoading && (
            <div className="text-center py-12 text-gray-500">
              <p>今天還沒有記錄，點擊右上角「新增筆記」來開始。</p>
            </div>
          )}
        </div>
      </div>

      {/* --- Add New Note Modal --- */}
      {isAddNoteModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 transition-opacity duration-300 ease-in-out animate-fade-in p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-screen overflow-y-auto transform transition-all duration-300 ease-in-out scale-95 animate-fade-in-scale">
            <div className="p-4 sm:p-6 lg:p-8">
              <div className="flex justify-between items-center mb-4 sm:mb-6">
                <h3 className="text-lg sm:text-xl font-semibold text-gray-900">
                  新增筆記到今日報告
                </h3>
                <button
                  onClick={handleCloseNewRecordModal}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              <div className="space-y-4 sm:space-y-6">
                {/* 級聯工作選擇器 */}
                <CascadingWorkSelector
                  selectedProjectId={newRecord.project_id?.toString()}
                  selectedExecutionWorkId={newRecord.execution_work_id?.toString()}
                  selectedWorkItemId={
                    newRecord.work_item_id
                      ? [newRecord.work_item_id.toString()]
                      : undefined
                  }
                  onProjectChange={handleProjectChange}
                  onExecutionWorkChange={handleExecutionWorkChange}
                  onWorkItemChange={handleWorkItemChange}
                  onServiceDataLoaded={handleServiceDataLoaded}
                  required={false}
                />

                {/* 服務選擇器 */}
                <ServiceSelector
                  selectedCompanyId={newRecord.service_cocode}
                  selectedTargetId={newRecord.service_empno}
                  onCompanyChange={(cocode) =>
                    setNewRecord((prev) => ({
                      ...prev,
                      service_cocode: cocode,
                    }))
                  }
                  onTargetChange={(empno) =>
                    setNewRecord((prev) => ({
                      ...prev,
                      service_empno: empno,
                    }))
                  }
                  serviceCompanies={serviceCompanies}
                  serviceTargets={serviceTargets}
                  required={false}
                />
                <ExecutionTimeSelector
                  totalMinutes={newRecord.execution_time_minutes || 0}
                  onChange={(minutes) =>
                    setNewRecord((prev) => ({
                      ...prev,
                      execution_time_minutes: minutes,
                    }))
                  }
                  required
                />
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    內容
                  </label>
                  <RichTextEditor
                    value={newRecord.content || ""}
                    onChange={(content) =>
                      setNewRecord((prev) => ({ ...prev, content }))
                    }
                    onFileUpload={handleNewRecordEditorFileUpload}
                    onFileRemove={handleRemoveNewRecordFile}
                    files={newRecord.files || []}
                    placeholder="記錄您的想法... (可直接貼上圖片或者附上檔案)"
                  />
                </div>

                <AttachedFilesManager
                  files={newRecord.files || []}
                  onRemoveFile={handleRemoveNewRecordFile}
                  onAiSelectionChange={handleNewRecordAiSelectionChange}
                  isUploading={isUploadingNewFile}
                  showUploadButton={false}
                />

                <div className="flex flex-col sm:flex-row justify-end space-y-2 sm:space-y-0 sm:space-x-4">
                  <button
                    onClick={handleCloseNewRecordModal}
                    className="px-4 py-2 bg-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-300 order-2 sm:order-1"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleSaveNewRecord}
                    disabled={isUploadingNewFile || isSavingNewRecord}
                    className={`w-full sm:w-32 py-2 px-4 rounded-lg flex items-center justify-center ${blueButtonStyle} disabled:bg-gray-200 disabled:text-gray-400 order-1 sm:order-2`}
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    {isSavingNewRecord ? "儲存中..." : "新增筆記"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      <style>{`
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes fade-in-scale {
          from { opacity: 0; transform: scale(0.95); }
          to { opacity: 1; transform: scale(1); }
        }
        .animate-fade-in {
          animation: fade-in 0.2s ease-in-out forwards;
        }
        .animate-fade-in-scale {
          animation: fade-in-scale 0.2s ease-in-out forwards;
        }
      `}</style>
    </>
  );
};

export default DailyReportTab;
