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
  Eye,
  EyeOff,
  Trash2,
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
import ServiceSelector, {
  ServiceCompany,
  ServiceTarget,
} from "./ServiceSelector";
import DateSelector from "./DateSelector";
import RichTextEditor from "./RichTextEditor";
import AiServiceSelector, { AiService } from "./AiServiceSelector";
import AiEnhanceButton from "./AiEnhanceButton";
import { toast } from "react-hot-toast";
import { TypographyClasses } from "../styles/typography";
import { formatMinutesToHours } from "../utils/timeUtils";
import { RecordsApi } from "../services/recordsApi";

interface DailyRecordCreate
  extends Omit<WorkRecordCreate, "service_company_id" | "service_target_id" | "work_item_id"> {
  work_item_ids?: number[]; // 支援多選工作項目
  service_cocode?: string;
  service_empno?: string;
  service_empnamec?: string;
  service_target_cocode?: string;
  service_deptno?: string;
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
  // ✅ writingStatus 改用 AuthContext 的全域狀態
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDeletingDraft, setIsDeletingDraft] = useState(false);
  const [editingRecordKey, setEditingRecordKey] = useState<string | null>(null); // 格式: daily_no-planno-sopno
  const [editContent, setEditContent] = useState<string>("");
  const [editFiles, setEditFiles] = useState<FileForUpload[]>([]);
  const [editProjectId, setEditProjectId] = useState<number | undefined>(
    undefined
  );
  const [editExecutionWorkId, setEditExecutionWorkId] = useState<
    number | undefined
  >(undefined);
  const [editWorkItemIds, setEditWorkItemIds] = useState<number[]>([]);
  const [editServiceCocode, setEditServiceCocode] = useState<
    string | undefined
  >(undefined);
  const [editServiceEmpno, setEditServiceEmpno] = useState<string | undefined>(
    undefined
  );
  const [editServiceEmpnamec, setEditServiceEmpnamec] = useState<
    string | undefined
  >(undefined);
  const [editServiceTargetCocode, setEditServiceTargetCocode] = useState<
    string | undefined
  >(undefined);
  const [editServiceDeptno, setEditServiceDeptno] = useState<
    string | undefined
  >(undefined);
  const [editExecutionTimeMinutes, setEditExecutionTimeMinutes] =
    useState<number>(0);
  const [editOriginalContent, setEditOriginalContent] = useState<string>("");
  const [editOriginalFiles, setEditOriginalFiles] = useState<FileForUpload[]>(
    []
  );
  const [editPendingDeleteFiles, setEditPendingDeleteFiles] = useState<
    string[]
  >([]);
  const [editPendingUploadFiles, setEditPendingUploadFiles] = useState<
    string[]
  >([]);
  const { authFetch, user, writingStatus, refreshWritingStatus } = useAuth(); // ✅ 使用全域狀態

  const [isAiViewActive, setIsAiViewActive] = useState(false);
  const [isGeneratingAllAi, setIsGeneratingAllAi] = useState(false);
  const [generatingAiFor, setGeneratingAiFor] = useState<Set<string>>(
    new Set()
  );
  const [isFocusMode, setIsFocusMode] = useState(true); // 預設隱藏其他欄位（專注模式）
  const [selectedAiService, setSelectedAiService] = useState<AiService>("aoai"); // AI 服務選擇

  // --- Modal and New Record State ---
  const [isAddNoteModalOpen, setIsAddNoteModalOpen] = useState(false);
  const [newRecord, setNewRecord] = useState<Partial<DailyRecordCreate>>({
    content: "",
    project_id: undefined,
    execution_work_id: undefined,
    work_item_ids: [], // 支援多選工作項目
    service_cocode: undefined,
    service_empno: undefined,
    service_empnamec: undefined,
    service_target_cocode: undefined,
    service_deptno: undefined,
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
      work_item_ids: undefined,
    }));
  }, []);

  const handleExecutionWorkChange = useCallback((executionWorkId?: string) => {
    setNewRecord((prev) => ({
      ...prev,
      execution_work_id: executionWorkId
        ? parseInt(executionWorkId)
        : undefined,
      work_item_ids: undefined,
    }));
  }, []);

  const handleWorkItemChange = useCallback((workItemId?: string[]) => {
    setNewRecord((prev) => ({
      ...prev,
      work_item_ids: workItemId?.map((id) => parseInt(id)),
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

  // ✅ 移除本地的 fetchWritingStatus，改用 AuthContext 的 refreshWritingStatus

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

    // ✅ 載入 writing status 使用全域 refreshWritingStatus
    if (refreshWritingStatus) {
      refreshWritingStatus(docDate);
    }

    loadReports();
  }, [authFetch, selectedDate, refreshWritingStatus]); // ✅ 只依賴真正需要的變數

  // 處理日期變更
  const handleDateChange = (newDate: string) => {
    onDateChange(newDate);
  };

  const handleEnhanceOne = async (report: ConsolidatedReport) => {
    if (!authFetch || !user?.employee?.empno) return;

    // 使用 daily_no + planno + sopno 作為唯一識別符
    const planno = report.project?.planno || "NULL";
    const reportKey = `${report.daily_no}-${planno}-${report.sopno}`;
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
        `/api/ai/enhance_one/${report.daily_no}/${planno}/${report.sopno}?ai_service=${selectedAiService}`,
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

      // 更新報告內容 - 使用 daily_no + planno + sopno 精確識別
      setReports((prev) =>
        prev.map((r) => {
          const rPlanno = r.project?.planno || "NULL";
          return r.daily_no === report.daily_no &&
                 rPlanno === planno &&
                 r.sopno === report.sopno
            ? { ...r, ai_content: enhancedReport.ai_content }
            : r;
        })
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

        // 使用 daily_no + planno + sopno 作為唯一識別符
        const reportKey = `${report.daily_no}-${planno}-${report.sopno}`;

        try {
          // 設置該專案為生成中狀態
          setGeneratingAiFor((prev) => new Set([...prev, reportKey]));

          const response = await authFetch(
            `/api/ai/enhance_one/${report.daily_no}/${planno}/${report.sopno}?ai_service=${selectedAiService}`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
            }
          );

          if (response.ok) {
            const enhancedReport = await response.json();

            // 更新該專案的AI內容 - 使用 daily_no + planno + sopno 精確識別
            setReports((prev) =>
              prev.map((r) => {
                const rPlanno = r.project?.planno || "NULL";
                return r.daily_no === report.daily_no &&
                       rPlanno === planno &&
                       r.sopno === report.sopno
                  ? { ...r, ai_content: enhancedReport.ai_content }
                  : r;
              })
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
    // 使用 daily_no + planno + sopno 組合作為唯一識別
    const planno = report.project?.planno || "NULL";
    const recordKey = `${report.daily_no}-${planno}-${report.sopno}`;
    setEditingRecordKey(recordKey);
    const content = report.content;
    const files = report.files.map((f) => ({
      ...f,
      id: f.id || f.url,
      is_selected_for_ai: !!f.is_selected_for_ai,
    }));

    // 保存原始內容和檔案列表(用於取消時恢復)
    setEditOriginalContent(content);
    setEditOriginalFiles(files);
    setEditContent(content);
    setEditFiles(files);

    // 載入所有編輯欄位的值
    setEditProjectId(
      report.project?.id ? Number(report.project.id) : undefined
    );
    setEditExecutionWorkId(report.execution_work_id);
    setEditWorkItemIds(report.work_item_ids || []);
    setEditServiceCocode(report.service_cocode);
    setEditServiceEmpno(report.service_empno);
    setEditServiceEmpnamec(report.service_target_name?.match(/^(.+)\(/)?.[1]); // 從 "姓名(工號)" 提取姓名
    setEditServiceTargetCocode(report.service_target_cocode);
    setEditServiceDeptno(report.service_deptno);
    setEditExecutionTimeMinutes(report.total_execution_time_minutes || 0);

    // 清空 pending 列表
    setEditPendingDeleteFiles([]);
    setEditPendingUploadFiles([]);
  };

  const cancelEdit = async () => {
    try {
      // 刪除編輯期間新上傳的檔案
      for (const filePath of editPendingUploadFiles) {
        try {
          // filePath 格式: YYYYMM/filename
          const [yearMonth, filename] = filePath.split("/");
          await RecordsApi.deleteFile(yearMonth, filename, authFetch);
        } catch (error) {
          console.error(`清理檔案 ${filePath} 失敗:`, error);
        }
      }

      // 清空所有編輯狀態
      setEditingRecordKey(null);
      setEditContent("");
      setEditFiles([]);
      setEditProjectId(undefined);
      setEditExecutionWorkId(undefined);
      setEditWorkItemIds([]);
      setEditServiceCocode(undefined);
      setEditServiceEmpno(undefined);
      setEditExecutionTimeMinutes(0);
      setEditOriginalContent("");
      setEditOriginalFiles([]);
      setEditPendingDeleteFiles([]);
      setEditPendingUploadFiles([]);

      toast.success("已取消編輯");
    } catch (error) {
      console.error("取消編輯時發生錯誤:", error);
      toast.error("取消編輯失敗");
    }
  };

  const deleteDraft = async () => {
    if (!authFetch || !editingRecordKey) return;

    // 確認刪除
    if (!window.confirm("確定要刪除這筆記錄嗎？此操作無法復原。")) {
      return;
    }

    // 從 editingRecordKey 解析出 daily_no, planno, sopno
    const [daily_no, planno, sopno] = editingRecordKey.split("-");

    const reportToDelete = reports.find(
      (r) => r.daily_no === daily_no &&
             (r.project?.planno || "NULL") === planno &&
             r.sopno === sopno
    );
    if (!reportToDelete) {
      toast.error("無法找到記錄資訊");
      return;
    }

    setIsDeletingDraft(true);
    try {
      const response = await authFetch(
        `/api/drafts/${daily_no}/${planno}/${sopno}`,
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        throw new Error("刪除記錄失敗");
      }

      toast.success("記錄已刪除");

      // 清空所有編輯狀態
      setEditingRecordKey(null);
      setEditContent("");
      setEditFiles([]);
      setEditProjectId(undefined);
      setEditExecutionWorkId(undefined);
      setEditWorkItemIds([]);
      setEditServiceCocode(undefined);
      setEditServiceEmpno(undefined);
      setEditExecutionTimeMinutes(0);
      setEditOriginalContent("");
      setEditOriginalFiles([]);
      setEditPendingDeleteFiles([]);
      setEditPendingUploadFiles([]);

      // 重新獲取資料
      const docDate = selectedDate ? selectedDate.replace(/-/g, "") : undefined;
      await fetchReports(docDate);

      // 刷新日期選擇器（如果有的話）
      if (dateRefreshRef.current) {
        await dateRefreshRef.current();
      }
    } catch (error) {
      console.error("刪除記錄失敗:", error);
      toast.error("刪除記錄失敗");
    } finally {
      setIsDeletingDraft(false);
    }
  };

  const saveEdit = async () => {
    if (editingRecordKey === null || !authFetch) return;

    // 驗證必填欄位
    if (!editExecutionWorkId) {
      toast.error("請選擇執行工作");
      return;
    }
    if (editExecutionTimeMinutes === 0) {
      toast.error("請設定執行時間");
      return;
    }

    setIsSaving(true);
    try {
      // 從 editingRecordKey 解析出 daily_no, planno, sopno
      const [daily_no, planno, sopno] = editingRecordKey.split("-");

      const reportToUpdate = reports.find(
        (r) => r.daily_no === daily_no &&
               (r.project?.planno || "NULL") === planno &&
               r.sopno === sopno
      );
      if (!reportToUpdate) throw new Error("找不到原始報告");

      const response = await authFetch(
        `/api/drafts/by-daily-planno-sopno/${daily_no}/${planno}/${sopno}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            content: editContent,
            files: editFiles,
            planno: editProjectId?.toString(),
            sopno: editExecutionWorkId?.toString(),
            work_item_ids: editWorkItemIds,
            service_cocode: editServiceCocode,
            service_empno: editServiceEmpno,
            service_empnamec: editServiceEmpnamec,
            service_target_cocode: editServiceTargetCocode,
            service_deptno: editServiceDeptno,
            execution_time_minutes: editExecutionTimeMinutes,
          }),
        }
      );

      if (!response.ok) throw new Error("更新報告失敗");

      // 儲存成功後，實際刪除標記為待刪除的檔案
      for (const filePath of editPendingDeleteFiles) {
        try {
          // filePath 格式: YYYYMM/filename
          const [yearMonth, filename] = filePath.split("/");
          await RecordsApi.deleteFile(yearMonth, filename, authFetch);
        } catch (error) {
          console.error(`刪除檔案 ${filePath} 失敗:`, error);
        }
      }

      // 重新獲取最新內容
      const docDate = selectedDate ? selectedDate.replace(/-/g, "") : undefined;
      await fetchReports(docDate);
      toast.success("報告草稿更新成功！");

      // 清空所有編輯狀態
      setEditingRecordKey(null);
      setEditContent("");
      setEditFiles([]);
      setEditProjectId(undefined);
      setEditExecutionWorkId(undefined);
      setEditWorkItemIds([]);
      setEditServiceCocode(undefined);
      setEditServiceEmpno(undefined);
      setEditExecutionTimeMinutes(0);
      setEditOriginalContent("");
      setEditOriginalFiles([]);
      setEditPendingDeleteFiles([]);
      setEditPendingUploadFiles([]);
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

    // 將選中的日期轉換為 YYYYMMDD 格式（如果有破折號則移除）
    const docDate = selectedDate.replace(/-/g, "");
    // 格式化日期為中文顯示 (YYYYMMDD -> YYYY年MM月DD日)
    const formattedDate = docDate.replace(
      /(\d{4})(\d{2})(\d{2})/,
      "$1年$2月$3日"
    );
    if (!window.confirm(`確定要提交此版本作為 ${formattedDate} 的最終日報嗎？`))
      return;

    setIsSubmitting(true);
    try {
      const result = await RecordsApi.submit(docDate, authFetch);
      toast.success(`日報已成功上傳！日報編號: ${result.daily_no}`);

      // 重新獲取日期範圍（因為補教只會補教一次，當天就會從可用日期中移除）
      if (dateRefreshRef.current) {
        await dateRefreshRef.current();
      }

      // 立即跳轉到日報首頁（使用 supervisor tab）
      if (onUploadComplete) {
        // 將 YYYYMMDD 轉換為 YYYY-MM-DD 格式
        const formattedDate = docDate.replace(/(\d{4})(\d{2})(\d{2})/, "$1-$2-$3");
        onUploadComplete(formattedDate);
      }
    } catch (error: any) {
      console.error(error);
      toast.error(`上傳日報時發生錯誤: ${error.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditFileUpload = async (filesToUpload: FileList) => {
    if (!filesToUpload || filesToUpload.length === 0 || !authFetch) return;
    const uploadDocDate =
      selectedDate?.replace(/-/g, "") ||
      new Date().toISOString().slice(0, 10).replace(/-/g, "");

    const uploadPromises = Array.from(filesToUpload).map(async (file) => {
      try {
        const uploadedFile: FileAttachment = await RecordsApi.uploadFile(
          file,
          uploadDocDate,
          authFetch
        );
        const newFile: FileForUpload = {
          name: uploadedFile.name,
          type: uploadedFile.type,
          size: uploadedFile.size,
          url: uploadedFile.url,
          is_selected_for_ai: false,
        };

        // 追蹤新上傳的檔案 (從 URL 中提取完整的 YYYYMM/filename)
        const urlParts = uploadedFile.url.split("/");
        const yearMonth = urlParts[urlParts.length - 2]; // 倒數第二個是 YYYYMM
        const filename = urlParts[urlParts.length - 1]; // 最後一個是檔名
        if (yearMonth && filename) {
          setEditPendingUploadFiles((prev) => [
            ...prev,
            `${yearMonth}/${filename}`,
          ]);
        }

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

  const handleRemoveEditFile = useCallback(async (urlOrPath: string) => {
    try {
      let fullUrl: string;
      let relativePath: string;

      if (urlOrPath.startsWith("http")) {
        fullUrl = urlOrPath;
        // 解碼 URL 編碼的路徑
        relativePath = decodeURIComponent(new URL(urlOrPath).pathname);
      } else {
        relativePath = urlOrPath;
        fullUrl = getFullFileUrl(urlOrPath);
      }

      // 從路徑中提取 YYYYMM/filename (例如: /uploads/202510/xxx.png -> 202510/xxx.png)
      const pathParts = relativePath.split("/");
      const yearMonth = pathParts[pathParts.length - 2]; // 倒數第二個是 YYYYMM
      const filename = pathParts[pathParts.length - 1]; // 最後一個是檔名

      if (!yearMonth || !filename) {
        throw new Error("無法從路徑中解析年月或檔案名稱");
      }

      // 不立即刪除實體檔案,而是標記為待刪除 (包含年月目錄)
      setEditPendingDeleteFiles((prev) => [
        ...prev,
        `${yearMonth}/${filename}`,
      ]);

      setEditFiles((prev) => prev.filter((file) => file.url !== relativePath));

      setEditContent((prev) =>
        (prev || "").replace(
          new RegExp(`<img[^>]*src="${fullUrl}"[^>]*>`, "g"),
          ""
        )
      );
    } catch (error) {
      console.error("刪除編輯檔案時發生錯誤:", error);
      toast.error("檔案刪除失敗");
    }
  }, []);

  // 處理來自編輯用 RichTextEditor 的檔案上傳回調
  const handleEditEditorFileUpload = useCallback((file: FileForUpload) => {
    // 標記為新上傳的檔案 (從 URL 中提取完整的 YYYYMM/filename)
    const urlParts = file.url.split("/");
    const yearMonth = urlParts[urlParts.length - 2]; // 倒數第二個是 YYYYMM
    const filename = urlParts[urlParts.length - 1]; // 最後一個是檔名
    if (yearMonth && filename) {
      setEditPendingUploadFiles((prev) => [
        ...prev,
        `${yearMonth}/${filename}`,
      ]);
    }

    setEditFiles((prev) => [...prev, file]);
  }, []);

  const handleNewRecordUpload = async (filesToUpload: FileList) => {
    if (!filesToUpload || filesToUpload.length === 0 || !authFetch) return;
    setIsUploadingNewFile(true);
    const uploadDocDate =
      selectedDate?.replace(/-/g, "") ||
      new Date().toISOString().slice(0, 10).replace(/-/g, "");

    const uploadPromises = Array.from(filesToUpload).map(async (file) => {
      try {
        const uploadedFile: FileAttachment = await RecordsApi.uploadFile(
          file,
          uploadDocDate,
          authFetch
        );
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
    async (urlOrPath: string) => {
      try {
        let fullUrl: string;
        let relativePath: string;

        if (urlOrPath.startsWith("http")) {
          fullUrl = urlOrPath;
          // 解碼 URL 編碼的路徑
          relativePath = decodeURIComponent(new URL(urlOrPath).pathname);
        } else {
          relativePath = urlOrPath;
          fullUrl = getFullFileUrl(urlOrPath);
        }

        // 從路徑中提取 YYYYMM/filename
        const pathParts = relativePath.split("/");
        const yearMonth = pathParts[pathParts.length - 2];
        const filename = pathParts[pathParts.length - 1];

        if (!yearMonth || !filename) {
          throw new Error("無法從路徑中解析年月或檔案名稱");
        }

        await RecordsApi.deleteFile(yearMonth, filename, authFetch);

        setNewRecord((prev) => ({
          ...prev,
          files: (prev.files || []).filter((file) => file.url !== relativePath),
        }));

        setNewRecord((prev) => ({
          ...prev,
          content: (prev.content || "").replace(
            new RegExp(`<img[^>]*src="${fullUrl}"[^>]*>`, "g"),
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
        let relativePath = fileUrl;
        if (fileUrl.startsWith("http")) {
          const url = new URL(fileUrl);
          relativePath = url.pathname;
        }

        // 從路徑中提取 YYYYMM/filename
        const pathParts = relativePath.split("/");
        const yearMonth = pathParts[pathParts.length - 2];
        const filename = pathParts[pathParts.length - 1];

        if (yearMonth && filename) {
          await RecordsApi.deleteFile(yearMonth, filename, authFetch);
        }
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
      work_item_ids: [],
      service_cocode: undefined,
      service_empno: undefined,
      service_empnamec: undefined,
      service_target_cocode: undefined,
      service_deptno: undefined,
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

      // 檢查今天是否已經有暫存記錄（取得現有的 daily_no）
      let daily_no = null;
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
            // 使用現有記錄的 daily_no
            daily_no = existingDrafts[0].daily_no;
            console.log("使用現有的 daily_no:", daily_no);
          }
        }
      } catch (error) {
        console.warn("檢查現有暫存失敗:", error);
      }

      // 如果沒有找到現有的 daily_no，傳入 null
      // 後端 save_draft API 會自動生成新的 daily_no
      if (!daily_no) {
        console.log("沒有現有 daily_no，將由後端自動生成");
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
          work_item_seq: newRecord.work_item_ids?.map((id) => id.toString()) || [],
          work_item_name: undefined,
          service_cocode: newRecord.service_cocode,
          service_empno: newRecord.service_empno,
          service_empnamec: newRecord.service_empnamec,
          service_target_cocode: newRecord.service_target_cocode,
          service_deptno: newRecord.service_deptno,
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
        work_item_ids: [],
        service_cocode: undefined,
        service_empno: undefined,
        service_empnamec: undefined,
        service_target_cocode: undefined,
        service_deptno: undefined,
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
              disabled={editingRecordKey !== null || generatingAiFor.size > 0}
              className={`inline-flex items-center justify-center px-3 sm:px-4 h-10 text-xs sm:text-sm rounded-lg ${blueButtonStyle} disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed flex-shrink-0`}
            >
              <Plus className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">新增筆記</span>
              <span className="sm:hidden">新增</span>
            </button>
            {/* AI 潤飾全部按鈕 (Split Button 設計) */}
            <AiEnhanceButton
              selectedService={selectedAiService}
              onServiceChange={setSelectedAiService}
              onEnhance={handleEnhanceAll}
              disabled={
                isGeneratingAllAi ||
                reports.length === 0 ||
                editingRecordKey !== null ||
                generatingAiFor.size > 0
              }
              isLoading={isGeneratingAllAi}
            />
            <button
              onClick={handleSubmitReport}
              disabled={isSubmitting || editingRecordKey !== null}
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
                  {/* 第一行：工作計畫與操作按鈕 */}
                  <div className="mb-3">
                    <div className="flex items-center justify-between gap-4 mb-2">
                      {/* 左側：工作計畫標題 */}
                      <div className="flex-1 min-w-0">
                        <div className="inline-flex items-center px-2 py-1 text-base font-medium rounded-md bg-indigo-100 text-indigo-800 max-w-full">
                          <span className="truncate">
                            {report.project.plan_subj_c}
                          </span>
                        </div>
                      </div>

                      {/* 右側：按鈕組 */}
                      {(() => {
                        const planno = report.project?.planno || "NULL";
                        const recordKey = `${report.daily_no}-${planno}-${report.sopno}`;
                        return editingRecordKey !== recordKey;
                      })() && (
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <button
                            onClick={() => handleEnhanceOne(report)}
                            disabled={
                              generatingAiFor.size > 0 ||
                              isGeneratingAllAi ||
                              editingRecordKey !== null
                            }
                            className="inline-flex items-center justify-center px-3 py-2 text-xs sm:text-sm font-medium rounded-lg bg-gradient-to-r from-purple-100 to-blue-100 text-purple-700 hover:from-purple-200 hover:to-blue-200 transition-all duration-200 border border-purple-200 disabled:from-gray-100 disabled:to-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed disabled:border-gray-300"
                          >
                            {(() => {
                              const planno = report.project?.planno || "NULL";
                              const reportKey = `${report.daily_no}-${planno}-${report.sopno}`;
                              return generatingAiFor.has(reportKey);
                            })() ? (
                              <div className="w-4 h-4 border-2 border-transparent border-t-purple-500 rounded-full animate-spin mr-2"></div>
                            ) : (
                              <Wand2 className="w-4 h-4 mr-2" />
                            )}
                            <span className="hidden sm:inline whitespace-nowrap">
                              潤飾
                            </span>
                            <span className="sm:hidden">AI</span>
                          </button>
                          <button
                            onClick={() => startEdit(report)}
                            disabled={
                              generatingAiFor.size > 0 || isGeneratingAllAi
                            }
                            className="inline-flex items-center justify-center px-3 py-2 text-xs sm:text-sm font-medium rounded-lg bg-green-100 text-green-700 hover:bg-green-200 border border-green-200 disabled:bg-gray-300 disabled:cursor-not-allowed"
                          >
                            <Edit className="w-4 h-4 sm:mr-2" />
                            <span className="hidden sm:inline">編輯</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* 第二行：執行工作 */}
                  {report.execution_work_name && (
                    <div className="mb-2">
                      <div className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-md bg-green-100 text-green-800 max-w-full">
                        <span className="truncate">
                          {report.execution_work_name}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* 第三行：工作項目 */}
                  {report.work_item_name && (
                    <div>
                      <div className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-md bg-purple-100 text-purple-800 max-w-full">
                        <span className="truncate">
                          {report.work_item_name}
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex-grow">
                  {(() => {
                    const planno = report.project?.planno || "NULL";
                    const recordKey = `${report.daily_no}-${planno}-${report.sopno}`;
                    return editingRecordKey === recordKey;
                  })() ? (
                    <div className="space-y-4">
                      {/* 其他欄位折疊按鈕 */}
                      <button
                        onClick={() => setIsFocusMode(!isFocusMode)}
                        // Key change: justify-center will center the content horizontally.
                        className="w-full flex items-center justify-center py-0.5 bg-gray-50 hover:bg-gray-100 rounded-lg border border-gray-200 transition-colors"
                      >
                        {/* The icon now directly represents the action to be taken */}
                        <span className="text-xl font-semibold text-gray-500">
                          {isFocusMode ? "展開細項" : "收起細項"}
                        </span>
                      </button>

                      {/* 級聯工作選擇器 - 預設隱藏 */}
                      {!isFocusMode && (
                        <CascadingWorkSelector
                          selectedProjectId={editProjectId?.toString()}
                          selectedExecutionWorkId={editExecutionWorkId?.toString()}
                          selectedWorkItemId={editWorkItemIds.map((id) =>
                            id.toString()
                          )}
                          onProjectChange={(projectId) => {
                            setEditProjectId(
                              projectId ? parseInt(projectId) : undefined
                            );
                            // 當工作計畫改變時，清空執行工作和工作項目選擇
                            // 因為不同工作計畫對應的執行工作不同
                            setEditExecutionWorkId(undefined);
                            setEditWorkItemIds([]);
                          }}
                          onExecutionWorkChange={(executionWorkId) => {
                            setEditExecutionWorkId(
                              executionWorkId
                                ? parseInt(executionWorkId)
                                : undefined
                            );
                            // 當執行工作改變時，清空工作項目選擇
                            setEditWorkItemIds([]);
                          }}
                          onWorkItemChange={(workItemIds) =>
                            setEditWorkItemIds(
                              workItemIds?.map((id) => parseInt(id)) || []
                            )
                          }
                          onServiceDataLoaded={handleServiceDataLoaded}
                          required={false}
                        />
                      )}

                      {/* 服務選擇器 - 預設隱藏 */}
                      {!isFocusMode && (
                        <ServiceSelector
                          selectedCompanyId={editServiceCocode}
                          selectedTargetId={editServiceEmpno}
                          onCompanyChange={(cocode, company) => {
                            setEditServiceCocode(cocode);
                          }}
                          onTargetChange={(empno, target) => {
                            setEditServiceEmpno(empno);
                            if (target) {
                              setEditServiceTargetCocode(target.cocode);
                              setEditServiceDeptno(target.deptno);
                              setEditServiceEmpnamec(target.empnamec);
                            }
                          }}
                          serviceCompanies={serviceCompanies}
                          serviceTargets={serviceTargets}
                          required={false}
                        />
                      )}

                      {/* 執行時間選擇器 - 預設隱藏 */}
                      {!isFocusMode && (
                        <ExecutionTimeSelector
                          totalMinutes={editExecutionTimeMinutes}
                          onChange={(minutes) =>
                            setEditExecutionTimeMinutes(minutes)
                          }
                          required
                        />
                      )}

                      {/* 內容編輯器 - 永遠顯示 */}
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
                          docDate={selectedDate?.replace(/-/g, "") || undefined}
                        />
                      </div>

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
                          onClick={deleteDraft}
                          disabled={isDeletingDraft}
                          className="px-4 py-2 bg-red-500 text-white text-sm font-medium rounded-lg hover:bg-red-600 disabled:bg-gray-200 disabled:text-gray-400 order-2 inline-flex items-center justify-center"
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          {isDeletingDraft ? "刪除中..." : "刪除記錄"}
                        </button>
                        <button
                          onClick={cancelEdit}
                          className="px-4 py-2 bg-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-300 order-3"
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
                        <AttachedFilesDisplay files={report.files} content={report.content} />
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
                  {(() => {
                    const planno = report.project?.planno || "NULL";
                    const reportKey = `${report.daily_no}-${planno}-${report.sopno}`;
                    return generatingAiFor.has(reportKey);
                  })() ? (
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
              {(() => {
                const planno = report.project?.planno || "NULL";
                const recordKey = `${report.daily_no}-${planno}-${report.sopno}`;
                return editingRecordKey === recordKey &&
                  isAiViewActive &&
                  report.ai_content;
              })() && (
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
                  selectedWorkItemId={newRecord.work_item_ids?.map((id) => id.toString())}
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
                  onCompanyChange={(cocode, company) =>
                    setNewRecord((prev) => ({
                      ...prev,
                      service_cocode: cocode,
                    }))
                  }
                  onTargetChange={(empno, target) => {
                    setNewRecord((prev) => ({
                      ...prev,
                      service_empno: empno,
                      service_empnamec: target?.empnamec,
                      service_target_cocode: target?.cocode,
                      service_deptno: target?.deptno,
                    }));
                  }}
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
                    docDate={selectedDate?.replace(/-/g, "") || undefined}
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
