// frontend/src/components/WeekSelector.tsx

import React, { useEffect, useLayoutEffect, useRef, useState, useMemo } from "react";
import { WeeklyReportApi } from "../services/weeklyReportApi";
import { useAuth } from "../hooks/useAuth";

interface WeekItem {
  year: number;
  weekly_no: number;
  startdate: string; // YYYYMMDD
  enddate: string;   // YYYYMMDD
}

interface WeekSelectorProps {
  selectedWeek: number;
  selectedYear: number;
  onChange: (year: number, week: number) => void;
  className?: string;
}

const DISPLAY_WEEKS_COUNT = 20;

const formatRange = (startdate: string, enddate: string) => {
  // YYYYMMDD → MM/DD ~ MM/DD
  if (!startdate || !enddate) return "";
  const fmt = (s: string) => `${s.substring(4, 6)}/${s.substring(6, 8)}`;
  return `${fmt(startdate)} ~ ${fmt(enddate)}`;
};

const WeekSelector: React.FC<WeekSelectorProps> = React.memo(
  ({ selectedWeek, selectedYear, onChange, className = "" }) => {
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const selectedWeekBtnRef = useRef<HTMLButtonElement>(null);
    const { authFetch } = useAuth();

    const [weeks, setWeeks] = useState<WeekItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    // 載入週次列表（一次 API 取得 20 週）
    useEffect(() => {
      if (!authFetch) return;
      let cancelled = false;

      WeeklyReportApi.getWeekList(authFetch, DISPLAY_WEEKS_COUNT)
        .then((data) => {
          if (!cancelled) {
            setWeeks(data.weeks);
            setIsLoading(false);
          }
        })
        .catch((err) => {
          console.error("WeekSelector 載入週次列表失敗:", err);
          if (!cancelled) setIsLoading(false);
        });

      return () => {
        cancelled = true;
      };
    }, [authFetch]);

    // 找出當前選中週次的日期範圍
    const selectedRangeText = useMemo(() => {
      const selected = weeks.find(
        (w) => w.year === selectedYear && w.weekly_no === selectedWeek
      );
      if (selected) return formatRange(selected.startdate, selected.enddate);
      return "";
    }, [weeks, selectedYear, selectedWeek]);

    // 初始化滾動位置 — 滾到最右邊（顯示當前週）
    const hasScrolledRef = useRef(false);
    useLayoutEffect(() => {
      if (scrollContainerRef.current && !hasScrolledRef.current && weeks.length > 0) {
        const container = scrollContainerRef.current;
        container.scrollLeft = container.scrollWidth - container.clientWidth;
        hasScrolledRef.current = true;
      }
    }, [weeks]);

    // 視窗大小變化時重新滾動到當前週（如果選中的是當前週）
    useEffect(() => {
      const handleResize = () => {
        if (!scrollContainerRef.current || weeks.length === 0) return;
        const lastWeek = weeks[weeks.length - 1];
        if (lastWeek && selectedYear === lastWeek.year && selectedWeek === lastWeek.weekly_no) {
          const container = scrollContainerRef.current;
          container.scrollLeft = container.scrollWidth - container.clientWidth;
        }
      };
      window.addEventListener("resize", handleResize);
      return () => window.removeEventListener("resize", handleResize);
    }, [weeks, selectedWeek, selectedYear]);

    if (isLoading || weeks.length === 0) {
      return (
        <div className={`w-full ${className}`}>
          <div className="w-full h-[76px] bg-white border border-gray-200 rounded-lg shadow-sm p-4 flex items-center justify-center text-gray-400">
            載入週次中...
          </div>
        </div>
      );
    }

    return (
      <div className={`w-full ${className}`}>
        <div className="w-full bg-white border border-gray-200 rounded-lg shadow-sm p-4">
          <div className="flex items-center gap-6">
            {/* 週次按鈕列表（可滾動） */}
            <div
              ref={scrollContainerRef}
              className="flex-1 overflow-x-auto scrollbar-hide"
              style={{ scrollBehavior: "smooth" }}
            >
              <div className="flex gap-3 min-w-max items-center pl-2 pr-1 min-h-[44px]">
                {weeks.map((w) => {
                  const isSelected =
                    w.year === selectedYear && w.weekly_no === selectedWeek;
                  return (
                    <button
                      key={`${w.year}-${w.weekly_no}`}
                      ref={isSelected ? selectedWeekBtnRef : null}
                      onClick={() => onChange(w.year, w.weekly_no)}
                      className={`
                      min-w-[36px] h-[36px] flex items-center justify-center rounded-full text-sm font-medium transition-all duration-300 ease-in-out
                      ${
                        isSelected
                          ? "bg-teal-500 text-white shadow-md scale-110 hover:bg-teal-600"
                          : "text-gray-400 hover:text-gray-700 hover:bg-gray-100"
                      }
                    `}
                      title={formatRange(w.startdate, w.enddate)}
                    >
                      {w.weekly_no}
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
                {selectedRangeText || "..."}
              </div>
            </div>
          </div>
        </div>

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
