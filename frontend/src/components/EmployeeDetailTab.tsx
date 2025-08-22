// frontend/src/components/EmployeeDetailTab.tsx

import React, { useState, useEffect } from "react";
import { ArrowLeft, Star } from "lucide-react";
import type { EmployeeInList, DailyReport } from "../App";
import { getProjectColors } from "../utils/colorUtils";
import { useAuth } from "../contexts/AuthContext";
import AttachedFilesDisplay from "./AttachedFilesDisplay";
import ChatInterface from "./ChatInterface";
import type { SupervisorApprovalInfo } from "../types/supervisor";

interface ReportWithApprovals extends DailyReport {
  approvals?: SupervisorApprovalInfo[];
}

interface EmployeeDetailTabProps {
  employee: EmployeeInList;
  reportId: number; // Correctly added prop
  onBack: () => void;
  onReviewCompleted?: () => void; // 主管評分完成後的回調
}

const EmployeeDetailTab: React.FC<EmployeeDetailTabProps> = ({
  employee: initialEmployee,
  reportId,
  onBack,
  onReviewCompleted,
}) => {
  const [reportDetail, setReportDetail] = useState<ReportWithApprovals | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);
  const { authFetch } = useAuth();

  const fetchReportDetails = async () => {
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
  };

  useEffect(() => {
    fetchReportDetails();
  }, [reportId]);

  const formatDate = (dateString: string) =>
    new Date(dateString).toLocaleDateString("zh-TW", {
      year: "numeric",
      month: "numeric",
      day: "numeric",
    });

  const getRatingLabel = (rating: number | null | undefined) => {
    if (!rating) return null;
    const labels: { [key: number]: string } = {
      1: "很差",
      2: "差",
      3: "普通",
      4: "好",
      5: "很好",
    };
    return labels[rating] || `${rating}`;
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
            <h2 className="text-2xl font-bold text-gray-900">
              {reportDetail.employee.empnamec || reportDetail.employee.name} -{" "}
              {formatDate(reportDetail.date)} 日報
            </h2>
            <p className="text-sm text-gray-500">
              {reportDetail.employee.department_name ||
                reportDetail.employee.department_no}
            </p>
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

          {typeof reportDetail.rating === "number" && (
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">此日報評分:</span>
              {renderFiveLevelStars(reportDetail.rating)}
              <span className="text-sm text-gray-700">
                {getRatingLabel(reportDetail.rating)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* 上方 - 日報內容 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">日報內容</h3>
        <div className="space-y-4">
          {(reportDetail.consolidated_content || []).map(
            (projectReport, index) => (
              <div
                key={index}
                className="border border-gray-100 rounded-lg p-4"
              >
                <div
                  className={`inline-flex items-center px-3 py-1 text-sm font-medium rounded-md mb-3 ${
                    getProjectColors(projectReport.project.plan_subj_c).tag
                  }`}
                >
                  {projectReport.project.plan_subj_c}
                </div>
                <p className="text-gray-700 whitespace-pre-wrap">
                  {projectReport.content}
                </p>
                <AttachedFilesDisplay files={projectReport.files} />
              </div>
            )
          )}
        </div>
      </div>

      {/* 下方 - 對話區域 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <ChatInterface
          reportId={reportDetail.id}
          reportOwnerId={reportDetail.employee.id}
          className="min-h-[400px]"
          reportStatus={reportDetail.status}
          approvals={reportDetail.approvals || []}
          onReviewSubmitted={fetchReportDetails}
          onReviewCompleted={onReviewCompleted}
        />
      </div>
    </div>
  );
};
export default EmployeeDetailTab;
