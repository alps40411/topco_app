import React, { useEffect, useRef } from "react";
import { Upload } from "lucide-react";
import { TypographyClasses } from "../styles/typography";
import AttachedFilesDisplay from "./AttachedFilesDisplay";
import { formatMinutesToHours } from "../utils/timeUtils";
import type { ConsolidatedReport } from "../App";

interface DailyReportPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: () => void;
  isSubmitting: boolean;
  canSubmit: boolean;
  selectedDate: string;
  empno: string;
  empName?: string;
  deptName?: string;
  /** 當前頁面的草稿記錄列表 */
  reports: ConsolidatedReport[];
}

const DailyReportPreviewModal: React.FC<DailyReportPreviewModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isSubmitting,
  canSubmit,
  selectedDate,
  empno,
  empName,
  deptName,
  reports,
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

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

  // 防止背景滾動 + 重置滾動位置
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
      // 重置滾動位置到頂部
      if (scrollContainerRef.current) {
        scrollContainerRef.current.scrollTop = 0;
      }
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const formattedEmpno = empno ? String(empno).padStart(5, "0") : "";

  // 格式化日期顯示 (YYYYMMDD -> YYYY年MM月DD日)
  const formatDateDisplay = (dateStr: string) => {
    if (!dateStr || dateStr.length !== 8) return dateStr;
    const year = dateStr.substring(0, 4);
    const month = dateStr.substring(4, 6);
    const day = dateStr.substring(6, 8);
    return `${year}年${month}月${day}日`;
  };

  // 計算總執行時間
  const totalExecutionTime = reports.reduce(
    (total, report) => total + (report.total_execution_time_minutes || 0),
    0
  );

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
                {formattedEmpno} {empName} {formatDateDisplay(selectedDate)} 日報
                <span className="ml-2 text-sm font-normal text-orange-600 bg-orange-100 px-2 py-0.5 rounded">
                  預覽
                </span>
              </h2>
              <div className="text-base text-gray-500">{deptName || ""}</div>
            </div>
          </div>

          {/* 日報內容 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3 sm:p-4 md:p-6 mb-4 sm:mb-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-4 mb-3 sm:mb-4">
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 flex items-center">
                日報內容
              </h3>
              {totalExecutionTime > 0 ? (
                <span className="text-xs sm:text-sm text-green-600 bg-green-50 px-2 sm:px-3 py-1 rounded-full font-medium border border-green-200 w-fit">
                  總執行時間: {formatMinutesToHours(totalExecutionTime)}
                </span>
              ) : (
                <span className="text-xs sm:text-sm text-gray-500 bg-gray-50 px-2 sm:px-3 py-1 rounded-full font-medium border border-gray-200 w-fit">
                  總執行時間: 0 小時
                </span>
              )}
            </div>

            {reports.length === 0 ? (
              <div className="text-gray-500 text-center py-8">尚無日報內容</div>
            ) : (
              <div className="space-y-3 sm:space-y-4">
                {reports.map((report, index) => (
                  <div
                    key={`${report.daily_no}-${report.sopno}-${index}`}
                    className="border border-gray-100 rounded-lg p-3 sm:p-4 min-w-0"
                  >
                    <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mb-2 sm:mb-3">
                      {/* 工作計畫標籤 */}
                      <div className="inline-flex items-center px-2 sm:px-3 py-1 text-sm sm:text-base font-medium rounded-md bg-indigo-100 text-indigo-800">
                        <span className="truncate max-w-[200px] sm:max-w-none">
                          {report.project.plan_subj_c}
                        </span>
                      </div>
                      {/* 執行工作標籤 */}
                      {report.execution_work_name && (
                        <div className="inline-flex items-center px-1.5 sm:px-2 py-0.5 sm:py-1 text-xs font-medium rounded-md bg-green-100 text-green-800">
                          <span className="truncate max-w-[150px] sm:max-w-none">
                            {report.execution_work_name}
                          </span>
                        </div>
                      )}
                      {/* 工作項目標籤 */}
                      {report.work_item_name && (
                        <div className="inline-flex items-center px-1.5 sm:px-2 py-0.5 sm:py-1 text-xs font-medium rounded-md bg-purple-100 text-purple-800">
                          <span className="truncate max-w-[150px] sm:max-w-none">
                            {report.work_item_name}
                          </span>
                        </div>
                      )}
                      {/* 服務公司標籤 */}
                      {report.service_company_name && (
                        <div className="inline-flex items-center px-1.5 sm:px-2 py-0.5 sm:py-1 text-xs font-medium rounded-md bg-orange-100 text-orange-800">
                          <span className="truncate max-w-[120px] sm:max-w-none">
                            {report.service_company_name}
                          </span>
                        </div>
                      )}
                      {/* 服務對象標籤 */}
                      {report.service_target_name && (
                        <div className="inline-flex items-center px-1.5 sm:px-2 py-0.5 sm:py-1 text-xs font-medium rounded-md bg-cyan-100 text-cyan-800">
                          <span className="truncate max-w-[120px] sm:max-w-none">
                            {report.service_target_name}
                          </span>
                        </div>
                      )}
                      {/* 執行時間 */}
                      {report.total_execution_time_minutes !== undefined &&
                      report.total_execution_time_minutes > 0 ? (
                        <span className="text-xs sm:text-sm text-blue-600 bg-blue-50 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded font-medium whitespace-nowrap">
                          {formatMinutesToHours(report.total_execution_time_minutes)}
                        </span>
                      ) : null}
                    </div>

                    {/* 內容 */}
                    <div
                      className={TypographyClasses.richTextDisplay}
                      dangerouslySetInnerHTML={{
                        __html: report.content || "",
                      }}
                    />

                    {/* 附件 - 使用與詳情頁相同的組件 */}
                    <AttachedFilesDisplay
                      files={report.files}
                      content={report.content}
                    />
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

export default DailyReportPreviewModal;
