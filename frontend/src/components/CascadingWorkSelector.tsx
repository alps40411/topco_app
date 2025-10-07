// frontend/src/components/CascadingWorkSelector.tsx

import React, { useState, useEffect, useCallback } from "react";
import { ChevronDown } from "lucide-react";
import { useWorkData } from "../hooks/useWorkData";
import InlineMultiSelect from "./InlineMultiSelect";

interface CascadingWorkSelectorProps {
  selectedProjectId?: string;
  selectedExecutionWorkId?: string;
  selectedWorkItemId?: string[];
  onProjectChange: (projectId?: string) => void;
  onExecutionWorkChange: (executionWorkId?: string) => void;
  onWorkItemChange: (workItemId?: string[]) => void;
  onWorkItemsAvailabilityChange?: (hasItems: boolean) => void;
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
  onWorkItemsAvailabilityChange,
  onServiceDataLoaded,
  required = false,
  className = "",
}) => {
  // ✅ 使用 WorkDataContext 取代本地狀態和 API 呼叫
  const { workData, isLoading } = useWorkData();

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

  // ✅ 修改: 使用 Context 資料初始化
  useEffect(() => {
    if (!workData) return;

    // 將服務資料傳遞給父組件
    if (onServiceDataLoaded) {
      onServiceDataLoaded(
        workData.service_companies || [],
        workData.service_targets || []
      );
    }

    // 設定初始下拉選單的狀態
    if (!selectedProjectId) {
      const basicWorks = workData.basic_execution_works || [];
      setCurrentExecutionWorks(basicWorks);
      if (basicWorks.length > 0) {
        const firstExecutionWork = basicWorks[0];
        onExecutionWorkChange(firstExecutionWork.sopno);
      }
    }
  }, [workData]);

  // ✅ 修改: 依賴 selectedProjectId 的 useEffect
  useEffect(() => {
    if (!workData) return;

    let executionWorks: Array<{
      sopno: string;
      sop_desc_c: string;
      work_items: Array<{ seq: string; name: string }>;
    }> = [];

    if (selectedProjectId && workData.project_execution_works[selectedProjectId]) {
      executionWorks = workData.project_execution_works[selectedProjectId];
    } else {
      executionWorks = workData.basic_execution_works || [];
    }

    setCurrentExecutionWorks(executionWorks);

    if (executionWorks.length > 0 && !selectedExecutionWorkId) {
      const firstExecutionWork = executionWorks[0];
      onExecutionWorkChange(firstExecutionWork.sopno);
    } else if (executionWorks.length === 0) {
      onExecutionWorkChange(undefined);
    }

    if (!selectedExecutionWorkId) {
      onWorkItemChange([]);
    }
  }, [selectedProjectId, selectedExecutionWorkId, workData]);

  // ✅ 修改: 依賴 selectedExecutionWorkId 的 useEffect
  useEffect(() => {
    if (!workData) return;

    if (selectedExecutionWorkId) {
      const selectedWork = currentExecutionWorks.find(
        (work) => String(work.sopno) === String(selectedExecutionWorkId)
      );
      if (selectedWork) {
        const workItems = selectedWork.work_items || [];
        setCurrentWorkItems(workItems);
        if (onWorkItemsAvailabilityChange) {
          onWorkItemsAvailabilityChange(workItems.length > 0);
        }
      } else {
        setCurrentWorkItems([]);
        if (onWorkItemsAvailabilityChange) {
          onWorkItemsAvailabilityChange(false);
        }
      }
    } else {
      setCurrentWorkItems([]);
      if (onWorkItemsAvailabilityChange) {
        onWorkItemsAvailabilityChange(false);
      }
    }
  }, [selectedExecutionWorkId, currentExecutionWorks, workData]);

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
            disabled={isLoading || !workData}
          >
            <option value="">基本工作事項</option>
            {(workData?.work_plans || []).map((plan) => (
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
              isLoading || !workData || currentExecutionWorks.length === 0
            }
          >
            <option value="">
              {isLoading
                ? "載入中..."
                : !workData
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
          placeholder={
            currentWorkItems.length === 0
              ? "此執行工作無工作項目"
              : "暫無工作項目"
          }
          required={required && currentWorkItems.length > 0}
        />
      )}
    </div>
  );
};

export default CascadingWorkSelector;
