// frontend/src/components/EmployeeDetailTab.tsx

import React, { useState, useEffect, useCallback } from "react";
import { ArrowLeft, Star } from "lucide-react";
import type { DailyReport } from "../App";
import { getProjectColors } from "../utils/colorUtils";
import { useAuth } from "../contexts/AuthContext";
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
  const [selectedForwardUsers, setSelectedForwardUsers] = useState<string[]>([]);
  const { authFetch } = useAuth();

  // 從 URL 獲取 status 參數（status=P 表示從郵件進入）
  const urlParams = new URLSearchParams(window.location.search);
  const status = urlParams.get('status') || undefined;

  const fetchReportDetails = useCallback(async () => {
    setIsLoading(true);
    try {
      // Fetch specific report directly by ID instead of fetching all reports
      const response = await authFetch(`/api/supervisor/reports/${reportId}`);
      if (response.ok) {
        const specificReport: DailyReport = await response.json();

        // Fetch the detailed approval status for this specific report
        const approvalResponse = await authFetch(
          `/api/supervisor/reports/${reportId}/approvals`
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
    <div className="p-6">
      {/* 標題列 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <button
            onClick={onBack}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h2 className="text-2xl font-bold text-gray-900 h-8 flex items-center">
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
                  {/* <span className="text-sm text-gray-600">
                    {Math.round(clampedAvg)}/5
                  </span> */}
                </div>
              );
            })()}
        </div>
      </div>

      {/* 上方 - 日報內容 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 h-6 flex items-center">
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
              <span className="text-sm text-green-600 bg-green-50 px-3 py-1 rounded-full font-medium border border-green-200">
                總執行時間: {totalExecutionTime} 小時
              </span>
            ) : (
              <span className="text-sm text-gray-500 bg-gray-50 px-3 py-1 rounded-full font-medium border border-gray-200">
                總執行時間: 0 小時
              </span>
            );
          })()}
        </div>
        <div className="space-y-4">
          {(reportDetail.consolidated_content || []).map(
            (projectReport, index) => (
              <div
                key={index}
                className="border border-gray-100 rounded-lg p-4"
              >
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <div
                    className={`inline-flex items-center px-3 py-1 text-base font-medium rounded-md ${
                      getProjectColors(projectReport.project.plan_subj_c).tag
                    }`}
                  >
                    {projectReport.project.plan_subj_c}
                  </div>
                  {projectReport.execution_work_name && (
                    <div className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-md bg-green-100 text-green-800">
                      {projectReport.execution_work_name}
                    </div>
                  )}
                  {projectReport.work_item_name && (
                    <div className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-md bg-purple-100 text-purple-800">
                      {projectReport.work_item_name}
                    </div>
                  )}
                  {projectReport.total_execution_time_minutes !== undefined &&
                  projectReport.total_execution_time_minutes > 0 ? (
                    <span className="text-base text-blue-600 bg-blue-50 px-2 py-1 rounded font-medium">
                      執行時間: {projectReport.total_execution_time_minutes}{" "}
                      小時
                    </span>
                  ) : (
                    <span className="text-base text-gray-400 bg-gray-50 px-2 py-1 rounded font-medium">
                      執行時間: 未設定
                    </span>
                  )}
                </div>
                <div
                  className={TypographyClasses.richTextDisplay}
                  dangerouslySetInnerHTML={{ __html: projectReport.content }}
                />
                <AttachedFilesDisplay files={projectReport.files} />
              </div>
            )
          )}
        </div>
      </div>

      {/* 下方 - 對話區域 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6">
        <ChatInterface
          reportId={reportDetail.id}
          reportOwnerId={reportDetail.employee.id}
          reportOwnerEmpno={reportDetail.employee.empno}
          reportOwnerName={reportDetail.employee.name}
          className="min-h-[400px]"
          reportStatus={reportDetail.status}
          approvals={reportDetail.approvals || []}
          onReviewSubmitted={fetchReportDetails}
          onReviewCompleted={onReviewCompleted}
          selectedForwardUsers={selectedForwardUsers}
          onForwardUsersChange={setSelectedForwardUsers}
          urlStatus={status}
        />
      </div>

      {/* 轉寄功能區塊 - 在頁面底部 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <ForwardSelector
          selectedForwardUsers={selectedForwardUsers}
          onForwardUsersChange={setSelectedForwardUsers}
        />
      </div>
    </div>
  );
};
export default EmployeeDetailTab;
