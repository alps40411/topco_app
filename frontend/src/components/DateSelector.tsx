// frontend/src/components/DateSelector.tsx

import React, { useState, useEffect, useCallback } from "react";
import { Calendar, ChevronDown } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import toast from "react-hot-toast";

interface DateOption {
  value: string;
  display: string;
  date: string;
  is_weekday: boolean;
  is_today: boolean;
  is_default: boolean;
  can_write: boolean;
  status: string;
}

interface DateSelectorProps {
  selectedDate: string;
  onDateChange: (date: string) => void;
  className?: string;
  disabled?: boolean;
  onRefreshRef?: React.MutableRefObject<(() => Promise<void>) | null>;
  showOnlyWritableDates?: boolean; // 是否只顯示可填寫的日期
}

// 全局緩存日期數據
let globalDateCache: {
  data: DateOption[];
  currentReportDate: string;
  timestamp: number;
  isLoading?: boolean;
} | null = null;

const CACHE_DURATION = 5 * 60 * 1000; // 5分鐘緩存

// Export 清除快取函數，供登入頁面使用
export const clearDateCache = () => {
  console.log("🗑️ 清除日期快取");
  globalDateCache = null;
};

const DateSelector: React.FC<DateSelectorProps> = ({
  selectedDate,
  onDateChange,
  className = "",
  disabled = false,
  onRefreshRef,
  showOnlyWritableDates = true,
}) => {
  const [availableDates, setAvailableDates] = useState<DateOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [currentReportDate, setCurrentReportDate] = useState<string>("");
  const { authFetch } = useAuth();

  const fetchAvailableDates = useCallback(
    async (forceRefresh = false) => {
      if (!authFetch) return;

      // 檢查緩存是否有效（除非強制刷新）
      const now = Date.now();
      if (
        !forceRefresh &&
        globalDateCache &&
        now - globalDateCache.timestamp < CACHE_DURATION
      ) {
        console.log("使用緩存的日期數據");
        setAvailableDates(globalDateCache.data);
        setCurrentReportDate(globalDateCache.currentReportDate);

        // 如果沒有選擇日期，使用預設日期（後端已設定為最新的可填寫日期）
        if (!selectedDate && globalDateCache.currentReportDate) {
          onDateChange(globalDateCache.currentReportDate);
        }
        setIsLoading(false);
        return;
      }

      // 防止多個實例同時發起請求 - 檢查是否已有請求正在進行
      if (!forceRefresh && globalDateCache?.isLoading) {
        console.log("等待其他實例的請求完成");
        // 等待一小段時間後重新檢查快取
        setTimeout(() => {
          if (globalDateCache && !globalDateCache.isLoading) {
            setAvailableDates(globalDateCache.data);
            setCurrentReportDate(globalDateCache.currentReportDate);
            if (!selectedDate && globalDateCache.currentReportDate) {
              onDateChange(globalDateCache.currentReportDate);
            }
            setIsLoading(false);
          }
        }, 100);
        return;
      }

      try {
        setIsLoading(true);

        // 標記正在載入，防止其他實例重複請求
        if (globalDateCache) {
          globalDateCache.isLoading = true;
        } else {
          globalDateCache = { isLoading: true } as any;
        }

        const response = await authFetch("/api/legacy/daily-date-range");

        if (response.ok) {
          const data = await response.json();
          const dateData = data.data || [];
          const currentDate = data.current_report_date || "";

          // 更新全局緩存
          globalDateCache = {
            data: dateData,
            currentReportDate: currentDate,
            timestamp: now,
            isLoading: false,
          };

          setAvailableDates(dateData);
          setCurrentReportDate(currentDate);

          // 強制刷新或沒有選擇日期時，使用預設日期
          if ((forceRefresh || !selectedDate) && currentDate) {
            onDateChange(currentDate);
          }
        } else {
          throw new Error("取得日期範圍失敗");
        }
      } catch (error) {
        console.error("獲取可用日期失敗:", error);
        toast.error("載入日期選項失敗");

        // 清除載入狀態
        if (globalDateCache) {
          globalDateCache.isLoading = false;
        }

        // 失敗時使用當前日期作為備選
        const today = new Date();
        const todayStr = today.toISOString().slice(0, 10).replace(/-/g, "");
        if (!selectedDate) {
          onDateChange(todayStr);
        }
      } finally {
        setIsLoading(false);
      }
    },
    [authFetch, selectedDate, onDateChange]
  );

  // 提供刷新函數給父組件
  useEffect(() => {
    if (onRefreshRef) {
      onRefreshRef.current = () => fetchAvailableDates(true);
    }
  }, [fetchAvailableDates, onRefreshRef]);

  useEffect(() => {
    fetchAvailableDates();
  }, [fetchAvailableDates]);

  const handleDateChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const newDate = event.target.value;
    onDateChange(newDate);

    // 顯示選擇的日期信息
    const selectedOption = availableDates.find(
      (date) => date.value === newDate
    );
    if (selectedOption) {
      if (selectedOption.is_today) {
        toast.success(`已選擇今日日報 (${selectedOption.display})`);
      } else {
        toast.success(`已切換至 ${selectedOption.display} 的日報`);
      }
    }
  };


  if (isLoading) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <Calendar className="w-4 h-4 text-gray-400" />
        <div className="animate-pulse bg-gray-200 h-8 w-32 rounded"></div>
      </div>
    );
  }

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <Calendar className="w-4 h-4 text-gray-600" />
      <div className="relative">
        <select
          value={selectedDate}
          onChange={handleDateChange}
          disabled={disabled}
          className="appearance-none bg-white border border-gray-300 rounded-lg px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed min-w-[160px]"
        >
          {availableDates
            .filter((dateOption) =>
              showOnlyWritableDates ? dateOption.can_write : true
            ) // 根據設定過濾日期
            .map((dateOption) => (
              <option
                key={dateOption.value}
                value={dateOption.value}
                className={
                  dateOption.is_today
                    ? "font-semibold"
                    : !dateOption.is_weekday
                    ? "text-gray-500"
                    : ""
                }
              >
                {dateOption.display}
              </option>
            ))}
        </select>
        <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
      </div>

      {/* 日期信息提示 */}
      {selectedDate && (
        <div className="hidden sm:block text-xs text-gray-500">
          {(() => {
            const selectedOption = availableDates.find(
              (date) => date.value === selectedDate
            );
            if (!selectedOption) return "";

            if (selectedOption.is_today) {
              return "當前日報";
            } else if (selectedOption.value === currentReportDate) {
              return "預設日期";
            } else if (!selectedOption.is_weekday) {
              return "假日補報";
            } else {
              return "補報/預報";
            }
          })()}
        </div>
      )}
    </div>
  );
};

export default DateSelector;
