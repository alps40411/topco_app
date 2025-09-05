// frontend/src/components/DailyReportTab.tsx

import React, { useState, useEffect } from "react";
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
import {
  getProjectColors,
  blueButtonStyle,
  greenButtonStyle,
} from "../utils/colorUtils";
import { useAuth } from "../contexts/AuthContext";
import AttachedFilesManager from "./AttachedFilesManager";
import AttachedFilesDisplay from "./AttachedFilesDisplay";
import ExecutionTimeSelector from "./ExecutionTimeSelector";
import CascadingWorkSelector from "./CascadingWorkSelector";
import ServiceSelector from "./ServiceSelector";
import { toast } from "react-hot-toast";
import { formatMinutesToHours } from "../utils/timeUtils";

interface WritingStatus {
  allowed: boolean;
  message: string;
  current_time: string;
}

const DailyReportTab: React.FC = () => {
  const [reports, setReports] = useState<ConsolidatedReport[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [writingStatus, setWritingStatus] = useState<WritingStatus | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingProjectId, setEditingProjectId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState<string>("");
  const [editFiles, setEditFiles] = useState<FileForUpload[]>([]);
  const { authFetch, user } = useAuth();

  const [isAiViewActive, setIsAiViewActive] = useState(false);
  const [isGeneratingAllAi, setIsGeneratingAllAi] = useState(false);
  const [generatingAiFor, setGeneratingAiFor] = useState<number | null>(null);

  // --- Modal and New Record State ---
  const [isAddNoteModalOpen, setIsAddNoteModalOpen] = useState(false);
  const [newRecord, setNewRecord] = useState<Partial<WorkRecordCreate>>({
    content: "",
    project_id: undefined,
    execution_work_id: undefined,
    work_item_id: undefined,
    service_company_id: undefined,
    service_target_id: undefined,
    files: [],
    execution_time_minutes: 0,
  });
  const [isSavingNewRecord, setIsSavingNewRecord] = useState(false);
  const [isUploadingNewFile, setIsUploadingNewFile] = useState(false);

  const fetchReports = async () => {
    if (!authFetch) return;
    setIsLoading(true);
    try {
      const response = await authFetch("/api/records/consolidated/today");
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

  const fetchWritingStatus = async () => {
    if (!authFetch) return;
    try {
      const response = await authFetch("/api/records/writing-status");
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

  useEffect(() => {
    if (authFetch) {
      fetchReports();
      fetchProjects();
      fetchWritingStatus();
    }
  }, [authFetch]);

  const handleEnhanceOne = async (projectId: number) => {
    if (!authFetch || !user?.employee?.empno) return;
    setGeneratingAiFor(projectId);
    try {
      // 找到對應的報告
      const report = reports.find((r) => r.project.id === projectId);
      if (!report) {
        throw new Error("找不到對應的報告");
      }

      // 生成唯一的 daily_no
      // 使用新的 AI 潤飾 API - 直接更新 tdr_draft 表
      const response = await authFetch(
        `/api/records/ai/enhance_one/${projectId}`,
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

      // 更新報告內容
      setReports((prev) =>
        prev.map((r) =>
          r.project.id === projectId
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
      setGeneratingAiFor(null);
    }
  };

  const handleEnhanceAll = async () => {
    if (!authFetch) return;
    setIsGeneratingAllAi(true);
    try {
      const response = await authFetch("/api/records/ai/enhance_all", {
        method: "POST",
      });
      if (response.ok) {
        const enhancedReports = await response.json();
        setReports(enhancedReports);
        setIsAiViewActive(true);
        toast.success("所有報告皆已完成 AI 潤飾！");
      } else {
        throw new Error("AI 服務失敗");
      }
    } catch (error: any) {
      console.error(error);
      toast.error(error.message);
    } finally {
      setIsGeneratingAllAi(false);
    }
  };

  const startEdit = (report: ConsolidatedReport) => {
    setEditingProjectId(report.project.id);
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
    setEditingProjectId(null);
    setEditContent("");
    setEditFiles([]);
  };

  const saveEdit = async () => {
    if (editingProjectId === null || !authFetch) return;
    setIsSaving(true);
    try {
      const reportToUpdate = reports.find(
        (r) => r.project.id === editingProjectId
      );
      if (!reportToUpdate) throw new Error("找不到原始報告");

      const response = await authFetch(
        `/api/records/consolidated/${editingProjectId}`,
        {
          method: "PUT",
          body: JSON.stringify({
            ...reportToUpdate,
            content: editContent,
            files: editFiles,
          }),
        }
      );

      if (!response.ok) throw new Error("更新報告失敗");

      setReports((prevReports) =>
        prevReports.map((r) =>
          r.project.id === editingProjectId
            ? {
                ...r,
                content: editContent,
                files: editFiles as FileAttachment[],
              }
            : r
        )
      );
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
    if (!window.confirm("確定要提交此版本作為今日的最終日報嗎？")) return;

    setIsSubmitting(true);
    try {
      const response = await authFetch("/api/legacy/upload-daily-report", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });
      if (!response.ok) {
        const errData = await response
          .json()
          .catch(() => ({ detail: "提交失敗" }));
        throw new Error(errData.detail);
      }
      const result = await response.json();
      toast.success(`日報已成功上傳！日報編號: ${result.daily_no}`);
      await fetchReports();
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
  const removeEditFile = (fileUrl: string) => {
    setEditFiles((prev) => prev.filter((file) => file.url !== fileUrl));
  };

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
  const removeNewRecordFile = (fileUrl: string) => {
    setNewRecord((prev) => ({
      ...prev,
      files: (prev.files || []).filter((file) => file.url !== fileUrl),
    }));
  };

  const handleSaveNewRecord = async () => {
    if (!authFetch) return;
    if (!newRecord.project_id) {
      toast.error("請選擇工作計劃");
      return;
    }
    if (!newRecord.execution_work_id) {
      toast.error("請選擇執行工作");
      return;
    }
    if (!newRecord.work_item_id) {
      toast.error("請選擇工作項目");
      return;
    }
    if (!newRecord.service_company_id) {
      toast.error("請選擇服務公司");
      return;
    }
    if (!newRecord.service_target_id) {
      toast.error("請選擇服務對象");
      return;
    }
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
      const response = await authFetch("/api/records/", {
        method: "POST",
        body: JSON.stringify({
          project_id: newRecord.project_id,
          execution_work_id: newRecord.execution_work_id,
          work_item_id: newRecord.work_item_id,
          service_company_id: newRecord.service_company_id,
          service_target_id: newRecord.service_target_id,
          content: newRecord.content,
          files: newRecord.files || [],
          execution_time_minutes: newRecord.execution_time_minutes,
        }),
      });
      if (!response.ok) throw new Error("儲存新筆記失敗");
      toast.success("新筆記儲存成功！");
      setNewRecord({
        content: "",
        project_id: undefined,
        execution_work_id: undefined,
        work_item_id: undefined,
        service_company_id: undefined,
        service_target_id: undefined,
        files: [],
        execution_time_minutes: 0,
      });
      setIsAddNoteModalOpen(false);
      await fetchReports();
    } catch (error: any) {
      console.error("儲存新筆記時發生錯誤:", error);
      toast.error(error.message);
    } finally {
      setIsSavingNewRecord(false);
    }
  };

  const handleApplyAiSuggestion = (aiContent: string) => {
    // Convert HTML line breaks to plain text newlines for the textarea
    const plainTextContent = aiContent.replace(/<br \/>/g, "\n");
    setEditContent(plainTextContent);
    toast.success("AI 建議已套用至編輯框！");
  };

  if (isLoading) {
    return <div className="p-6 text-center">載入中...</div>;
  }

  return (
    <>
      <div className="p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between mb-4 sm:mb-6 space-y-4 lg:space-y-0">
          <div>
            <h2 className="text-xl sm:text-2xl font-bold text-gray-900 h-6 sm:h-8 flex items-center">
              日報編輯
            </h2>
            {writingStatus && (
              <div className="flex flex-col sm:flex-row sm:items-center mt-1 text-sm text-gray-600">
                <span className="mr-0 sm:mr-2">
                  🕐 {writingStatus.current_time}
                </span>
                <span className="text-blue-600">{writingStatus.message}</span>
              </div>
            )}
          </div>
          <div className="flex flex-row items-center gap-3">
            <button
              onClick={() => setIsAddNoteModalOpen(true)}
              disabled={editingProjectId !== null || generatingAiFor !== null}
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
                editingProjectId !== null ||
                generatingAiFor !== null
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
              disabled={isSubmitting || editingProjectId !== null}
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
                        className={`inline-flex items-center px-3 py-1 text-sm font-medium rounded-md ${
                          getProjectColors(report.project.plan_subj_c).tag
                        }`}
                      >
                        {report.project.plan_subj_c}
                      </div>
                      {report.total_execution_time_minutes !== undefined &&
                        report.total_execution_time_minutes > 0 && (
                          <span className="text-sm text-blue-600 bg-blue-50 px-2 py-1 rounded font-medium">
                            {formatMinutesToHours(
                              report.total_execution_time_minutes
                            )}
                          </span>
                        )}
                    </div>
                    {editingProjectId !== report.project.id && (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleEnhanceOne(report.project.id)}
                          disabled={
                            generatingAiFor !== null ||
                            isGeneratingAllAi ||
                            editingProjectId !== null
                          }
                          className="inline-flex items-center justify-center px-3 py-2 text-xs sm:text-sm font-medium rounded-lg bg-gradient-to-r from-purple-100 to-blue-100 text-purple-700 hover:from-purple-200 hover:to-blue-200 transition-all duration-200 border border-purple-200 disabled:from-gray-100 disabled:to-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed disabled:border-gray-300"
                        >
                          {generatingAiFor === report.project.id ? (
                            <div className="w-4 h-4 border-2 border-transparent border-t-purple-500 rounded-full animate-spin mr-2"></div>
                          ) : (
                            <Wand2 className="w-4 h-4 mr-2" />
                          )}
                          <span className="whitespace-nowrap">潤飾</span>
                        </button>
                        <button
                          onClick={() => startEdit(report)}
                          disabled={
                            generatingAiFor !== null || isGeneratingAllAi
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
                  {editingProjectId === report.project.id ? (
                    <div className="space-y-4">
                      <textarea
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        className="w-full min-h-[200px] p-4 border rounded-lg"
                      />
                      <AttachedFilesManager
                        files={editFiles}
                        onFileUpload={handleEditFileUpload}
                        onRemoveFile={removeEditFile}
                        onAiSelectionChange={handleEditAiSelectionChange}
                        isUploading={false}
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
                        <p className="prose max-w-none text-gray-700 whitespace-pre-wrap">
                          {report.content}
                        </p>
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
                  {generatingAiFor === report.project.id ? (
                    <p className="text-sm text-gray-500 italic">
                      AI 正在為此專案生成潤飾內容...
                    </p>
                  ) : report.ai_content ? (
                    <div className="prose max-w-none text-gray-700 whitespace-pre-wrap">
                      <div
                        dangerouslySetInnerHTML={{
                          __html: report.ai_content.replace(/\n/g, "<br />"),
                        }}
                      />
                    </div>
                  ) : (
                    <p className="text-sm text-gray-400 italic">
                      此專案無 AI 潤飾內容。點擊魔法棒按鈕開始生成。
                    </p>
                  )}
                </div>
              )}

              {/* --- Apply AI Suggestion Button (FINAL - Corrected Position) --- */}
              {editingProjectId === report.project.id &&
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
                  onClick={() => setIsAddNoteModalOpen(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              <div className="space-y-4 sm:space-y-6">
                {/* 級聯工作選擇器 */}
                <CascadingWorkSelector
                  selectedProjectId={newRecord.project_id}
                  selectedExecutionWorkId={newRecord.execution_work_id}
                  selectedWorkItemId={newRecord.work_item_id}
                  onProjectChange={(projectId) =>
                    setNewRecord({
                      ...newRecord,
                      project_id: projectId,
                      execution_work_id: undefined,
                      work_item_id: undefined,
                    })
                  }
                  onExecutionWorkChange={(executionWorkId) =>
                    setNewRecord({
                      ...newRecord,
                      execution_work_id: executionWorkId,
                      work_item_id: undefined,
                    })
                  }
                  onWorkItemChange={(workItemId) =>
                    setNewRecord({
                      ...newRecord,
                      work_item_id: workItemId,
                    })
                  }
                  required
                />

                {/* 服務選擇器 */}
                <ServiceSelector
                  selectedCompanyId={newRecord.service_company_id}
                  selectedTargetId={newRecord.service_target_id}
                  onCompanyChange={(companyId) =>
                    setNewRecord({
                      ...newRecord,
                      service_company_id: companyId,
                    })
                  }
                  onTargetChange={(targetId) =>
                    setNewRecord({
                      ...newRecord,
                      service_target_id: targetId,
                    })
                  }
                  required
                />
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    內容
                  </label>
                  <textarea
                    rows={5}
                    placeholder="記錄您的想法..."
                    value={newRecord.content || ""}
                    onChange={(e) =>
                      setNewRecord({ ...newRecord, content: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <ExecutionTimeSelector
                  totalMinutes={newRecord.execution_time_minutes || 0}
                  onChange={(minutes) =>
                    setNewRecord({
                      ...newRecord,
                      execution_time_minutes: minutes,
                    })
                  }
                  required
                />

                <AttachedFilesManager
                  files={newRecord.files || []}
                  onFileUpload={handleNewRecordUpload}
                  onRemoveFile={removeNewRecordFile}
                  onAiSelectionChange={handleNewRecordAiSelectionChange}
                  isUploading={isUploadingNewFile}
                />

                <div className="flex flex-col sm:flex-row justify-end space-y-2 sm:space-y-0 sm:space-x-4">
                  <button
                    onClick={() => setIsAddNoteModalOpen(false)}
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
