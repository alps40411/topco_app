// frontend/src/components/EmployeeDetailTab.tsx

import React, { useState, useEffect } from "react";
import { ArrowLeft, Send, Star } from "lucide-react";
import type { EmployeeInList, DailyReport } from "../App";
import { getProjectColors, greenButtonStyle } from "../utils/colorUtils";
import { useAuth } from "../contexts/AuthContext";
import AttachedFilesDisplay from "./AttachedFilesDisplay";
import ChatInterface from "./ChatInterface";
import toast from "react-hot-toast";

// Copied from EmployeeListTab.tsx for now, should be in a central types file
interface SupervisorApprovalInfo {
  supervisor_id: number;
  supervisor_name: string;
  supervisor_empno: string;
  status: "pending" | "approved";
  approved_at?: string;
  rating?: number;
  feedback?: string;
}

interface ReportWithApprovals extends DailyReport {
  approvals?: SupervisorApprovalInfo[];
}

interface EmployeeDetailTabProps {
  employee: EmployeeInList;
  reportId: number; // Correctly added prop
  onBack: () => void;
}

const EmployeeDetailTab: React.FC<EmployeeDetailTabProps> = ({
  employee: initialEmployee,
  reportId,
  onBack,
}) => {
  const [reportDetail, setReportDetail] = useState<ReportWithApprovals | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);
  const { authFetch } = useAuth();

  const fetchReportDetails = async () => {
    setIsLoading(true);
    try {
      const dateString = new Date().toISOString().split("T")[0]; // Flawed, but keeping as per user instruction
      const response = await authFetch(
        `/api/supervisor/reports-by-date?date=${dateString}`
      );
      if (response.ok) {
        const reports: DailyReport[] = await response.json();
        const specificReport = reports.find((r) => r.id === reportId);

        if (specificReport) {
          // Now, fetch the detailed approval status for this specific report
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
      }
    } catch (error) {
      console.error("無法獲取日報詳情:", error);
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
              {initialEmployee.name} - {formatDate(reportDetail.date)} 日報
            </h2>
            <p className="text-sm text-gray-500">
              {initialEmployee.department_name || initialEmployee.department_no}
            </p>
          </div>
        </div>
        {reportDetail.approvals && reportDetail.approvals.length > 0 && (() => {
          const ratedApprovals = reportDetail.approvals.filter(a => a.rating && a.rating > 0);
          if (ratedApprovals.length === 0) return null;

          const totalRating = ratedApprovals.reduce((sum, approval) => sum + (approval.rating || 0), 0);
          const averageRating = totalRating / ratedApprovals.length;

          return (
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">平均評分:</span>
              <div className="flex items-center text-yellow-500">
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    className={`w-5 h-5 ${
                      i < Math.floor(averageRating)
                        ? "fill-current"
                        : "text-gray-300"
                    }`}
                  />
                ))}
                <span className="ml-2 text-sm text-gray-600">
                  {averageRating.toFixed(1)}/5.0
                </span>
              </div>
            </div>
          );
        })()}
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
          className="min-h-[400px]"
          reportStatus={reportDetail.status}
          approvals={reportDetail.approvals || []}
          onReviewSubmitted={fetchReportDetails}
        />
      </div>
    </div>
  );
};
export default EmployeeDetailTab;
