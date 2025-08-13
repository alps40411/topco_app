// frontend/src/components/EmployeeDetailTab.tsx

import React, { useState, useEffect } from "react";
import { ArrowLeft, Send, Star } from "lucide-react";
import type { EmployeeInList, DailyReport } from "../App";
import { getProjectColors, greenButtonStyle } from "../utils/colorUtils";
import { useAuth } from "../contexts/AuthContext";
import AttachedFilesDisplay from "./AttachedFilesDisplay";
import toast from "react-hot-toast";

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
  const [reportDetail, setReportDetail] = useState<DailyReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { authFetch } = useAuth();

  const [selectedRating, setSelectedRating] = useState<number>(0);
  const [feedback, setFeedback] = useState<string>("");

  const fetchReportDetails = async () => {
    // This logic is now simpler as we fetch a single report
    setIsLoading(true);
    // You would typically fetch a single report by its ID.
    // We will simulate this by fetching all and finding the one.
    // In a real app, you'd have a GET /api/supervisor/reports/{reportId} endpoint.
    try {
      const dateString = new Date().toISOString().split("T")[0]; // Assuming today for now
      const response = await authFetch(
        `/api/supervisor/reports-by-date?date=${dateString}`
      );
      if (response.ok) {
        const reports: DailyReport[] = await response.json();
        const specificReport = reports.find((r) => r.id === reportId);
        setReportDetail(specificReport || null);
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

  const handleSubmitReview = async () => {
    if (!reportDetail || selectedRating === 0) {
      toast.error("請給予評分");
      return;
    }
    try {
      const response = await authFetch(
        `/api/supervisor/reports/${reportDetail.id}/review`,
        {
          method: "PUT",
          body: JSON.stringify({ rating: selectedRating, feedback }),
        }
      );
      if (!response.ok) throw new Error("提交審核失敗");
      toast.success("審核已成功提交！");
      onBack(); // Go back to the list view after submission
    } catch (error) {
      console.error(error);
      toast.error("提交審核時發生錯誤。");
    }
  };

  const ratingLabels = ["很差", "差", "普通", "好", "非常好"];
  const suggestedFeedbacks = [
    "工作內容詳實，執行效果良好，請繼續保持。",
    "報告內容完整，建議在執行細節上可以更加具體。",
    "工作進度符合預期，期待看到更多創新想法。",
  ];
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
              {initialEmployee.department}
            </p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="space-y-4 mb-6">
          {(reportDetail.consolidated_content || []).map(
            (projectReport, index) => (
              <div
                key={index}
                className="border border-gray-100 rounded-lg p-4"
              >
                <div
                  className={`inline-flex items-center px-3 py-1 text-sm font-medium rounded-md mb-3 ${
                    getProjectColors(projectReport.project.name).tag
                  }`}
                >
                  {projectReport.project.name}
                </div>
                <p className="text-gray-700 whitespace-pre-wrap">
                  {projectReport.content}
                </p>
                <AttachedFilesDisplay files={projectReport.files} />
              </div>
            )
          )}
        </div>
        {reportDetail.status === "pending" ? (
          <div className="border-t border-gray-200 pt-6 mt-4">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  評分
                </label>
                <div className="flex space-x-2">
                  {[1, 2, 3, 4, 5].map((rating) => (
                    <button
                      key={rating}
                      onClick={() => setSelectedRating(rating)}
                      className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                        selectedRating === rating
                          ? "bg-yellow-400 text-yellow-800"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      {ratingLabels[rating - 1]}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  建議回覆
                </label>
                <div className="flex flex-wrap gap-2 mb-3">
                  {suggestedFeedbacks.map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => setFeedback(suggestion)}
                      className="px-3 py-1 bg-blue-50 text-blue-700 text-xs rounded-full hover:bg-blue-100"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  回覆內容
                </label>
                <textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  className="w-full min-h-[100px] p-3 border border-gray-300 rounded-lg"
                  placeholder="請輸入您的回覆..."
                />
              </div>
              <div className="flex justify-end">
                <button
                  onClick={handleSubmitReview}
                  disabled={selectedRating === 0}
                  className={`inline-flex items-center px-4 py-2 text-sm rounded-lg disabled:bg-gray-200 disabled:text-gray-400 ${greenButtonStyle}`}
                >
                  <Send className="w-4 h-4 mr-2" /> 提交審核
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="border-t border-gray-200 pt-4 mt-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h5 className="text-sm font-medium text-gray-900">審核結果</h5>
                <div className="flex items-center text-yellow-500">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      className={`w-5 h-5 ${
                        i < (reportDetail.rating || 0)
                          ? "fill-current"
                          : "text-gray-300"
                      }`}
                    />
                  ))}
                </div>
              </div>
              <p className="text-sm text-gray-700">{reportDetail.feedback}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
export default EmployeeDetailTab;
