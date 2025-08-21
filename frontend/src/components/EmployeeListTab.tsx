// frontend/src/components/EmployeeListTab.tsx

import React, { useState, useEffect } from "react";
import {
  Clock,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Calendar,
  MessageCircle,
} from "lucide-react";
import type { DailyReport, EmployeeInList } from "../App";
import { useAuth } from "../contexts/AuthContext";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import type { SupervisorApprovalInfo } from "../types/supervisor";

interface ReportWithApprovals extends DailyReport {
  approvals?: SupervisorApprovalInfo[];
}

interface EmployeeListTabProps {
  onSelectEmployee: (employee: EmployeeInList, reportId: number) => void;
}

const EmployeeListTab: React.FC<EmployeeListTabProps> = ({
  onSelectEmployee,
}) => {
  const [reports, setReports] = useState<ReportWithApprovals[]>([]);
  const [currentUserId, setCurrentUserId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  // 主管審核頁面預設顯示前一天的日報，因為當天的日報通常隔天才審核
  const getDefaultDate = () => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    return yesterday;
  };

  const [selectedDate, setSelectedDate] = useState<Date | null>(
    getDefaultDate()
  );
  const { authFetch, user } = useAuth();

  useEffect(() => {
    if (user?.employee?.id) {
      setCurrentUserId(user.employee.id);
    }
  }, [user]);

  useEffect(() => {
    if (!selectedDate) return; // Don't fetch if date is null

    const fetchReportsByDate = async () => {
      setIsLoading(true);
      const dateString = selectedDate.toISOString().split("T")[0];
      try {
        const response = await authFetch(
          `/api/supervisor/reports-by-date?date=${dateString}`
        );
        if (response.ok) {
          const reportsData = await response.json();

          // 為每個報告獲取審核狀態
          const reportsWithApprovals = await Promise.all(
            reportsData.map(async (report: DailyReport) => {
              try {
                const approvalResponse = await authFetch(
                  `/api/supervisor/reports/${report.id}/approvals`
                );
                if (approvalResponse.ok) {
                  const approvals = await approvalResponse.json();
                  return { ...report, approvals };
                }
              } catch (error) {
                console.error(`無法獲取報告 ${report.id} 的審核狀態:`, error);
              }
              return { ...report, approvals: [] };
            })
          );

          setReports(reportsWithApprovals);
        } else {
          setReports([]);
        }
      } catch (error) {
        console.error("無法獲取日報列表:", error);
        setReports([]);
      } finally {
        setIsLoading(false);
      }
    };
    fetchReportsByDate();
  }, [selectedDate, authFetch]);

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
    }
  };

  if (isLoading) {
    return <div className="p-6 text-center">載入日報中...</div>;
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">日報審核</h2>
          <p className="text-sm text-gray-600 mt-1">
            預設顯示前一天的日報，因為員工填寫時間到隔天8:30截止
          </p>
        </div>
        <div className="flex items-center space-x-2 bg-white border border-gray-200 rounded-lg p-1">
          <button
            onClick={() => changeDate(-1)}
            className="p-2 rounded hover:bg-gray-100"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <DatePicker
            selected={selectedDate}
            onChange={handleDateChange} // Corrected handler
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

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                員工姓名
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                狀態
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                留言
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                操作
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {reports.map((report) => (
              <tr key={report.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">
                    {report.employee.name || report.employee.empnamec}
                  </div>
                  <div className="text-sm text-gray-500">
                    {report.employee.department_name || report.employee.department_no}
                  </div>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  {(() => {
                    const myApproval = report.approvals?.find(
                      (approval) => approval.supervisor_id === currentUserId
                    );
                    console.log(myApproval);
                    console.log(currentUserId);
                    if (!myApproval || myApproval.status === "pending") {
                      return (
                        <div className="flex items-center space-x-1 text-orange-600">
                          <Clock className="w-4 h-4" />
                          <span className="text-sm font-medium">待審核</span>
                        </div>
                      );
                    } else if (myApproval.status === "approved") {
                      return (
                        <div className="flex items-center space-x-1 text-green-600">
                          <CheckCircle className="w-4 h-4" />
                          <span className="text-sm font-medium">已審核</span>
                        </div>
                      );
                    } else { // Fallback for unexpected statuses, should ideally not happen with current backend logic
                      return (
                        <div className="flex items-center space-x-1 text-orange-600">
                          <Clock className="w-4 h-4" />
                          <span className="text-sm font-medium">待審核 (未知狀態)</span>
                        </div>
                      );
                    }
                  })()}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="flex items-center space-x-1">
                    <MessageCircle className="w-4 h-4 text-gray-400" />
                    <span className="text-sm text-gray-600">
                      {report.comments_count || 0} 則
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <button
                    onClick={() =>
                      onSelectEmployee(
                        {
                          id: report.employee.id,
                          name: report.employee.name,
                          department_name: report.employee.department_name,
                          department_no: report.employee.department_no,
                          pending_reports_count: 0,
                        },
                        report.id
                      )
                    }
                    className="text-blue-600 hover:text-blue-900 text-sm font-medium"
                  >
                    查看日報
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {reports.length === 0 && !isLoading && (
        <div className="text-center py-16 text-gray-500 bg-white border border-gray-200 rounded-lg">
          <p>這天沒有任何人提交日報。</p>
        </div>
      )}
    </div>
  );
};
export default EmployeeListTab;
