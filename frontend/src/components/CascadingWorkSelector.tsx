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

  // 載入所有工作資料
  const fetchAllWorkData = useCallback(async () => {
    if (!user?.employee?.empno) {
      toast.error("無法獲取用戶員工號碼");
      return;
    }

    setIsLoading(true);
    try {
      const workData = await LegacyApi.getAllWorkData(user.employee.empno);
      console.log("=== API 返回資料 ===");
      console.log("workData:", workData);
      console.log("basic_execution_works:", workData.basic_execution_works);
      if (
        workData.basic_execution_works &&
        workData.basic_execution_works.length > 0
      ) {
        console.log("第一個執行工作:", workData.basic_execution_works[0]);
        console.log(
          "第一個執行工作的項目:",
          workData.basic_execution_works[0].work_items
        );
      }
      setWorkPlans(workData.work_plans || []);
      setBasicExecutionWorks(workData.basic_execution_works || []);
      setProjectExecutionWorks(workData.project_execution_works || {});

      // 將服務資料傳遞給父組件
      if (onServiceDataLoaded) {
        onServiceDataLoaded(
          workData.service_companies || [],
          workData.service_targets || []
        );
      }

      // 預設選擇基本工作事項（空字符串代表基本工作事項）
      if (!selectedProjectId) {
        onProjectChange("");
        setCurrentExecutionWorks(workData.basic_execution_works || []);

        // 預設選擇第一個執行工作
        if (
          workData.basic_execution_works &&
          workData.basic_execution_works.length > 0
        ) {
          const firstExecutionWork = workData.basic_execution_works[0];
          onExecutionWorkChange(firstExecutionWork.sopno);
          setCurrentWorkItems(firstExecutionWork.work_items || []);
        }
      }

      setIsInitialized(true);
    } catch (error) {
      console.error("無法獲取工作資料:", error);
      toast.error("載入工作資料失敗");
    } finally {
      setIsLoading(false);
    }
  }, [
    user?.employee?.empno,
    onServiceDataLoaded,
    onProjectChange,
    onExecutionWorkChange,
    selectedProjectId,
  ]);

  // 初始化載入所有工作資料（只執行一次）
  useEffect(() => {
    if (user?.employee?.empno) {
      fetchAllWorkData();
    }
  }, [user?.employee?.empno, fetchAllWorkData]);

  // 當選擇工作計畫時，切換對應的執行工作
  useEffect(() => {
    if (!isInitialized) return; // 等待初始化完成

    if (selectedProjectId === "" || selectedProjectId === undefined) {
      // 選擇基本工作事項
      setCurrentExecutionWorks(basicExecutionWorks);
      // 自動選擇第一個執行工作
      if (basicExecutionWorks.length > 0) {
        const firstExecutionWork = basicExecutionWorks[0];
        onExecutionWorkChange(firstExecutionWork.sopno);
        setCurrentWorkItems(firstExecutionWork.work_items || []);
      }
    } else {
      // 選擇特定工作計畫
      const executionWorks = projectExecutionWorks[selectedProjectId] || [];
      setCurrentExecutionWorks(executionWorks);
      // 自動選擇第一個執行工作
      if (executionWorks.length > 0) {
        const firstExecutionWork = executionWorks[0];
        onExecutionWorkChange(firstExecutionWork.sopno);
        setCurrentWorkItems(firstExecutionWork.work_items || []);
      }
    }
  }, [
    selectedProjectId,
    basicExecutionWorks,
    projectExecutionWorks,
    onExecutionWorkChange,
    isInitialized,
  ]);

  // 當選擇執行工作時，切換對應的工作項目
  useEffect(() => {
    console.log("=== 工作項目更新檢查 ===");
    console.log("selectedExecutionWorkId:", selectedExecutionWorkId);
    console.log("currentExecutionWorks.length:", currentExecutionWorks.length);
    console.log("currentExecutionWorks:", currentExecutionWorks);

    if (selectedExecutionWorkId && currentExecutionWorks.length > 0) {
      const selectedWork = currentExecutionWorks.find(
        (work) => String(work.sopno) === String(selectedExecutionWorkId)
      );
      console.log("找到的執行工作:", selectedWork);
      if (selectedWork) {
        console.log("工作項目:", selectedWork.work_items);
        setCurrentWorkItems(selectedWork.work_items || []);
      } else {
        console.log("未找到對應的執行工作");
        console.log("嘗試匹配的 sopno 類型:", typeof selectedExecutionWorkId);
        console.log(
          "currentExecutionWorks 中的 sopno 類型:",
          typeof currentExecutionWorks[0]?.sopno
        );
        setCurrentWorkItems([]);
      }
    } else {
      console.log("條件不滿足，清空工作項目");
      setCurrentWorkItems([]);
    }
  }, [selectedExecutionWorkId, currentExecutionWorks]);

  const handleProjectChange = (value: string) => {
    const planno = value === "" ? undefined : value;
    onProjectChange(planno);
    onExecutionWorkChange(undefined);
    onWorkItemChange([]);
    // 清空當前的工作項目狀態，讓 useEffect 重新設置
    setCurrentWorkItems([]);
  };

  const handleExecutionWorkChange = (value: string) => {
    const sopno = value || undefined;
    onExecutionWorkChange(sopno);
    // 不要在這裡清空工作項目，讓 useEffect 來處理
  };

  const handleWorkItemChange = (value: string[] | string) => {
    const workItemSeq = Array.isArray(value) ? value : value ? [value] : [];
    onWorkItemChange(workItemSeq);
  };

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
            disabled={isLoading || currentExecutionWorks.length === 0}
          >
            <option value="">
              {isLoading
                ? "載入中..."
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
            id: item.unique_id || `${selectedExecutionWorkId}_${item.seq}_${index}`, // 確保唯一性
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
                      ? item.unique_id || `${selectedExecutionWorkId}_${seq}_${currentWorkItems.findIndex(i => i.seq === seq)}`
                      : "";
                  })
                  .filter(Boolean)
              : []
          }
          onSelectionChange={(values) => {
            // 將唯一 id 轉換回原始的 seq 值
            const originalSeqs = values
              .map((uniqueId) => {
                const item = currentWorkItems.find(
                  (item, index) =>
                    (item.unique_id ||
                      `${selectedExecutionWorkId}_${item.seq}_${index}`) === uniqueId
                );
                return item?.seq;
              })
              .filter(Boolean);
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
