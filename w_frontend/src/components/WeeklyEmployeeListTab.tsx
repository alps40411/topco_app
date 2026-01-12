// frontend/src/components/WeeklyEmployeeListTab.tsx

import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../hooks/useAuth";
import WeekSelector from "./WeekSelector";
import { getCurrentWeek } from "../utils/weekUtils";
import { WeeklyReportApi } from "../services/weeklyReportApi";
import { toast } from "react-hot-toast";
import { useNavigate, useSearchParams } from "react-router-dom";

interface WeeklyReport {
  id: number;
  week: number;
  year: number;
  employee: {
    id: number;
    empno: string;
    name: string;
    department_no: string;
    department_name: string;
    company_code: string;
    company_name: string; // 公司名稱
  };
  work_item: {
    id: number;
    name: string;
  };
  subject: string;
  content: string;
  status: "pending" | "reviewed";
  attachments: any[];
  last_update: string;
  reply_count: number;
  replier_count: number;
  my_ask: boolean;
  other_ask: boolean;
  is_forwarded: boolean;
  is_forwarded_to_me?: boolean;
  can_view_detail: boolean;
  start_date: string; // 週報開始日期 YYYYMMDD
  end_date: string; // 週報結束日期 YYYYMMDD
}

interface WeeklyEmployeeListTabProps {
  onSelectEmployee?: (employee: any, reportId: number) => void;
}

const WeeklyEmployeeListTab: React.FC<WeeklyEmployeeListTabProps> = ({
  onSelectEmployee,
}) => {
  const [subordinateReports, setSubordinateReports] = useState<WeeklyReport[]>(
    []
  );
  const [forwardedReports, setForwardedReports] = useState<WeeklyReport[]>([]);
  const [currentUserEmpno, setCurrentUserEmpno] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const { authFetch, user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // 獲取初始週次（從 URL 參數或當前週次）
  const getInitialWeek = (): { year: number; week: number } => {
    const yearParam = searchParams.get("year");
    const weekParam = searchParams.get("week");

    if (yearParam && weekParam) {
      return {
        year: parseInt(yearParam),
        week: parseInt(weekParam),
      };
    }

    return getCurrentWeek();
  };

  const [selectedYear, setSelectedYear] = useState<number>(
    getInitialWeek().year
  );
  const [selectedWeek, setSelectedWeek] = useState<number>(
    getInitialWeek().week
  );

  useEffect(() => {
    if (user?.employee?.empno) {
      setCurrentUserEmpno(user.employee.empno);
    }
  }, [user]);

  // 載入週報列表
  useEffect(() => {
    const loadReports = async () => {
      if (!authFetch) return;

      setIsLoading(true);
      try {
        const data = await WeeklyReportApi.getWeeklyReports(
          selectedYear,
          selectedWeek,
          authFetch
        );

        setSubordinateReports(data.subordinate_reports || []);
        // 為轉寄週報標記 is_forwarded_to_me
        const markedForwardedReports = (data.forwarded_reports || []).map(
          (report: WeeklyReport) => ({
            ...report,
            is_forwarded_to_me: true,
          })
        );
        setForwardedReports(markedForwardedReports);
      } catch (error) {
        console.error("載入週報列表失敗:", error);
        toast.error("載入週報列表失敗");
        setSubordinateReports([]);
        setForwardedReports([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadReports();
  }, [selectedYear, selectedWeek, authFetch]);

  // 處理週次變更 - 使用 useCallback 避免不必要的重新渲染
  const handleWeekChange = useCallback((year: number, week: number) => {
    setSelectedYear(year);
    setSelectedWeek(week);

    // 更新 URL 參數
    navigate(`?tab=weeklyList&year=${year}&week=${week}`, { replace: true });
  }, [navigate]);

  // 按公司分組週報
  const groupReportsByCompany = (reports: WeeklyReport[]) => {
    const grouped = new Map<string, WeeklyReport[]>();

    reports.forEach((report) => {
      const companyName = report.employee.company_name || "未分類公司";
      if (!grouped.has(companyName)) {
        grouped.set(companyName, []);
      }
      grouped.get(companyName)!.push(report);
    });

    return Array.from(grouped.entries())
      .sort((a, b) => a[0].localeCompare(b[0], "zh-TW"))
      .map(([companyName, reports]) => ({
        companyName: companyName,
        reports,
      }));
  };

  // 格式化日期範圍 YYYYMMDD -> YYYY-MM-DD
  const formatDateRange = (startDate: string, endDate: string, week: number) => {
    const formatDate = (dateStr: string) => {
      if (!dateStr || dateStr.length !== 8) return "";
      return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`;
    };

    const start = formatDate(startDate);
    const end = formatDate(endDate);

    if (start && end) {
      return `第 ${week} 週 (${start}~ ${end})`;
    }
    return `第 ${week} 週`;
  };

  // 渲染轉寄狀態
  const renderForwardedStatus = (report: WeeklyReport) => {
    // 別人轉寄給我的
    if (report.is_forwarded_to_me) {
      return (
        <div className="flex items-center justify-center gap-0.5">
          <img
            src="/MyReportAI/isforward.png"
            alt="轉寄給我"
            className="w-6 h-6 flex-shrink-0"
          />
        </div>
      );
    }

    // 自己轉寄出去的
    if (report.is_forwarded) {
      return (
        <div className="flex items-center justify-center gap-0.5">
          <img
            src="/MyReportAI/forward.png"
            alt="我轉寄的"
            className="w-6 h-6 flex-shrink-0"
          />
        </div>
      );
    }

    return <div className="flex items-center justify-center gap-0.5"></div>;
  };

  // 渲染回應狀態
  const renderResponseStatus = (report: WeeklyReport) => {
    const replyCount = report.reply_count || 0;
    const replierCount = report.replier_count || 0;

    if (replyCount === 0) {
      return null;
    } else if (replyCount === replierCount) {
      // 只有自己回應
      return (
        <img
          src="/MyReportAI/purple_heart.gif"
          alt="自己回應"
          className="w-6 h-6"
        />
      );
    } else if (replierCount === 0) {
      // 只有別人回應
      return (
        <img
          src="/MyReportAI/red_heart.gif"
          alt="有人回應"
          className="w-6 h-6"
        />
      );
    } else if (replyCount > replierCount) {
      // 雙方都有回應
      return (
        <img src="/MyReportAI/hearts.gif" alt="雙方回應" className="w-6 h-6" />
      );
    }

    return null;
  };

  // 渲染內容狀態
  const renderContentStatus = (report: WeeklyReport) => {
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
            title="此週報包含附件"
          />
        )}
      </div>
    );
  };

  // 公司標題組件
  const CompanyHeader: React.FC<{ companyName: string }> = ({
    companyName,
  }) => (
    <div className="bg-gradient-to-r from-blue-100 to-blue-50 border-b-2 border-blue-300 px-4 py-3">
      <h3 className="text-base md:text-lg font-bold text-gray-800">
        {companyName}
      </h3>
    </div>
  );

  // 渲染單一週報行
  const renderReportRow = (report: WeeklyReport) => {
    const weeklyPeriod = formatDateRange(report.start_date, report.end_date, report.week);

    return (
      <tr key={report.id} className="hover:bg-gray-50">
        <td className="px-1 sm:px-2 md:px-3 py-2.5 whitespace-nowrap">
          <div className="flex items-center justify-center gap-1 flex-col sm:flex-row">
            {renderForwardedStatus(report)}
            {renderResponseStatus(report)}
          </div>
        </td>
        <td className="px-1 sm:px-2 md:px-3 py-2.5">
          <div
            className="text-sm sm:text-base font-medium text-gray-900 truncate max-w-[120px] sm:max-w-[140px] md:max-w-[160px]"
            title={report.employee.name}
          >
            {report.employee.name}
          </div>
          {/* 在小螢幕上顯示部門和週報（因為md以下會隱藏這些列） */}
          <div className="md:hidden mt-1">
            <div className="text-xs text-gray-500 truncate max-w-[120px] sm:max-w-[140px]">
              {report.employee.department_name}
            </div>
            <div
              onClick={() => {
                if (onSelectEmployee) {
                  onSelectEmployee(
                    {
                      id: report.employee.id,
                      empno: report.employee.empno,
                      name: report.employee.name,
                      department_no: report.employee.department_no,
                      department_name: report.employee.department_name,
                    },
                    report.id
                  );
                }
              }}
              className="text-xs sm:text-sm text-blue-600 hover:text-blue-900 cursor-pointer hover:bg-blue-50 px-1 py-0.5 rounded transition-colors truncate max-w-[120px] sm:max-w-[140px] block"
              title={weeklyPeriod}
            >
              {weeklyPeriod}
            </div>
          </div>
        </td>
        {/* 部門列 - 只在md及以上顯示 */}
        <td className="hidden md:table-cell px-2 sm:px-3 md:px-4 py-2">
          <div className="text-sm md:text-base text-gray-700 truncate">
            <span className="truncate block">{report.employee.department_name}</span>
          </div>
        </td>
        {/* 週報(週期)列 - 只在md及以上顯示 */}
        <td className="hidden md:table-cell px-2 sm:px-3 md:px-4 py-2">
          <div
            onClick={() => {
              if (onSelectEmployee) {
                onSelectEmployee(
                  {
                    id: report.employee.id,
                    empno: report.employee.empno,
                    name: report.employee.name,
                    department_no: report.employee.department_no,
                    department_name: report.employee.department_name,
                  },
                  report.id
                );
              }
            }}
            className="text-sm md:text-base text-blue-600 hover:text-blue-900 cursor-pointer hover:bg-blue-50 p-2 rounded transition-colors truncate block"
          >
            <span className="truncate block">{weeklyPeriod}</span>
          </div>
        </td>
        <td className="px-1 sm:px-2 md:px-3 py-2.5 text-center whitespace-nowrap">
          {renderContentStatus(report)}
        </td>
        <td className="px-1 sm:px-2 md:px-3 py-2.5 text-center whitespace-nowrap">
          {/* 週報暫時不提供編輯/刪除功能 */}
        </td>
      </tr>
    );
  };

  // 渲染按公司分組的週報區塊
  const renderGroupedReportsSection = (
    reports: WeeklyReport[],
    sectionTitle?: string,
    headerBgColor?: string
  ) => {
    if (reports.length === 0) {
      return null;
    }

    const groupedReports = groupReportsByCompany(reports);

    return (
      <>
        {/* 區塊總標題（可選） */}
        {sectionTitle && headerBgColor && (
          <div className={`${headerBgColor} px-4 py-3 rounded-t-lg mb-2`}>
            <h2 className="text-lg font-bold text-gray-700">{sectionTitle}</h2>
          </div>
        )}

        {/* 各公司分組 */}
        {groupedReports.map(
          ({ companyName, reports: companyReports }, index) => (
            <div
              key={companyName}
              className={`bg-white border border-gray-200 rounded-lg overflow-hidden ${
                index > 0 ? "mt-6" : "mt-0"
              }`}
            >
              {/* 公司標題 */}
              <CompanyHeader companyName={companyName} />

              {/* 公司內的週報表格 */}
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-1 sm:px-2 md:px-3 py-2 text-center text-xs font-medium text-gray-700 uppercase tracking-wider w-12 sm:w-16">
                      狀態
                    </th>
                    <th className="px-1 sm:px-2 md:px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider w-20 sm:w-24 md:w-32">
                      姓名
                    </th>
                    <th className="hidden md:table-cell px-2 md:px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider w-32">
                      部門
                    </th>
                    <th className="hidden md:table-cell px-2 md:px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                      週報(週期)
                    </th>
                    <th className="px-1 sm:px-2 md:px-3 py-2 text-center text-xs font-medium text-gray-700 uppercase tracking-wider w-12 sm:w-16">
                      內容
                    </th>
                    <th className="px-1 sm:px-2 md:px-3 py-2 text-center text-xs font-medium text-gray-700 uppercase tracking-wider w-12 sm:w-16">
                      編輯
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {companyReports.map((report) => renderReportRow(report))}
                </tbody>
              </table>
            </div>
          )
        )}
      </>
    );
  };

  return (
    <div className="p-2 sm:p-4 md:p-6">
      <div className="mb-4 sm:mb-6">
        <h2 className="text-lg sm:text-xl md:text-2xl font-bold text-gray-900 mb-3 sm:mb-4">
          週報首頁
        </h2>

        <WeekSelector
          selectedYear={selectedYear}
          selectedWeek={selectedWeek}
          onChange={handleWeekChange}
          className="w-full"
        />
      </div>

      {/* Loading 狀態：只顯示在列表區域 */}
      {isLoading ? (
        <div className="text-center py-16 text-gray-500 bg-white border border-gray-200 rounded-lg">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-teal-500 mb-2"></div>
          <p>載入週報中...</p>
        </div>
      ) : (
        <>
          {/* 區塊1: 轉寄給我的週報 (按部門分組) */}
          {renderGroupedReportsSection(
            forwardedReports,
            "轉寄給我的週報",
            "bg-blue-100"
          )}

          {/* 區塊2: 週報 (按部門分組，不顯示區塊標題) */}
          {renderGroupedReportsSection(subordinateReports)}

          {/* 無資料提示 */}
          {subordinateReports.length === 0 && forwardedReports.length === 0 && (
            <div className="text-center py-16 text-gray-500 bg-white border border-gray-200 rounded-lg">
              <p>本週沒有任何相關的週報。</p>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default WeeklyEmployeeListTab;
