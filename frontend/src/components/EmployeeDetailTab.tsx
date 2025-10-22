// frontend/src/components/EmployeeDetailTab.tsx

import React, { useState, useEffect, useCallback } from "react";
import { ArrowLeft, Star } from "lucide-react";
import type { DailyReport } from "../App";
import { getProjectColors } from "../utils/colorUtils";
import { useAuth } from "../hooks/useAuth";
import AttachedFilesDisplay from "./AttachedFilesDisplay";
import ChatInterface from "./ChatInterface";
import type { SupervisorApprovalInfo } from "../types/supervisor";
import { formatMinutesToHours } from "../utils/timeUtils";
import ForwardSelector from "./ForwardSelector";
import { TypographyClasses } from "../styles/typography";

interface ReportWithApprovals extends DailyReport {
  approvals?: SupervisorApprovalInfo[];
}

interface EmployeeDetailTabProps {
  reportId: number; // Correctly added prop
  onBack: () => void;
  onReviewCompleted?: () => void; // 主管評分完成後的回調
}

const EmployeeDetailTab: React.FC<EmployeeDetailTabProps> = ({
  reportId,
  onBack,
  onReviewCompleted,
}) => {
  const [reportDetail, setReportDetail] = useState<ReportWithApprovals | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);
  const [selectedForwardUsers, setSelectedForwardUsers] = useState<string[]>(
    []
  );
  // ✅ 新增: 提取作者資訊並傳遞給 ChatInterface
  const [reportAuthor, setReportAuthor] = useState<{
    empno: string;
    empname: string;
  } | null>(null);
  const { authFetch } = useAuth();

  // 從 URL 獲取 status 和 replyid 參數（從郵件進入時使用）
  const urlParams = new URLSearchParams(window.location.search);
  const status = urlParams.get("status") || undefined;
  const replyid = urlParams.get("replyid") || undefined;

  const fetchReportDetails = useCallback(async () => {
    setIsLoading(true);
    try {
      // Fetch specific report directly by ID instead of fetching all reports
      const response = await authFetch(`/api/supervisor/reports/${reportId}`);
      if (response.ok) {
        const specificReport: DailyReport = await response.json();

        // ✅ 提取作者資訊,避免 ChatInterface 重複查詢
        if (specificReport.employee) {
          const empno = String(specificReport.employee.empno).padStart(5, "0");
          setReportAuthor({
            empno: empno,
            empname: specificReport.employee.name,
          });
        }

        // Fetch the detailed approval status for this specific report
        const approvalResponse = await authFetch(
          `/api/supervisor/${reportId}/approvals`
        );
        if (approvalResponse.ok) {
          const approvals = await approvalResponse.json();
          setReportDetail({ ...specificReport, approvals });
        } else {
          // If approvals fail, still show the report
          setReportDetail({ ...specificReport, approvals: [] });
        }
      } else {
        setReportDetail(null);
      }
    } catch (error) {
      console.error("無法獲取日報詳情:", error);
      setReportDetail(null);
    } finally {
      setIsLoading(false);
    }
  }, [reportId, authFetch]);

  useEffect(() => {
    fetchReportDetails();
  }, [reportId, fetchReportDetails]);

  const formatDate = (dateString: string) => {
    if (!dateString) return "無日期";

    // 處理 YYYYMMDD 格式
    if (/^\d{8}$/.test(dateString)) {
      const year = dateString.substring(0, 4);
      const month = dateString.substring(4, 6);
      const day = dateString.substring(6, 8);
      return `${year}/${month}/${day}`;
    }

    // 處理其他格式
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) {
        return "無效日期";
      }
      return date.toLocaleDateString("zh-TW", {
        year: "numeric",
        month: "numeric",
        day: "numeric",
      });
    } catch {
      return "無效日期";
    }
  };

  const renderFiveLevelStars = (rating: number) => (
    <div className="flex items-center text-yellow-500">
      {[...Array(5)].map((_, i) => (
        <Star
          key={i}
          className={`w-5 h-5 ${
            i < (rating || 0) ? "fill-current" : "text-gray-300"
          }`}
        />
      ))}
    </div>
  );

  if (isLoading) {
    return <div className="p-6 text-center">載入日報詳情中...</div>;
  }
  if (!reportDetail) {
    return <div className="p-6 text-center">找不到指定的日報。</div>;
  }

  return (
    <div className="p-2 sm:p-4 md:p-6">
      {/* 大螢幕：標題列（標題和平均評分同一行） */}
      <div className="hidden md:flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <button
            onClick={onBack}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 flex-shrink-0"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h2 className="text-xl lg:text-2xl font-bold text-gray-900">
              {String(reportDetail.employee.id).padStart(5, "0")}{" "}
              {reportDetail.employee.empnamec || reportDetail.employee.name}{" "}
              {formatDate(reportDetail.date)} 日報
            </h2>
            <div className="text-base text-gray-500">
              {reportDetail.employee.department_name ||
                reportDetail.employee.department_no}
            </div>
          </div>
        </div>
        {/* 平均評分 - 右上角 */}
        <div className="flex items-center space-x-4">
          {reportDetail.approvals &&
            reportDetail.approvals.length > 0 &&
            (() => {
              const ratedApprovals = reportDetail.approvals.filter(
                (a) => a.rating && a.rating > 0
              );
              if (ratedApprovals.length === 0) return null;
              const totalRating = ratedApprovals.reduce(
                (sum, a) => sum + (a.rating || 0),
                0
              );
              const averageRating = totalRating / ratedApprovals.length;
              const clampedAvg = Math.min(5, Math.max(1, averageRating));
              return (
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600">平均評分:</span>
                  {renderFiveLevelStars(Math.round(clampedAvg))}
                </div>
              );
            })()}
        </div>
      </div>

      {/* 小螢幕：標題列（垂直佈局） */}
      <div className="md:hidden flex flex-col gap-3 mb-4">
        {/* 返回按鈕 + 標題 */}
        <div className="flex items-center gap-2">
          <button
            onClick={onBack}
            className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 flex-shrink-0"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex-1 min-w-0">
            <h2 className="text-base sm:text-lg font-bold text-gray-900 truncate">
              {String(reportDetail.employee.id).padStart(5, "0")}{" "}
              {reportDetail.employee.empnamec || reportDetail.employee.name}
            </h2>
            <div className="text-xs sm:text-sm text-gray-500 truncate">
              {reportDetail.employee.department_name ||
                reportDetail.employee.department_no}
            </div>
            <div className="text-xs text-gray-500 mt-0.5">
              {formatDate(reportDetail.date)}
            </div>
          </div>
        </div>

        {/* 平均評分 - 獨立一行 */}
        {reportDetail.approvals &&
          reportDetail.approvals.length > 0 &&
          (() => {
            const ratedApprovals = reportDetail.approvals.filter(
              (a) => a.rating && a.rating > 0
            );
            if (ratedApprovals.length === 0) return null;
            const totalRating = ratedApprovals.reduce(
              (sum, a) => sum + (a.rating || 0),
              0
            );
            const averageRating = totalRating / ratedApprovals.length;
            const clampedAvg = Math.min(5, Math.max(1, averageRating));
            return (
              <div className="flex items-center gap-2 bg-yellow-50 px-3 py-2 rounded-lg border border-yellow-200">
                <span className="text-xs sm:text-sm text-gray-600 font-medium whitespace-nowrap">平均評分:</span>
                {renderFiveLevelStars(Math.round(clampedAvg))}
              </div>
            );
          })()}
      </div>

      {/* 上方 - 日報內容 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3 sm:p-4 md:p-6 mb-4 sm:mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-4 mb-3 sm:mb-4">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 flex items-center">
            日報內容
          </h3>
          {(() => {
            const totalExecutionTime = (
              reportDetail.consolidated_content || []
            ).reduce(
              (total, project) =>
                total + (project.total_execution_time_minutes || 0),
              0
            );
            return totalExecutionTime > 0 ? (
              <span className="text-xs sm:text-sm text-green-600 bg-green-50 px-2 sm:px-3 py-1 rounded-full font-medium border border-green-200 w-fit">
                總執行時間: {totalExecutionTime} 小時
              </span>
            ) : (
              <span className="text-xs sm:text-sm text-gray-500 bg-gray-50 px-2 sm:px-3 py-1 rounded-full font-medium border border-gray-200 w-fit">
                總執行時間: 0 小時
              </span>
            );
          })()}
        </div>
        <div className="space-y-3 sm:space-y-4">
          {(reportDetail.consolidated_content || []).map(
            (projectReport, index) => (
              <div
                key={index}
                className="border border-gray-100 rounded-lg p-3 sm:p-4 min-w-0"
              >
                <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mb-2 sm:mb-3">
                  <div
                    className={`inline-flex items-center px-2 sm:px-3 py-1 text-sm sm:text-base font-medium rounded-md ${
                      getProjectColors(projectReport.project.plan_subj_c).tag
                    }`}
                  >
                    <span className="truncate max-w-[200px] sm:max-w-none">
                      {projectReport.project.plan_subj_c}
                    </span>
                  </div>
                  {projectReport.execution_work_name && (
                    <div className="inline-flex items-center px-1.5 sm:px-2 py-0.5 sm:py-1 text-xs font-medium rounded-md bg-green-100 text-green-800">
                      <span className="truncate max-w-[150px] sm:max-w-none">
                        {projectReport.execution_work_name}
                      </span>
                    </div>
                  )}
                  {projectReport.work_item_name && (
                    <div className="inline-flex items-center px-1.5 sm:px-2 py-0.5 sm:py-1 text-xs font-medium rounded-md bg-purple-100 text-purple-800">
                      <span className="truncate max-w-[150px] sm:max-w-none">
                        {projectReport.work_item_name}
                      </span>
                    </div>
                  )}
                  {projectReport.service_company_name && (
                    <div className="inline-flex items-center px-1.5 sm:px-2 py-0.5 sm:py-1 text-xs font-medium rounded-md bg-orange-100 text-orange-800">
                      <span className="truncate max-w-[120px] sm:max-w-none">
                        {projectReport.service_company_name}
                      </span>
                    </div>
                  )}
                  {projectReport.service_target_name && (
                    <div className="inline-flex items-center px-1.5 sm:px-2 py-0.5 sm:py-1 text-xs font-medium rounded-md bg-cyan-100 text-cyan-800">
                      <span className="truncate max-w-[120px] sm:max-w-none">
                        {projectReport.service_target_name}
                      </span>
                    </div>
                  )}
                  {projectReport.total_execution_time_minutes !== undefined &&
                  projectReport.total_execution_time_minutes > 0 ? (
                    <span className="text-xs sm:text-sm text-blue-600 bg-blue-50 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded font-medium whitespace-nowrap">
                      {projectReport.total_execution_time_minutes} 小時
                    </span>
                  ) : (
                    <span className="text-xs sm:text-sm text-gray-400 bg-gray-50 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded font-medium whitespace-nowrap">
                      未設定
                    </span>
                  )}
                </div>
                <div
                  className={TypographyClasses.richTextDisplay}
                  dangerouslySetInnerHTML={{ __html: projectReport.content }}
                />
                <AttachedFilesDisplay
                  files={projectReport.files}
                  content={projectReport.content}
                />
              </div>
            )
          )}
        </div>
        {/* 最後修改日期時間 - 整個日報內容區塊的底部 */}
        {reportDetail.consolidated_content &&
          reportDetail.consolidated_content.length > 0 &&
          reportDetail.consolidated_content[0].xdate &&
          reportDetail.consolidated_content[0].xtime && (
            <div className="pt-3 text-right text-xs text-gray-400">
              {reportDetail.consolidated_content[0].xdate.replace(
                /(\d{4})(\d{2})(\d{2})/,
                "$1/$2/$3"
              )}{" "}
              {reportDetail.consolidated_content[0].xtime}
            </div>
          )}
      </div>

      {/* 下方 - 回覆與評分區域 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-4 sm:mb-6 overflow-hidden">
        <div className="p-3 sm:p-4 md:p-6 border-b border-gray-200">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 flex items-center">
            回覆與評分
          </h3>
        </div>
        <ChatInterface
          reportId={reportDetail.id}
          reportOwnerId={reportDetail.employee.id}
          reportOwnerEmpno={reportDetail.employee.empno}
          reportOwnerName={reportDetail.employee.name}
          reportAuthor={reportAuthor} // ✅ 傳遞已獲取的作者資訊
          className="min-h-[300px] sm:min-h-[400px]"
          reportStatus={reportDetail.status}
          approvals={reportDetail.approvals || []}
          onReviewSubmitted={fetchReportDetails}
          onReviewCompleted={onReviewCompleted}
          selectedForwardUsers={selectedForwardUsers}
          onForwardUsersChange={setSelectedForwardUsers}
          urlStatus={status}
          urlReplyId={replyid} // ✅ 傳遞 replyid 參數
        />
      </div>

      {/* 轉寄功能區塊 - 在頁面底部 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-3 sm:p-4 md:p-6 border-b border-gray-200">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 flex items-center">
            轉寄設定
          </h3>
        </div>
        <div className="p-3 sm:p-4 md:p-6">
          <ForwardSelector
            selectedForwardUsers={selectedForwardUsers}
            onForwardUsersChange={setSelectedForwardUsers}
          />
        </div>
      </div>
    </div>
  );
};
export default EmployeeDetailTab;
