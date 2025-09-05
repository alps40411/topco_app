// frontend/src/components/CascadingWorkSelector.tsx

import React, { useState, useEffect, useCallback } from "react";
import { ChevronDown } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "react-hot-toast";
import { LegacyApi } from "../services/legacyApi";
import InlineMultiSelect from "./InlineMultiSelect";

interface CascadingWorkSelectorProps {
  selectedProjectId?: string;
  selectedExecutionWorkId?: string;
  selectedWorkItemId?: string[];
  onProjectChange: (projectId?: string) => void;
  onExecutionWorkChange: (executionWorkId?: string) => void;
  onWorkItemChange: (workItemId?: string[]) => void;
  onServiceDataLoaded?: (
    serviceCompanies: Array<{ id: string; cocode: string; coabbv: string }>,
    serviceTargets: Array<{
      cocode: string;
      coabbv: string;
      deptno: string;
      deptabbv: string;
      empno: string;
      empnamec: string;
    }>
  ) => void;
  required?: boolean;
  className?: string;
}

const CascadingWorkSelector: React.FC<CascadingWorkSelectorProps> = ({
  selectedProjectId,
  selectedExecutionWorkId,
  selectedWorkItemId,
  onProjectChange,
  onExecutionWorkChange,
  onWorkItemChange,
  onServiceDataLoaded,
  required = false,
  className = "",
}) => {
  // ===== 狀態定義 (無變更) =====
  const [workPlans, setWorkPlans] = useState<
    Array<{ planno: string; plan_subj_c: string }>
  >([]);
  const [basicExecutionWorks, setBasicExecutionWorks] = useState<
    Array<{
      sopno: string;
      sop_desc_c: string;
      work_items: Array<{ seq: string; name: string }>;
    }>
  >([]);
  const [projectExecutionWorks, setProjectExecutionWorks] = useState<{
    [key: string]: Array<{
      sopno: string;
      sop_desc_c: string;
      work_items: Array<{ seq: string; name: string }>;
    }>;
  }>({});
  const [currentExecutionWorks, setCurrentExecutionWorks] = useState<
    Array<{
      sopno: string;
      sop_desc_c: string;
      work_items: Array<{ seq: string; name: string }>;
    }>
  >([]);
  const [currentWorkItems, setCurrentWorkItems] = useState<
    Array<{ seq: string; name: string; unique_id?: string }>
  >([]);

  const [isLoading, setIsLoading] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  const { user } = useAuth();

  // ===== 修改 #1: useEffect 用於初始化資料獲取 =====
  // 這個 Effect 只會在 user.employee.empno 存在且變更時執行一次。
  // 它負責獲取所有需要的資料，並設定初始狀態。
  useEffect(() => {
    const fetchAllWorkData = async () => {
      if (!user?.employee?.empno) {
        toast.error("無法獲取用戶員工號碼");
        return;
      }

      setIsLoading(true);
      try {
        const workData = await LegacyApi.getAllWorkData(user.employee.empno);
        console.log("=== API 已呼叫並返回資料 (只會執行一次) ===", workData);

        // 1. 設定從 API 獲取的原始資料
        setWorkPlans(workData.work_plans || []);
        const basicWorks = workData.basic_execution_works || [];
        setBasicExecutionWorks(basicWorks);
        setProjectExecutionWorks(workData.project_execution_works || {});

        // 2. 將服務資料傳遞給父組件
        if (onServiceDataLoaded) {
          onServiceDataLoaded(
            workData.service_companies || [],
            workData.service_targets || []
          );
        }

        // 3. 設定初始下拉選單的狀態
        // 如果外部沒有傳入 selectedProjectId，就預設為「基本工作事項」
        if (!selectedProjectId) {
          setCurrentExecutionWorks(basicWorks);
          if (basicWorks.length > 0) {
            const firstExecutionWork = basicWorks[0];
            onExecutionWorkChange(firstExecutionWork.sopno);
            // 注意：這裡的 setCurrentWorkItems 會被後面的 useEffect 覆蓋，是正常的
          }
        }

        setIsInitialized(true);
      } catch (error) {
        console.error("無法獲取工作資料:", error);
        toast.error("載入工作資料失敗");
      } finally {
        setIsLoading(false);
      }
    };

    if (user?.employee?.empno && !isInitialized) {
      fetchAllWorkData();
    }
  }, [
    user?.employee?.empno,
    onServiceDataLoaded,
    isInitialized,
    selectedProjectId,
    onExecutionWorkChange,
  ]);

  // ===== 修改 #2: 依賴 selectedProjectId 的 useEffect =====
  // 這個 Effect 現在只負責根據已有的資料，在「工作計畫」變更時，更新「執行工作」的列表。
  // 它不再需要關心 API 呼叫。
  useEffect(() => {
    if (!isInitialized) return; // 等待初始化資料載入完成

    let executionWorks: typeof basicExecutionWorks = [];

    if (selectedProjectId && projectExecutionWorks[selectedProjectId]) {
      // 選擇了某個工作計畫
      executionWorks = projectExecutionWorks[selectedProjectId];
    } else {
      // 選擇了「基本工作事項」(selectedProjectId 為 "" 或 undefined)
      executionWorks = basicExecutionWorks;
    }

    setCurrentExecutionWorks(executionWorks);

    // 當工作計畫改變時，自動選擇第一個執行工作，並清空工作項目
    if (executionWorks.length > 0) {
      const firstExecutionWork = executionWorks[0];
      onExecutionWorkChange(firstExecutionWork.sopno);
    } else {
      onExecutionWorkChange(undefined);
    }
    // 清空工作項目，讓下一個 effect 來處理
    onWorkItemChange([]);
  }, [
    selectedProjectId,
    basicExecutionWorks,
    projectExecutionWorks,
    onExecutionWorkChange,
    onWorkItemChange, // 新增依賴
    isInitialized,
  ]);

  // ===== 修改 #3: 依賴 selectedExecutionWorkId 的 useEffect =====
  // 這個 Effect 保持不變，它的邏輯是正確的。
  // 負責在「執行工作」變更時，更新「工作項目」的列表。
  useEffect(() => {
    if (!isInitialized) return;

    if (selectedExecutionWorkId) {
      const selectedWork = currentExecutionWorks.find(
        (work) => String(work.sopno) === String(selectedExecutionWorkId)
      );
      if (selectedWork) {
        setCurrentWorkItems(selectedWork.work_items || []);
      } else {
        setCurrentWorkItems([]);
      }
    } else {
      setCurrentWorkItems([]);
    }
  }, [selectedExecutionWorkId, currentExecutionWorks, isInitialized]);

  // ===== 事件處理函式 (Handlers) 調整 =====
  const handleProjectChange = (value: string) => {
    // 當工作計畫改變時，我們只需要呼叫 onProjectChange
    // 相關的狀態更新會由上面的 useEffect 自動處理
    onProjectChange(value === "" ? undefined : value);
  };

  const handleExecutionWorkChange = (value: string) => {
    // 同樣，只需要呼叫 onExecutionWorkChange
    onExecutionWorkChange(value || undefined);
  };

  const handleWorkItemChange = (value: string[] | string) => {
    const workItemSeq = Array.isArray(value) ? value : value ? [value] : [];
    onWorkItemChange(workItemSeq);
  };

  // ===== JSX (無變更) =====
  return (
    <div className={`space-y-4 ${className}`}>
      {/* 工作計畫選擇 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          工作計畫
        </label>
        <div className="relative">
          <select
            value={selectedProjectId || ""}
            onChange={(e) => handleProjectChange(e.target.value)}
            className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white"
            disabled={isLoading}
          >
            <option value="">基本工作事項</option>
            {workPlans.map((plan) => (
              <option key={plan.planno} value={plan.planno}>
                {plan.plan_subj_c}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-2.5 h-4 w-4 text-gray-400 pointer-events-none" />
        </div>
        {isLoading && (
          <div className="text-xs text-gray-500 mt-1">載入工作資料中...</div>
        )}
      </div>

      {/* 執行工作選擇 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          執行工作 {required && <span className="text-red-500">*</span>}
        </label>
        <div className="relative">
          <select
            value={selectedExecutionWorkId || ""}
            onChange={(e) => handleExecutionWorkChange(e.target.value)}
            className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white disabled:bg-gray-50 disabled:text-gray-500"
            disabled={
              isLoading || !isInitialized || currentExecutionWorks.length === 0
            }
          >
            <option value="">
              {isLoading
                ? "載入中..."
                : !isInitialized
                ? "等待資料載入..."
                : currentExecutionWorks.length === 0
                ? "暫無執行工作"
                : "請選擇執行工作"}
            </option>
            {currentExecutionWorks.map((work) => (
              <option key={work.sopno} value={work.sopno}>
                {work.sop_desc_c || work.sopno}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-2.5 h-4 w-4 text-gray-400 pointer-events-none" />
        </div>
      </div>

      {/* 工作項目選擇 - 內聯多選 */}
      {!selectedExecutionWorkId ? (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            工作項目 {required && <span className="text-red-500">*</span>}
          </label>
          <div className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500">
            請先選擇執行工作
          </div>
        </div>
      ) : (
        <InlineMultiSelect
          label="工作項目"
          options={currentWorkItems.map((item, index) => ({
            id:
              item.unique_id ||
              `${selectedExecutionWorkId}_${item.seq}_${index}`,
            name: item.name,
          }))}
          selectedValues={
            Array.isArray(selectedWorkItemId)
              ? selectedWorkItemId
                  .map((seq) => {
                    const item = currentWorkItems.find(
                      (item) => item.seq === seq
                    );
                    return item
                      ? item.unique_id ||
                          `${selectedExecutionWorkId}_${seq}_${currentWorkItems.findIndex(
                            (i) => i.seq === seq
                          )}`
                      : "";
                  })
                  .filter(Boolean)
              : []
          }
          onSelectionChange={(values) => {
            const originalSeqs = values
              .map((uniqueId) => {
                const item = currentWorkItems.find(
                  (item, index) =>
                    (item.unique_id ||
                      `${selectedExecutionWorkId}_${item.seq}_${index}`) ===
                    uniqueId
                );
                return item?.seq;
              })
              .filter((seq): seq is string => !!seq); // 確保類型正確
            handleWorkItemChange(originalSeqs);
          }}
          placeholder="暫無工作項目"
          required={required}
        />
      )}
    </div>
  );
};

export default CascadingWorkSelector;
