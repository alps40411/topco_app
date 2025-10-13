// frontend/src/components/DataInputTab.tsx

import React, { useState, useEffect, useCallback } from "react";
import { Save, FileText } from "lucide-react";
import type {
  ConsolidatedReport,
  WorkRecordCreate,
  FileForUpload,
} from "../App";
import { getProjectColors, blueButtonStyle } from "../utils/colorUtils";
import { useAuth } from "../hooks/useAuth";
import AttachedFilesDisplay from "./AttachedFilesDisplay";
import AttachedFilesManager from "./AttachedFilesManager";
import ExecutionTimeSelector from "./ExecutionTimeSelector";
import CascadingWorkSelector from "./CascadingWorkSelector";
import { getFullFileUrl } from "../utils/urlUtils";
import ServiceSelector, {
  ServiceCompany,
  ServiceTarget,
} from "./ServiceSelector";
import DateSelector from "./DateSelector";
import RichTextEditor from "./RichTextEditor";
import { toast } from "react-hot-toast";
import { formatMinutesToHours } from "../utils/timeUtils";
import { useDataSync } from "../hooks/useDataSync";
import { TypographyClasses } from "../styles/typography";
import { RecordsApi } from "../services/recordsApi";

interface DataInputTabProps {
  selectedDate: string | null;
  onDateChange: (date: string) => void;
}

const DataInputTab: React.FC<DataInputTabProps> = ({
  selectedDate,
  onDateChange,
}) => {
  const [consolidatedRecords, setConsolidatedRecords] = useState<
    ConsolidatedReport[]
  >([]);
  const [isLoading, setIsLoading] = useState(true);
  const [currentRecord, setCurrentRecord] = useState<any>({
    content: "",
    planno: undefined,
    plan_subj_c: undefined,
    sopno: undefined,
    sop_desc_c: undefined,
    work_item_seq: [], // 改為陣列支援多選
    work_item_name: undefined,
    service_cocode: undefined,
    service_empno: undefined,
    service_empnamec: undefined,
    service_target_cocode: undefined,
    service_deptno: undefined,
    files: [],
    execution_time_minutes: 0,
  });
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const { authFetch, user, writingStatus, refreshWritingStatus } = useAuth(); // ✅ 使用全域狀態
  const [isSaving, setIsSaving] = useState(false);
  const [serviceCompanies, setServiceCompanies] = useState<any[]>([]);
  const [serviceTargets, setServiceTargets] = useState<any[]>([]);
  const [hasWorkItems, setHasWorkItems] = useState<boolean>(true);
  // ✅ writingStatus 改用 AuthContext 的全域狀態

  // 資料同步hook
  const { immediateSync, batchSync } = useDataSync({ debounceMs: 200 });

  // ✅ 移除本地的 fetchWritingStatus，改用 AuthContext 的 refreshWritingStatus

  const fetchConsolidatedRecords = useCallback(
    async (docDate?: string) => {
      if (!authFetch) return;
      setIsLoading(true);
      try {
        const url = docDate
          ? `/api/records/consolidated/today?doc_date=${docDate}`
          : "/api/records/consolidated/today";
        const response = await authFetch(url);
        if (response.ok) {
          setConsolidatedRecords(await response.json());
        }
      } catch (error) {
        console.error("取得彙整筆記失敗:", error);
        toast.error("取得彙整筆記失敗");
      } finally {
        setIsLoading(false);
      }
    },
    [authFetch]
  );

  // ✅ 修復: 合併兩個 useEffect,移除函數依賴，避免重複 API 呼叫
  useEffect(() => {
    if (!authFetch) return;

    const docDate = selectedDate ? selectedDate.replace(/-/g, "") : undefined;

    // 直接內聯邏輯,避免依賴外部函數
    const loadData = async () => {
      setIsLoading(true);
      try {
        const url = docDate
          ? `/api/records/consolidated/today?doc_date=${docDate}`
          : "/api/records/consolidated/today";
        const response = await authFetch(url);
        if (response.ok) {
          setConsolidatedRecords(await response.json());
        }
      } catch (error) {
        console.error("取得彙整筆記失敗:", error);
        toast.error("取得彙整筆記失敗");
      } finally {
        setIsLoading(false);
      }
    };

    // ✅ 載入 writing status 使用全域 refreshWritingStatus
    if (refreshWritingStatus && docDate) {
      refreshWritingStatus(docDate);
    }

    loadData();
  }, [authFetch, selectedDate, refreshWritingStatus]); // ✅ 只依賴真正需要的變數

  // 處理日期變更
  const handleDateChange = (newDate: string) => {
    onDateChange(newDate);
  };

  const onSave = async () => {
    // 工作計畫現在為非必選項
    // if (!currentRecord.planno) {
    //   toast.error("請選擇工作計劃");
    //   return;
    // }
    if (!currentRecord.sopno) {
      toast.error("請選擇執行工作");
      return;
    }
    // 只有當該執行工作有工作項目時，才要求必須選擇工作項目
    if (
      hasWorkItems &&
      (!currentRecord.work_item_seq || currentRecord.work_item_seq.length === 0)
    ) {
      toast.error("請選擇工作項目");
      return;
    }
    // 服務公司和服務對象現在為非必填項目
    // if (!currentRecord.service_cocode) {
    //   toast.error('請選擇服務公司');
    //   return;
    // }
    // if (!currentRecord.service_empno) {
    //   toast.error('請選擇服務對象');
    //   return;
    // }
    if (
      !currentRecord.content?.trim() &&
      (!currentRecord.files || currentRecord.files.length === 0)
    ) {
      toast.error("請填寫內容或附加檔案");
      return;
    }
    if (
      !currentRecord.execution_time_minutes ||
      currentRecord.execution_time_minutes === 0
    ) {
      toast.error("請設定執行時間");
      return;
    }
    setIsSaving(true);
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
        const dailyNoResponse = await authFetch("/api/dates/next-daily-no");
        const { next_daily_no: newDailyNo } = await dailyNoResponse.json();
        daily_no = newDailyNo;
      }

      // 準備暫存數據
      const draftData = {
        daily_no,
        empno: user.employee.empno,
        cocode: user.employee.cocode || "001", // 預設公司代碼
        doc_date:
          selectedDate ||
          new Date().toISOString().slice(0, 10).replace(/-/g, ""), // YYYYMMDD
        draft_type: "TEMP",
        draft_content: {
          content: currentRecord.content || "",
          planno: currentRecord.planno,
          plan_subj_c: currentRecord.plan_subj_c,
          sopno: currentRecord.sopno,
          sop_desc_c: currentRecord.sop_desc_c,
          work_item_seq: currentRecord.work_item_seq || [],
          work_item_name: currentRecord.work_item_name,
          service_cocode: currentRecord.service_cocode,
          service_empno: currentRecord.service_empno,
          service_empnamec: currentRecord.service_empnamec,
          service_target_cocode: currentRecord.service_target_cocode,
          service_deptno: currentRecord.service_deptno,
          files: currentRecord.files || [],
          execution_time_minutes: currentRecord.execution_time_minutes || 0,
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

      // ✅ 使用批次同步重新獲取最新資料，確保顯示正確的整合狀態
      const docDate = selectedDate ? selectedDate.replace(/-/g, "") : undefined;
      await fetchConsolidatedRecords(docDate);
      if (refreshWritingStatus && docDate) {
        await refreshWritingStatus(docDate);
      }

      setCurrentRecord({
        content: "",
        planno: undefined,
        plan_subj_c: undefined,
        sopno: undefined,
        sop_desc_c: undefined,
        work_item_seq: [], // 重置為空陣列
        work_item_name: undefined,
        service_cocode: undefined,
        service_empno: undefined,
        service_empnamec: undefined,
        service_target_cocode: undefined,
        service_deptno: undefined,
        files: [],
        execution_time_minutes: 0,
      });
      toast.success("記錄儲存成功！");
    } catch (error) {
      console.error("儲存筆記時發生錯誤:", error);
      toast.error("儲存失敗，請稍後再試。");
    } finally {
      setIsSaving(false);
    }
  };

  // 處理來自 RichTextEditor 的檔案上傳回調
  const handleEditorFileUpload = useCallback((file: FileForUpload) => {
    const t0 = performance.now();
    console.log("[DataInputTab] handleEditorFileUpload 被呼叫:", file);

    setCurrentRecord((prev) => ({
      ...prev,
      files: [...(prev.files || []), file],
    }));

    const t1 = performance.now();
    console.log(
      `[DataInputTab] handleEditorFileUpload 執行時間: ${(t1 - t0).toFixed(
        2
      )}ms`
    );
  }, []);

  const handleAiSelectionChange = (fileUrl: string, isSelected: boolean) => {
    setCurrentRecord((prev) => ({
      ...prev,
      files: (prev.files || []).map((f) =>
        f.url === fileUrl ? { ...f, is_selected_for_ai: isSelected } : f
      ),
    }));
  };

  const handleRemoveFile = useCallback(
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

        // 1. 呼叫後端 API 刪除實體檔案
        await RecordsApi.deleteFile(yearMonth, filename, authFetch);

        // 2. 從 currentRecord 的 files 列表中移除該檔案
        setCurrentRecord((prev) => ({
          ...prev,
          files: (prev.files || []).filter((file) => file.url !== relativePath),
        }));

        // 3. 從 RichTextEditor 的內容中移除圖片
        setCurrentRecord((prev) => ({
          ...prev,
          content: (prev.content || "").replace(
            new RegExp(`<img[^>]*src="${fullUrl}"[^>]*>`, "g"),
            ""
          ),
        }));
      } catch (error) {
        console.error("刪除檔案時發生錯誤:", error);
        toast.error("檔案刪除失敗");
      }
    },
    [authFetch]
  );

  // 只有在完全沒有其他可填寫日期時才顯示禁用提示
  if (
    writingStatus &&
    !writingStatus.allowed &&
    selectedDate &&
    !writingStatus.has_other_writable_dates
  ) {
    return (
      <div className="flex flex-col lg:flex-row gap-6 p-4 sm:p-6">
        <div className="w-full">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="h-5 w-5 text-yellow-400"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-yellow-800">
                  無法填寫此日期的日報
                </h3>
                <p className="mt-1 text-sm text-yellow-700">
                  {writingStatus.message}
                </p>
                <p className="mt-2 text-sm text-yellow-700">
                  請等待隔天8:30後填寫新的日報。
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col lg:flex-row gap-6 p-4 sm:p-6">
      <div className="w-full lg:w-1/2">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 sm:p-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900 h-6 flex items-center">
              記錄新筆記
            </h2>
            <DateSelector
              selectedDate={selectedDate || ""}
              onDateChange={handleDateChange}
              className="mt-2 sm:mt-0"
            />
          </div>
          <div className="space-y-6">
            {/* 級聯工作選擇器 */}
            <CascadingWorkSelector
              selectedProjectId={currentRecord.planno}
              selectedExecutionWorkId={currentRecord.sopno}
              selectedWorkItemId={currentRecord.work_item_seq}
              onProjectChange={useCallback((planno) => {
                setCurrentRecord((prev) => ({
                  ...prev,
                  planno,
                  sopno: undefined,
                  work_item_seq: undefined,
                }));
              }, [])}
              onExecutionWorkChange={useCallback((sopno) => {
                setCurrentRecord((prev) => ({
                  ...prev,
                  sopno,
                  work_item_seq: undefined,
                }));
              }, [])}
              onWorkItemChange={useCallback((workItemSeq) => {
                setCurrentRecord((prev) => ({
                  ...prev,
                  work_item_seq: workItemSeq,
                }));
              }, [])}
              onWorkItemsAvailabilityChange={useCallback((hasItems) => {
                setHasWorkItems(hasItems);
              }, [])}
              onServiceDataLoaded={useCallback((companies, targets) => {
                setServiceCompanies(companies);
                setServiceTargets(targets);
              }, [])}
              required={false}
            />

            {/* 服務選擇器 */}
            <ServiceSelector
              selectedCompanyId={currentRecord.service_cocode}
              selectedTargetId={currentRecord.service_empno}
              onCompanyChange={(cocode, company) => {
                setCurrentRecord((prev) => ({
                  ...prev,
                  service_cocode: cocode,
                }));
              }}
              onTargetChange={(empno, target) => {
                setCurrentRecord((prev) => ({
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
              totalMinutes={currentRecord.execution_time_minutes || 0}
              onChange={(minutes) => {
                setCurrentRecord((prev) => ({
                  ...prev,
                  execution_time_minutes: minutes,
                }));
              }}
              required
            />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                內容
              </label>
              <RichTextEditor
                value={currentRecord.content || ""}
                onChange={(content) => {
                  setCurrentRecord((prev) => ({
                    ...prev,
                    content,
                  }));
                }}
                onFileUpload={handleEditorFileUpload}
                onFileRemove={handleRemoveFile}
                files={currentRecord.files || []}
                placeholder="記錄您的想法... (可直接貼上圖片或者附上檔案)"
                docDate={selectedDate?.replace(/-/g, "") || undefined}
              />
            </div>

            <AttachedFilesManager
              files={currentRecord.files || []}
              onRemoveFile={handleRemoveFile}
              onAiSelectionChange={handleAiSelectionChange}
              isUploading={isUploading}
              showUploadButton={false}
            />

            <button
              onClick={onSave}
              disabled={isUploading || isSaving}
              className={`w-full h-10 px-4 rounded-lg flex items-center justify-center ${blueButtonStyle} disabled:bg-gray-200 disabled:text-gray-400`}
            >
              <Save className="w-4 h-4 mr-2" />
              {isUploading
                ? "檔案處理中..."
                : isSaving
                ? "儲存中..."
                : "儲存筆記"}
            </button>
          </div>
        </div>
      </div>
      <div className="w-full lg:w-1/2">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 sm:p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6 h-6 flex items-center">
            今日彙整預覽 ({consolidatedRecords.length})
          </h2>
          <div className="space-y-4">
            {isLoading ? (
              <div className="text-center py-8 text-gray-500">載入中...</div>
            ) : consolidatedRecords.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>今天還沒有記錄，開始您的工作吧！</p>
              </div>
            ) : (
              consolidatedRecords.map((report) => (
                <div
                  key={report.project.id}
                  className="bg-gray-50 rounded-lg p-3 sm:p-4 border border-gray-100 space-y-3"
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between mb-2 space-y-2 sm:space-y-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="inline-flex items-center px-2 py-1 text-xs sm:text-base font-medium rounded-md bg-indigo-100 text-indigo-800">
                        {report.project.plan_subj_c}
                      </div>
                      {report.execution_work_name && (
                        <div className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-md bg-green-100 text-green-800">
                          {report.execution_work_name}
                        </div>
                      )}
                      {report.work_item_name && (
                        <div className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-md bg-purple-100 text-purple-800">
                          {report.work_item_name}
                        </div>
                      )}
                      {report.total_execution_time_minutes !== undefined &&
                        report.total_execution_time_minutes > 0 && (
                          <span className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded font-medium">
                            {formatMinutesToHours(
                              report.total_execution_time_minutes
                            )}
                          </span>
                        )}
                    </div>
                  </div>

                  <div
                    className={TypographyClasses.richTextDisplay}
                    dangerouslySetInnerHTML={{ __html: report.content }}
                  />
                  <AttachedFilesDisplay files={report.files} />
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
export default DataInputTab;
