// frontend/src/components/WeekSelector.tsx

import React, { useMemo, useEffect, useLayoutEffect, useRef } from "react";
import {
  formatWeekRange,
  getCurrentWeek,
  getISOWeek,
  getISOWeekYear,
  getWeekStartDate,
} from "../utils/weekUtils";
import { addWeeks } from "date-fns";

interface WeekSelectorProps {
  selectedWeek: number;
  selectedYear: number;
  onChange: (year: number, week: number) => void;
  className?: string;
}

const WeekSelector: React.FC<WeekSelectorProps> = React.memo(
  ({ selectedWeek, selectedYear, onChange, className = "" }) => {
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const selectedWeekBtnRef = useRef<HTMLButtonElement>(null);

    // 獲取當前周次
    const { year: currentYear, week: currentWeek } = getCurrentWeek();

    // 獲取該年度的總週數（ISO 8601 標準）
    const getTotalWeeksInYear = (year: number): number => {
      const lastDayOfYear = new Date(year, 11, 31);
      const lastWeek = getISOWeek(lastDayOfYear);
      const yearOfLastWeek = getISOWeekYear(lastDayOfYear);

      // 如果 12/31 屬於下一年的第 1 周，該年實際周數更少
      if (yearOfLastWeek !== year) {
        const dec30 = new Date(year, 11, 30);
        return getISOWeek(dec30);
      }

      return lastWeek;
    };

    // 定義週次項目類型
    interface WeekItem {
      year: number;
      week: number;
    }

    // 固定顯示範圍：當前周往前推 N 周，當前周在最右邊
    const DISPLAY_WEEKS_COUNT = 20; // 顯示的周次數量

    const allWeeks = useMemo((): WeekItem[] => {
      const weeks: WeekItem[] = [];

      // 總是基於當前周顯示，從當前周往前推指定數量的周次
      // 當前周在最右邊
      for (let i = DISPLAY_WEEKS_COUNT - 1; i >= 0; i--) {
        const targetDate = addWeeks(
          getWeekStartDate(currentYear, currentWeek),
          -i
        );
        const weekYear = getISOWeekYear(targetDate);
        const weekNum = getISOWeek(targetDate);
        weeks.push({ year: weekYear, week: weekNum });
      }

      return weeks;
    }, [currentYear, currentWeek]);

    // 當前選中週次的日期範圍
    const selectedWeekRange = useMemo(() => {
      return formatWeekRange(selectedYear, selectedWeek);
    }, [selectedYear, selectedWeek]);

    // 只在初始載入時設置滾動位置（當前周在最右邊），之後保持不動
    const hasScrolledRef = useRef(false);

    useLayoutEffect(() => {
      if (scrollContainerRef.current && !hasScrolledRef.current) {
        const container = scrollContainerRef.current;
        // 初始載入時，滾動到最右邊（顯示當前周）
        container.scrollLeft = container.scrollWidth - container.clientWidth;
        hasScrolledRef.current = true;
      }
    }, [allWeeks]); // 只在周次列表變化時執行一次

    // 監聽窗口大小變化，重新調整滾動位置
    useEffect(() => {
      const handleResize = () => {
        if (
          scrollContainerRef.current &&
          selectedYear === currentYear &&
          selectedWeek === currentWeek
        ) {
          const container = scrollContainerRef.current;
          container.scrollLeft = container.scrollWidth - container.clientWidth;
        }
      };

      window.addEventListener("resize", handleResize);
      return () => window.removeEventListener("resize", handleResize);
    }, [selectedWeek, selectedYear, currentWeek, currentYear]);

    const handleWeekClick = (year: number, week: number) => {
      onChange(year, week);
    };

    return (
      <div className={`w-full ${className}`}>
        {/* 新設計：簡潔優雅的水平週次選擇器 */}
        <div className="w-full bg-white border border-gray-200 rounded-lg shadow-sm p-4">
          <div className="flex items-center gap-6">
            {/* 週次按鈕列表（可滾動） */}
            <div
              ref={scrollContainerRef}
              className="flex-1 overflow-x-auto scrollbar-hide"
              style={{ scrollBehavior: "smooth" }}
            >
              <div className="flex gap-3 min-w-max items-center pl-2 pr-1 min-h-[44px]">
                {allWeeks.map((weekItem) => {
                  const isSelected =
                    weekItem.year === selectedYear &&
                    weekItem.week === selectedWeek;

                  return (
                    <button
                      key={`${weekItem.year}-${weekItem.week}`}
                      ref={isSelected ? selectedWeekBtnRef : null}
                      onClick={() =>
                        handleWeekClick(weekItem.year, weekItem.week)
                      }
                      className={`
                      min-w-[36px] h-[36px] flex items-center justify-center rounded-full text-sm font-medium transition-all duration-300 ease-in-out
                      ${
                        isSelected
                          ? "bg-teal-500 text-white shadow-md scale-110 hover:bg-teal-600"
                          : "text-gray-400 hover:text-gray-700 hover:bg-gray-100"
                      }
                    `}
                      title={formatWeekRange(weekItem.year, weekItem.week)}
                    >
                      {weekItem.week}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 右側：年份和日期範圍 */}
            <div className="flex flex-col items-center w-[180px] border-l-2 border-gray-200 pl-6">
              <div className="text-2xl font-bold text-gray-800">
                {selectedYear}
              </div>
              <div className="text-xs text-gray-600 mt-1 whitespace-nowrap font-medium">
                {selectedWeekRange}
              </div>
            </div>
          </div>
        </div>

        {/* 添加自定義 CSS 來隱藏滾動條但保持滾動功能 */}
        <style>{`
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
        .scrollbar-hide {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
      `}</style>
      </div>
    );
  }
);

WeekSelector.displayName = "WeekSelector";

export default WeekSelector;
