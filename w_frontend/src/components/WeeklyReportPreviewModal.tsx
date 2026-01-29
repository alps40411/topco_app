import React, { useEffect, useState, useCallback, useRef } from "react";
import { Upload } from "lucide-react";
import { WeeklyReportApi } from "../services/weeklyReportApi";
import { TypographyClasses } from "../styles/typography";
import { processHtmlImageUrls } from "../utils/urlUtils";
import OverdueARTable from "./OverdueARTable";
import RevenueTable from "./RevenueTable";
import { OverdueARData, RevenueData } from "../services/types";

// 週報筆記類型（與 WeeklyReportTab 中的 WeeklyNote 一致）
interface WeeklyNote {
  id: number;
  work_item_id: number;
  work_item_name: string;
  subject: string;
  content: string;
  files: Array<{
    name: string;
    type: string;
    size: number;
    url: string;
    file_path?: string;
  }>;
  ai_content?: string;
  weekly_no?: string;
  seq?: number;
}

interface WeeklyReportPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: () => void;
  isSubmitting: boolean;
  canSubmit: boolean;
  year: number;
  week: number;
  empno: string;
  empName?: string;
  deptName?: string;
  /** 當前頁面的草稿筆記列表 */
  notes: WeeklyNote[];
  authFetch: (url: string, options?: RequestInit) => Promise<Response>;
}

const WeeklyReportPreviewModal: React.FC<WeeklyReportPreviewModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isSubmitting,
  canSubmit,
  year,
  week,
  empno,
  empName,
  deptName,
  notes,
  authFetch,
}) => {
  const [revenueData, setRevenueData] = useState<RevenueData[]>([]);
  const [overdueARData, setOverdueARData] = useState<OverdueARData[]>([]);
  const [isLoadingTables, setIsLoadingTables] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const loadTableData = useCallback(async () => {
    if (!authFetch) return;

    setIsLoadingTables(true);
    try {
      const [revenueResult, overdueARResult] = await Promise.allSettled([
        WeeklyReportApi.getRevenue(year, week, authFetch, empno),
        WeeklyReportApi.getOverdueAR(year, week, authFetch, empno),
      ]);

      if (revenueResult.status === "fulfilled") {
        setRevenueData(revenueResult.value?.ResponseData || []);
      }

      if (overdueARResult.status === "fulfilled") {
        setOverdueARData(overdueARResult.value?.ResponseData || []);
      }
    } catch (error) {
      console.error("載入表格資料失敗:", error);
    } finally {
      setIsLoadingTables(false);
    }
  }, [year, week, empno, authFetch]);

  useEffect(() => {
    if (isOpen) {
      loadTableData();
      // 重置滾動位置到頂部
      if (scrollContainerRef.current) {
        scrollContainerRef.current.scrollTop = 0;
      }
    }
  }, [isOpen, loadTableData]);

  // 關閉 modal 時按 Escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen, onClose]);

  // 防止背景滾動
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const formattedEmpno = empno ? String(empno).padStart(5, "0") : "";

  return (
    <div className="fixed inset-0 z-50">
      {/* 背景遮罩 */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50"
        onClick={onClose}
      />

      {/* 主體 - 全螢幕可滾動，內容置中 */}
      <div ref={scrollContainerRef} className="relative w-full h-full bg-gray-50 overflow-y-auto">
        <div className="max-w-5xl mx-auto p-2 sm:p-4 md:p-6">
          {/* 標題列 */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl lg:text-2xl font-bold text-gray-900">
                {formattedEmpno} {empName} {year}年 第{week}週 週報
                <span className="ml-2 text-sm font-normal text-orange-600 bg-orange-100 px-2 py-0.5 rounded">
                  預覽
                </span>
              </h2>
              <div className="text-base text-gray-500">{deptName || ""}</div>
            </div>
          </div>

          {/* 營收達成率表格 */}
          <RevenueTable data={revenueData} isLoading={isLoadingTables} />

          {/* 逾期應收帳款表格 */}
          <OverdueARTable data={overdueARData} isLoading={isLoadingTables} />

          {/* 週報內容 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3 sm:p-4 md:p-6 mb-4 sm:mb-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-4 mb-3 sm:mb-4">
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 flex items-center">
                週報內容
              </h3>
            </div>

            {notes.length === 0 ? (
              <div className="text-gray-500 text-center py-8">尚無筆記內容</div>
            ) : (
              <div className="space-y-3 sm:space-y-4">
                {notes.map((note, index) => (
                  <div
                    key={note.id || index}
                    className="border border-gray-100 rounded-lg p-3 sm:p-4 min-w-0"
                  >
                    <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mb-2 sm:mb-3">
                      {/* 工作項目標籤 */}
                      {note.work_item_name && (
                        <div className="inline-flex items-center px-2 sm:px-3 py-1 text-sm sm:text-base font-medium rounded-md bg-indigo-100 text-indigo-800">
                          <span className="truncate max-w-[200px] sm:max-w-none">
                            {note.work_item_name}
                          </span>
                        </div>
                      )}
                      {/* 主旨標籤 */}
                      {note.subject && (
                        <div className="inline-flex items-center px-1.5 sm:px-2 py-0.5 sm:py-1 text-xs font-medium rounded-md bg-green-100 text-green-800">
                          <span className="truncate max-w-[200px] sm:max-w-none">
                            {note.subject}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* 內容 */}
                    <div
                      className={TypographyClasses.richTextDisplay}
                      dangerouslySetInnerHTML={{
                        __html: processHtmlImageUrls(note.content || ""),
                      }}
                    />

                    {/* 附件 */}
                    {note.files && note.files.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-100">
                        <span className="text-sm text-gray-500">附件：</span>
                        <div className="flex flex-wrap gap-2 mt-1">
                          {note.files.map((file, fileIndex) => (
                            <a
                              key={fileIndex}
                              href={file.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:underline text-sm"
                            >
                              {file.name}
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 底部按鈕區域 */}
          <div className="flex justify-center gap-4 py-6">
            <button
              onClick={onClose}
              className="px-6 py-2.5 text-sm font-medium rounded-lg border border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
            >
              關閉預覽
            </button>
            <button
              onClick={onSubmit}
              disabled={!canSubmit || isSubmitting}
              className="inline-flex items-center px-6 py-2.5 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              <Upload className="w-4 h-4 mr-2" />
              {isSubmitting ? "提交中..." : "確定送出"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WeeklyReportPreviewModal;
