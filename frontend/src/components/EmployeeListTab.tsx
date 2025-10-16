// frontend/src/components/EmployeeListTab.tsx

import React, { useState, useEffect, useRef } from "react";
import { Clock, UserCheck, User } from "lucide-react";
import type { DailyReport, EmployeeInList } from "../App";
import { useAuth } from "../hooks/useAuth";
import type { SupervisorApprovalInfo } from "../types/supervisor";
import SupervisorDateBar from "./SupervisorDateBar";
import { toast } from "react-hot-toast";
import { useNavigate } from "react-router-dom";

// 新的日報首頁數據結構
interface HomepageReport {
  id: number;
  employee: {
    id: number;
    name: string;
    department_no: string;
    department_name: string;
    company_code: string;
  };
  date: string;
  status: "pending" | "reviewed";
  emergency: string;
  classify: string;
  sop_desc_c: string;
  reply_count: number;
  replier_count: number;
  my_ask: boolean;
  other_ask: boolean;
  is_forwarded: boolean;
  attachments: string[];
  customers: Array<{ name: string; company: string } | null>;
  last_update: string | null;
  can_view_detail: boolean; // 是否可以查看詳情
  supervision_status: "pending" | "approved" | "no_permission"; // 主管審核狀態
}

interface EmployeeListTabProps {
  onSelectEmployee: (employee: EmployeeInList, reportId: number) => void;
}

const EmployeeListTab: React.FC<EmployeeListTabProps> = ({
  onSelectEmployee,
}) => {
  const [reports, setReports] = useState<HomepageReport[]>([]);
  const [currentUserEmpno, setCurrentUserEmpno] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [editableStatus, setEditableStatus] = useState<Record<string, boolean>>(
    {}
  );
  const navigate = useNavigate();
  // 日報首頁預設顯示前一天的日報，因為當天的日報通常隔天才審閱
  // const getDefaultDate = () => {
  //   const yesterday = new Date();
  //   yesterday.setDate(yesterday.getDate() - 1);
  //   return yesterday;
  // };

  const [selectedDate, setSelectedDate] = useState<Date | null>(
    // getDefaultDate()
    new Date()
  );
  const { authFetch, user } = useAuth();

  // ✅ 使用 useRef 建立編輯狀態快取
  const editableStatusCache = useRef<Record<string, boolean>>({});

  useEffect(() => {
    if (user?.employee?.empno) {
      setCurrentUserEmpno(user.employee.empno);
    }
  }, [user]);

  // 檢查特定日期是否可編輯 (帶快取)
  const checkDateEditable = async (docDate: string) => {
    // ✅ 檢查快取
    if (editableStatusCache.current[docDate] !== undefined) {
      console.log(
        `[EmployeeListTab] 使用快取: ${docDate} = ${editableStatusCache.current[docDate]}`
      );
      return editableStatusCache.current[docDate];
    }

    try {
      // 改用 dates/range 來檢查可編輯狀態
      const response = await authFetch("/api/dates/range");
      if (response.ok) {
        const data = await response.json();

        // 從日期列表中找到對應日期
        const dateInfo = data.data?.find((d: any) => d.value === docDate);
        const isEditable = dateInfo?.can_write === true;

        // ✅ 存入快取
        editableStatusCache.current[docDate] = isEditable;
        console.log(
          `[EmployeeListTab] API 查詢 (daily-date-range): ${docDate} = ${isEditable}`
        );
        return isEditable;
      }
      return false;
    } catch (error) {
      console.error("檢查可編輯狀態失敗:", error);
      return false;
    }
  };

  useEffect(() => {
    if (!selectedDate) return; // Don't fetch if date is null

    const fetchHomepageReports = async () => {
      setIsLoading(true);
      // 確保使用本地日期，避免時區問題
      const year = selectedDate.getFullYear();
      const month = String(selectedDate.getMonth() + 1).padStart(2, "0");
      const day = String(selectedDate.getDate()).padStart(2, "0");
      const dateString = `${year}-${month}-${day}`;

      try {
        // 使用新的日報首頁API
        const response = await authFetch(
          `/api/supervisor/daily-homepage?date=${dateString}`
        );

        if (response.ok) {
          const homepageReports = await response.json();

          setReports(homepageReports);

          // 檢查當天所有唯一日期的可編輯狀態
          const uniqueDates = [
            ...new Set(
              homepageReports
                .map((r: HomepageReport) => r.date)
                .filter((d) => d != null)
            ),
          ];
          const statusPromises = uniqueDates.map(async (date) => {
            if (!date) return [null, false];
            const isEditable = await checkDateEditable(date);
            return [date, isEditable];
          });

          const statusResults = await Promise.all(statusPromises);
          const statusMap: Record<string, boolean> = {};
          statusResults.forEach(([date, isEditable]) => {
            statusMap[date as string] = isEditable as boolean;
          });

          setEditableStatus(statusMap);
        } else {
          console.error(
            "API response not ok:",
            response.status,
            await response.text()
          );
          setReports([]);
        }
      } catch (error) {
        console.error("無法獲取日報首頁列表:", error);
        setReports([]);
      } finally {
        setIsLoading(false);
      }
    };
    fetchHomepageReports();
  }, [selectedDate, authFetch]);

  const handleDateChange = (date: Date) => {
    setSelectedDate(date);
  };

  // 處理刪除日報
  const handleDeleteReport = async (reportId: number, reportDate: string) => {
    if (!window.confirm("確定要刪除這份日報嗎？")) {
      return;
    }

    try {
      const response = await authFetch(`/api/reports/${reportId}`, {
        method: "DELETE",
      });

      if (response.ok) {
        toast.success("日報刪除成功");
        // 重新載入當前日期的日報列表
        if (selectedDate) {
          const year = selectedDate.getFullYear();
          const month = String(selectedDate.getMonth() + 1).padStart(2, "0");
          const day = String(selectedDate.getDate()).padStart(2, "0");
          const dateString = `${year}-${month}-${day}`;
          const refreshResponse = await authFetch(
            `/api/supervisor/daily-homepage?date=${dateString}`
          );
          if (refreshResponse.ok) {
            const homepageReports = await refreshResponse.json();
            setReports(homepageReports);
          }
        }
      } else {
        const error = await response.json();
        toast.error(error.detail || "刪除日報失敗");
      }
    } catch (error) {
      console.error("刪除日報失敗:", error);
      toast.error("刪除日報失敗");
    }
  };

  // 處理編輯日報
  const handleEditReport = (reportDate: string) => {
    // 將 YYYYMMDD 格式轉換為 YYYY-MM-DD 格式
    const formattedDate =
      reportDate.length === 8
        ? `${reportDate.substring(0, 4)}-${reportDate.substring(
            4,
            6
          )}-${reportDate.substring(6, 8)}`
        : reportDate;
    // 導航到日報編輯頁面，使用該日報的日期
    navigate(`?tab=daily&date=${formattedDate}`);
  };

  const renderFowardedStatus = (report: HomepageReport) => {
    const isForwarded = report.is_forwarded;

    return (
      <div className="flex items-center justify-center gap-0.5">
        {isForwarded && (
          <img
            src="/MyReportAI/forward.png"
            alt="轉寄"
            className="w-4 h-4 flex-shrink-0"
          />
        )}
      </div>
    );
  };

  // 渲染回應狀態圖片 - 基於 reply_count 和 replier_count 判斷
  const renderResponseStatus = (report: HomepageReport) => {
    const replyCount = report.reply_count || 0;
    const replierCount = report.replier_count || 0;

    if (replyCount === 0) {
      // 沒有任何回應
      return null;
    } else if (replyCount === replierCount) {
      // 只有自己回應 (reply_count = replier_count)
      return (
        <img
          src="/MyReportAI/purple_heart.gif"
          alt="自己回應"
          className="w-6 h-6"
        />
      );
    } else if (replierCount === 0) {
      // 自己沒回應，只有別人回應 (replier_count = 0)
      return (
        <img
          src="/MyReportAI/red_heart.gif"
          alt="有人回應"
          className="w-6 h-6"
        />
      );
    } else if (replyCount > replierCount) {
      // 都有回應 (reply_count > replier_count)
      return (
        <img src="/MyReportAI/hearts.gif" alt="雙方回應" className="w-6 h-6" />
      );
    }

    return null;
  };

  // 渲染內容欄位 - my_ask、other_ask 和附件圖片
  const renderContentStatus = (report: HomepageReport) => {
    const hasMyAsk = report.my_ask;
    const hasOtherAsk = report.other_ask;
    const hasAttachments = report.attachments && report.attachments.length > 0;

    return (
      <div className="flex items-center justify-center gap-0.5">
        {hasMyAsk && (
          <img
            src="/MyReportAI/my_ask.png"
            alt="我的提問"
            className="w-4 h-4 flex-shrink-0"
          />
        )}
        {hasOtherAsk && (
          <img
            src="/MyReportAI/other_ask.png"
            alt="他人提問"
            className="w-4 h-4 flex-shrink-0"
          />
        )}
        {hasAttachments && (
          <img
            src="/MyReportAI/attached.gif"
            alt="有附件"
            className="w-4 h-4 flex-shrink-0"
            title="此日報包含附件"
          />
        )}
      </div>
    );
  };

  // 渲染主管審核狀態
  const renderSupervisionStatus = (status: string) => {
    switch (status) {
      case "pending":
        return (
          <div className="flex items-center space-x-1 text-orange-600">
            <Clock className="w-4 h-4" />
            <span className="text-sm font-medium">待審核</span>
          </div>
        );
      case "approved":
        return (
          <div className="flex items-center space-x-1 text-green-600">
            <UserCheck className="w-4 h-4" />
            <span className="text-sm font-medium">已審核</span>
          </div>
        );
      case "no_permission":
        return (
          <div className="flex items-center space-x-1 text-gray-500">
            <User className="w-4 h-4" />
            <span className="text-sm font-medium">無須審核</span>
          </div>
        );
      default:
        return null;
    }
  };

  if (isLoading) {
    return <div className="p-6 text-center">載入日報中...</div>;
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">日報首頁</h2>

        <SupervisorDateBar
          selectedDate={selectedDate}
          onChange={handleDateChange}
          className="w-full"
        />
      </div>

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-20">
                狀態
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                員工資訊
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                執行項目
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-20">
                內容
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-24">
                編輯
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {reports.map((report) => (
              <tr key={report.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <div className="flex items-center justify-center gap-1">
                    {renderFowardedStatus(report)}
                    {renderResponseStatus(report)}
                  </div>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="text-base font-medium text-gray-900">
                    {report.employee.name}
                  </div>
                </td>
                <td className="px-4 py-3">
                  {report.can_view_detail ? (
                    <div
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
                      className="text-base text-blue-600 hover:text-blue-900 max-w-xs cursor-pointer hover:bg-blue-50 p-2 rounded transition-colors"
                    >
                      {report.sop_desc_c || "執行項目"}
                      {report.emergency && (
                        <span className="ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                          緊急
                        </span>
                      )}
                    </div>
                  ) : (
                    <div className="text-base text-gray-400 max-w-xs p-2">
                      {report.sop_desc_c || "執行項目"}
                      {report.emergency && (
                        <span className="ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                          緊急
                        </span>
                      )}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 text-center">
                  {renderContentStatus(report)}
                </td>
                <td className="px-4 py-3 text-center">
                  {(() => {
                    const isOwnReport =
                      currentUserEmpno === String(report.employee.id);
                    const hasNoReply = report.reply_count === 0;
                    const hasDate = !!report.date;
                    const isEditable =
                      report.date && editableStatus[report.date] === true;
                    return (
                      isOwnReport &&
                      hasNoReply &&
                      hasDate &&
                      isEditable && (
                        <div className="flex items-center justify-center gap-2">
                          <button
                            onClick={() => handleEditReport(report.date)}
                            className="hover:opacity-75 transition-opacity"
                            title="編輯日報"
                          >
                            <img
                              src="/MyReportAI/edit.png"
                              alt="編輯"
                              className="w-5 h-5"
                            />
                          </button>
                          <button
                            onClick={() =>
                              handleDeleteReport(report.id, report.date)
                            }
                            className="hover:opacity-75 transition-opacity"
                            title="刪除日報"
                          >
                            <img
                              src="/MyReportAI/delete.png"
                              alt="刪除"
                              className="w-5 h-5"
                            />
                          </button>
                        </div>
                      )
                    );
                  })()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {reports.length === 0 && !isLoading && (
        <div className="text-center py-16 text-gray-500 bg-white border border-gray-200 rounded-lg">
          <p>這天沒有任何相關的日報。</p>
        </div>
      )}
    </div>
  );
};
export default EmployeeListTab;
