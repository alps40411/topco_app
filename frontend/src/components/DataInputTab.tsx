// frontend/src/components/DataInputTab.tsx

import React, { useState, useEffect, useCallback } from "react";
import { Save, FileText } from "lucide-react";
import type {
  ConsolidatedReport,
  WorkRecordCreate,
  FileForUpload,
} from "../App";
import { getProjectColors, blueButtonStyle } from "../utils/colorUtils";
import { useAuth } from "../contexts/AuthContext";
import AttachedFilesDisplay from "./AttachedFilesDisplay";
import AttachedFilesManager from "./AttachedFilesManager";
import ExecutionTimeSelector from "./ExecutionTimeSelector";
import CascadingWorkSelector from "./CascadingWorkSelector";
import ServiceSelector from "./ServiceSelector";
import DateSelector from "./DateSelector";
import { toast } from "react-hot-toast";
import { formatMinutesToHours } from "../utils/timeUtils";

const DataInputTab: React.FC = () => {
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
    service_deptno: undefined,
    files: [],
    execution_time_minutes: 0,
  });
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const { authFetch, user } = useAuth();
  const [isSaving, setIsSaving] = useState(false);
  const [serviceCompanies, setServiceCompanies] = useState<any[]>([]);
  const [serviceTargets, setServiceTargets] = useState<any[]>([]);
  const [hasWorkItems, setHasWorkItems] = useState<boolean>(true);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  const fetchConsolidatedRecords = useCallback(async (docDate?: string) => {
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
  }, [authFetch]);

  // 初始化時載入今日資料
  useEffect(() => {
    if (authFetch && selectedDate === null) {
      fetchConsolidatedRecords(undefined);
    }
  }, [authFetch, fetchConsolidatedRecords]);

  // 當日期變更時載入指定日期的資料
  useEffect(() => {
    if (authFetch && selectedDate !== null) {
      fetchConsolidatedRecords(selectedDate || undefined);
    }
  }, [authFetch, selectedDate, fetchConsolidatedRecords]);

  // 處理日期變更
  const handleDateChange = (newDate: string) => {
    setSelectedDate(newDate);
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

      // 檢查今天是否已經有暫存記錄（後端會自動處理8:30-8:30邏輯）
      let daily_no;
      try {
        const existingDraftsResponse = await authFetch(
          `/api/drafts/${user.employee.empno}?draft_type=TEMP`
        );
        if (existingDraftsResponse.ok) {
          const existingDrafts = await existingDraftsResponse.json();
          if (existingDrafts.length > 0) {
            // 使用現有記錄的daily_no
            daily_no = existingDrafts[0].daily_no;
            console.log("✅ 使用現有的 daily_no:", daily_no);
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
        console.log("✅ 取得新的 daily_no:", daily_no);
      }

      // 準備暫存數據
      const draftData = {
        daily_no,
        empno: user.employee.empno,
        cocode: user.employee.cocode || "001", // 預設公司代碼
        doc_date: selectedDate || new Date().toISOString().slice(0, 10).replace(/-/g, ""), // YYYYMMDD
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

      await fetchConsolidatedRecords(); // Re-fetch consolidated records
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

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setIsUploading(true);
    const uploadPromises = Array.from(files).map(async (file) => {
      const formData = new FormData();
      formData.append("file", file);
      try {
        const response = await authFetch("/api/records/upload", {
          method: "POST",
          body: formData,
        });
        if (!response.ok) throw new Error(`檔案 ${file.name} 上傳失敗`);
        const uploadedFile = await response.json();
        const newFile: FileForUpload = {
          name: uploadedFile.name,
          type: uploadedFile.type,
          size: uploadedFile.size,
          url: uploadedFile.url,
          is_selected_for_ai: false,
        };
        setCurrentRecord((prev) => ({
          ...prev,
          files: [...(prev.files || []), newFile],
        }));
      } catch (error: any) {
        console.error(error);
        toast.error(error.message);
      }
    });
    await Promise.all(uploadPromises);
    setIsUploading(false);
  };

  const handleAiSelectionChange = (fileUrl: string, isSelected: boolean) => {
    setCurrentRecord((prev) => ({
      ...prev,
      files: (prev.files || []).map((f) =>
        f.url === fileUrl ? { ...f, is_selected_for_ai: isSelected } : f
      ),
    }));
  };

  const removeFile = (fileUrl: string) => {
    setCurrentRecord((prev) => ({
      ...prev,
      files: (prev.files || []).filter((file) => file.url !== fileUrl),
    }));
  };

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
              onCompanyChange={(cocode) => {
                setCurrentRecord((prev) => ({
                  ...prev,
                  service_cocode: cocode,
                }));
              }}
              onTargetChange={(empno) => {
                setCurrentRecord((prev) => ({
                  ...prev,
                  service_empno: empno,
                }));
              }}
              serviceCompanies={serviceCompanies}
              serviceTargets={serviceTargets}
              required={false}
            />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                內容
              </label>
              <textarea
                rows={4}
                placeholder="記錄您的想法..."
                value={currentRecord.content || ""}
                onChange={(e) => {
                  setCurrentRecord((prev) => ({
                    ...prev,
                    content: e.target.value,
                  }));
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

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

            <AttachedFilesManager
              files={currentRecord.files || []}
              onFileUpload={handleFileUpload}
              onRemoveFile={removeFile}
              onAiSelectionChange={handleAiSelectionChange}
              isUploading={isUploading}
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
                      <div
                        className={`inline-flex items-center px-2 py-1 text-xs sm:text-sm font-medium rounded-md ${
                          getProjectColors(report.project.plan_subj_c).tag
                        }`}
                      >
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

                  <p className="text-sm text-gray-700 whitespace-pre-wrap">
                    {report.content}
                  </p>
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
