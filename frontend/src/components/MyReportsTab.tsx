// frontend/src/components/MyReportsTab.tsx

import React, { useState, useEffect } from "react";
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  Eye,
  MessageCircle,
  Star,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { getProjectColors } from "../utils/colorUtils";
import type { DailyReport } from "../App";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import toast from "react-hot-toast";
import EmployeeDetailTab from "./EmployeeDetailTab";

const MyReportsTab: React.FC = () => {
  const [reports, setReports] = useState<DailyReport[]>([]);
  const [selectedReport, setSelectedReport] = useState<DailyReport | null>(
    null
  );
  // 根據當前時間決定預設查看哪一天的日報
  const getDefaultViewDate = () => {
    const now = new Date();
    const currentTime = now.getTime();
    const eightThirtyToday = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate(),
      8,
      30
    ).getTime();

    // 如果現在是早上8:30之前，預設查看昨天的日報
    if (currentTime < eightThirtyToday) {
      const yesterday = new Date(now);
      yesterday.setDate(yesterday.getDate() - 1);
      return yesterday;
    }

    // 否則查看今天的日報
    return now;
  };

  const [selectedDate, setSelectedDate] = useState<Date | null>(
    getDefaultViewDate()
  );
  const [isLoading, setIsLoading] = useState(true);
  const { authFetch, user } = useAuth();

  const fetchMyReports = async () => {
    if (!selectedDate || !user) return;

    setIsLoading(true);
    try {
      const dateString = selectedDate.toISOString().split("T")[0];
      // 使用新的優化API端點，直接獲取當前用戶的日報
      const response = await authFetch(
        `/api/supervisor/my-reports-by-date?date=${dateString}`
      );
      if (response.ok) {
        const myReports: DailyReport[] = await response.json();
        setReports(myReports);
      } else {
        setReports([]);
      }
    } catch (error) {
      console.error("獲取日報失敗:", error);
      toast.error("載入日報失敗");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMyReports();
  }, [selectedDate]);

  const changeDate = (offset: number) => {
    setSelectedDate((prevDate) => {
      if (!prevDate) return new Date();
      const newDate = new Date(prevDate);
      newDate.setDate(newDate.getDate() + offset);
      return newDate;
    });
  };

  const handleDateChange = (date: Date | null) => {
    if (date) {
      setSelectedDate(date);
      setSelectedReport(null);
    }
  };

  const formatDate = (dateString: string) =>
    new Date(dateString).toLocaleDateString("zh-TW", {
      year: "numeric",
      month: "numeric",
      day: "numeric",
    });

  // 當選取某一筆日報時，直接沿用主管審閱的詳情頁 UI
  if (selectedReport) {
    const backToList = () => setSelectedReport(null);
    const employeeForDetail = {
      id: selectedReport.employee.id,
      name: selectedReport.employee.name,
      department_no: selectedReport.employee.department_no,
      department_name: selectedReport.employee.department_name,
      pending_reports_count: 0,
    };

    return (
      <EmployeeDetailTab
        employee={employeeForDetail as any}
        reportId={selectedReport.id}
        onBack={backToList}
      />
    );
  }

  return (
    <div className="p-6">
      {/* 標題和日期選擇器 */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">我的日報</h2>
        <div className="flex items-center space-x-2 bg-white border border-gray-200 rounded-lg p-1">
          <button
            onClick={() => changeDate(-1)}
            className="p-2 rounded hover:bg-gray-100"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <DatePicker
            selected={selectedDate}
            onChange={handleDateChange}
            dateFormat="yyyy / MM / dd"
            className="text-center font-semibold text-gray-700 w-32 bg-transparent focus:outline-none"
            customInput={
              <button className="flex items-center space-x-2 p-2 hover:bg-gray-100 rounded">
                <Calendar className="w-5 h-5 text-gray-500" />
                <span>
                  {selectedDate
                    ? selectedDate.toLocaleDateString("zh-TW", {
                        year: "numeric",
                        month: "2-digit",
                        day: "2-digit",
                      })
                    : "選擇日期"}
                </span>
              </button>
            }
          />
          <button
            onClick={() => changeDate(1)}
            className="p-2 rounded hover:bg-gray-100"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* 日報列表 */}
      {isLoading ? (
        <div className="p-6 text-center">載入日報中...</div>
      ) : reports.length === 0 ? (
        <div className="text-center py-16 text-gray-500 bg-white border border-gray-200 rounded-lg">
          <Calendar className="w-12 h-12 mx-auto mb-4 text-gray-300" />
          <p>這天沒有提交日報</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {reports.map((report) => (
            <div
              key={report.id}
              className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => setSelectedReport(report)}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {formatDate(report.date)} 的日報
                  </h3>
                  {(() => {
                    switch (report.status) {
                      case "pending":
                        return (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                            <MessageCircle className="w-3 h-3 mr-1" />
                            待審閱
                          </span>
                        );
                      case "reviewed":
                        return (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            <Eye className="w-3 h-3 mr-1" />
                            已審閱
                          </span>
                        );
                      default:
                        return null;
                    }
                  })()}
                </div>

                {/* 列表維持顯示後端 top-level rating（若有）*/}
                {report.rating && (
                  <div className="flex items-center space-x-2">
                    <span className="text-sm text-gray-600">我的分數:</span>
                    <div className="flex items-center text-yellow-500">
                      {[...Array(5)].map((_, i) => (
                        <Star
                          key={i}
                          className={`w-4 h-4 ${
                            i < (report.rating || 0)
                              ? "fill-current"
                              : "text-gray-300"
                          }`}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* 預覽專案內容 */}
              <div className="space-y-2">
                {(report.consolidated_content || [])
                  .slice(0, 2)
                  .map((projectReport, index) => (
                    <div
                      key={index}
                      className="border-l-4 border-gray-200 pl-4"
                    >
                      <div
                        className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded mb-1 ${
                          getProjectColors(projectReport.project.plan_subj_c)
                            .tag
                        }`}
                      >
                        {projectReport.project.plan_subj_c}
                      </div>
                      <p className="text-sm text-gray-600 line-clamp-2">
                        {projectReport.content.length > 100
                          ? projectReport.content.substring(0, 100) + "..."
                          : projectReport.content}
                      </p>
                    </div>
                  ))}
                {(report.consolidated_content || []).length > 2 && (
                  <p className="text-xs text-gray-500 mt-2">
                    還有 {(report.consolidated_content || []).length - 2}{" "}
                    個專案...
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MyReportsTab;
