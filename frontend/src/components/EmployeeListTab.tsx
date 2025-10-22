// frontend/src/components/EmployeeListTab.tsx

import React, { useState, useEffect, useRef } from "react";
import type { DailyReport, EmployeeInList } from "../App";
import { useAuth } from "../hooks/useAuth";
import SupervisorDateBar from "./SupervisorDateBar";
import { toast } from "react-hot-toast";
import { useNavigate, useSearchParams } from "react-router-dom";

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
  is_forwarded: boolean; // 自己轉寄出去的 (from_empno = 登入者)
  attachments: string[];
  customers: Array<{ name: string; company: string } | null>;
  last_update: string | null;
  can_view_detail: boolean; // 是否可以查看詳情
  is_forwarded_to_me?: boolean; // 別人轉寄給我的 (來自 forwardedReports)
}

// API 回傳結構 (包含下屬日報與轉寄日報)
interface HomepageData {
  subordinate_reports: HomepageReport[];
  forwarded_reports: HomepageReport[];
}

interface EmployeeListTabProps {
  onSelectEmployee: (employee: EmployeeInList, reportId: number) => void;
}

const EmployeeListTab: React.FC<EmployeeListTabProps> = ({
  onSelectEmployee,
}) => {
  const [subordinateReports, setSubordinateReports] = useState<
    HomepageReport[]
  >([]);
  const [forwardedReports, setForwardedReports] = useState<HomepageReport[]>(
    []
  );
  const [currentUserEmpno, setCurrentUserEmpno] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [editableStatus, setEditableStatus] = useState<Record<string, boolean>>(
    {}
  );

  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const getDefaultDate = () => {
    const now = new Date();

    // 建立一個我們要回傳的日期，預設為今天
    const dateToReturn = new Date();

    // 檢查現在的小時是否早於下午 5 點 (17:00)
    // getHours() 回傳的是 0-23 的 24 小時制數字
    if (now.getHours() < 17) {
      // 如果早於下午 5 點，就將日期設定為昨天
      dateToReturn.setDate(dateToReturn.getDate() - 1);
    }

    // 如果時間已是 17:00 或更晚，if 條件不成立，
    // 就會直接回傳預設的今天日期
    return dateToReturn;
  };

  // ✅ 通用日期解析函數：支援 YYYY-MM-DD 和 YYYYMMDD 兩種格式
  const parseDateParam = (dateParam: string): Date | null => {
    if (!dateParam) return null;

    // 格式1: YYYY-MM-DD
    if (dateParam.includes("-")) {
      const [year, month, day] = dateParam.split("-").map(Number);
      if (year && month && day) {
        return new Date(year, month - 1, day, 12, 0, 0);
      }
    }
    // 格式2: YYYYMMDD
    else if (dateParam.length === 8) {
      const year = parseInt(dateParam.substring(0, 4));
      const month = parseInt(dateParam.substring(4, 6));
      const day = parseInt(dateParam.substring(6, 8));
      if (year && month && day) {
        return new Date(year, month - 1, day, 12, 0, 0);
      }
    }

    return null;
  };

  // ✅ 從 URL 參數讀取日期，如果沒有則使用當天
  const getInitialDate = () => {
    const dateParam = searchParams.get("date");
    if (dateParam) {
      const parsedDate = parseDateParam(dateParam);
      if (parsedDate) return parsedDate;
    }
    // 使用五點前顯示前一天的邏輯
    return getDefaultDate();
  };

  const [selectedDate, setSelectedDate] = useState<Date | null>(
    getInitialDate()
  );
  const { authFetch, user } = useAuth();

  // ✅ 使用 useRef 建立編輯狀態快取
  const editableStatusCache = useRef<Record<string, boolean>>({});

  useEffect(() => {
    if (user?.employee?.empno) {
      setCurrentUserEmpno(user.employee.empno);
    }
  }, [user]);

  // ✅ 監聽 URL 參數變化，同步日期狀態
  useEffect(() => {
    const dateParam = searchParams.get("date");
    console.log(`[EmployeeListTab] URL date 參數變化: ${dateParam}`);

    if (dateParam) {
      const urlDate = parseDateParam(dateParam);
      if (urlDate) {
        console.log(`[EmployeeListTab] ✅ 設定日期為: ${urlDate.toDateString()}`);
        // 使用函數式更新,確保比較的是最新狀態
        setSelectedDate(prevDate => {
          if (prevDate?.toDateString() !== urlDate.toDateString()) {
            console.log(`[EmployeeListTab] 日期已更新: ${prevDate?.toDateString()} -> ${urlDate.toDateString()}`);
            return urlDate;
          }
          console.log(`[EmployeeListTab] 日期相同,不更新: ${prevDate?.toDateString()}`);
          return prevDate;
        });
      }
    }
    // ✅ 修復:移除自動重置為預設日期的邏輯,避免覆蓋從其他頁面傳入的日期
  }, [searchParams]);

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

    // ✅ 使用 AbortController 來取消過期的請求
    const abortController = new AbortController();
    let isCancelled = false;

    const fetchHomepageReports = async () => {
      setIsLoading(true);
      // 確保使用本地日期，避免時區問題
      const year = selectedDate.getFullYear();
      const month = String(selectedDate.getMonth() + 1).padStart(2, "0");
      const day = String(selectedDate.getDate()).padStart(2, "0");
      const dateString = `${year}-${month}-${day}`;

      console.log(`[EmployeeListTab] 🔍 開始載入日報資料: ${dateString} (${selectedDate.toDateString()})`);

      try {
        // 使用新的日報首頁API
        const response = await authFetch(
          `/api/supervisor/daily-homepage?date=${dateString}`
        );

        // ✅ 檢查請求是否已被取消
        if (isCancelled) {
          console.log(`[EmployeeListTab] ⚠️ 請求已取消,忽略 ${dateString} 的回應`);
          return;
        }

        if (response.ok) {
          const data: HomepageData = await response.json();

          // ✅ 再次檢查請求是否已被取消(避免 JSON 解析後狀態改變)
          if (isCancelled) {
            console.log(`[EmployeeListTab] ⚠️ 請求已取消,忽略 ${dateString} 的資料更新`);
            return;
          }

          console.log(`[EmployeeListTab] ✅ 成功載入 ${dateString} 的資料`);

          setSubordinateReports(data.subordinate_reports || []);
          // 為轉寄日報標記 is_forwarded_to_me
          const markedForwardedReports = (data.forwarded_reports || []).map(
            (report) => ({
              ...report,
              is_forwarded_to_me: true,
            })
          );
          setForwardedReports(markedForwardedReports);

          // 檢查當天所有唯一日期的可編輯狀態 (合併兩組日報的日期)
          const allReports = [
            ...(data.subordinate_reports || []),
            ...(data.forwarded_reports || []),
          ];
          const uniqueDates = [
            ...new Set(
              allReports
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
          setSubordinateReports([]);
          setForwardedReports([]);
        }
      } catch (error: any) {
        // ✅ 忽略被取消的請求錯誤
        if (error.name === 'AbortError' || isCancelled) {
          console.log(`[EmployeeListTab] 請求已取消: ${dateString}`);
          return;
        }
        console.error("無法獲取日報首頁列表:", error);
        setSubordinateReports([]);
        setForwardedReports([]);
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };
    fetchHomepageReports();

    // ✅ Cleanup: 當 selectedDate 改變時,取消前一個請求
    return () => {
      console.log(`[EmployeeListTab] 🚫 取消請求 (日期改變)`);
      isCancelled = true;
      abortController.abort();
    };
  }, [selectedDate, authFetch]);

  const handleDateChange = (date: Date) => {
    setSelectedDate(date);
    // ✅ 同步更新 URL 參數
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    const dateString = `${year}-${month}-${day}`;
    navigate(`?tab=supervisor&date=${dateString}`, { replace: true });
  };

  // 處理刪除日報
  const handleDeleteReport = async (reportId: number, reportDate: string) => {
    if (!window.confirm("確定要刪除這份日報嗎？")) {
      return;
    }

    try {
      const response = await authFetch(`/api/records/${reportId}`, {
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
            const data: HomepageData = await refreshResponse.json();
            setSubordinateReports(data.subordinate_reports || []);
            // 為轉寄日報標記 is_forwarded_to_me
            const markedForwardedReports = (data.forwarded_reports || []).map(
              (report) => ({
                ...report,
                is_forwarded_to_me: true,
              })
            );
            setForwardedReports(markedForwardedReports);
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
    // 別人轉寄給我的 (is_forwarded_to_me) 使用 forward.gif
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

    // 自己轉寄出去的 (is_forwarded) 使用 forward.png
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

  // ✅ 已移除 renderSupervisionStatus - 前端未使用此功能

  if (isLoading) {
    return <div className="p-6 text-center">載入日報中...</div>;
  }

  // 渲染日報表格區塊 (包含表頭和內容)
  const renderReportsSection = (
    reports: HomepageReport[],
    title: string,
    bgColorClass: string
  ) => (
    <>
      <thead className={bgColorClass}>
        <tr>
          <th className="px-1 sm:px-2 md:px-3 py-2 text-center text-xs font-medium text-gray-700 uppercase tracking-wider w-12 sm:w-16">
            狀態
          </th>
          <th className="px-1 sm:px-2 md:px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider w-20 sm:w-24 md:w-32">
            員工
          </th>
          <th className="hidden md:table-cell px-2 md:px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
            執行項目
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
        {reports.map((report) => (
          <tr key={report.id} className="hover:bg-gray-50">
            <td className="px-1 sm:px-2 md:px-3 py-2.5 whitespace-nowrap">
              <div className="flex items-center justify-center gap-1 flex-col sm:flex-row">
                {renderFowardedStatus(report)}
                {renderResponseStatus(report)}
              </div>
            </td>
            <td className="px-1 sm:px-2 md:px-3 py-2.5">
              <div className="text-sm sm:text-base font-medium text-gray-900 truncate max-w-[120px] sm:max-w-[140px] md:max-w-[160px]" title={report.employee.name}>
                {report.employee.name}
              </div>
              {/* 在小螢幕上顯示執行項目（因為md以下會隱藏執行項目列） */}
              <div className="md:hidden mt-1">
                {report.can_view_detail ? (
                  <div
                    onClick={() => {
                      // ✅ 在導航到詳細頁前，先更新 URL 的日期參數
                      if (selectedDate) {
                        const year = selectedDate.getFullYear();
                        const month = String(selectedDate.getMonth() + 1).padStart(2, "0");
                        const day = String(selectedDate.getDate()).padStart(2, "0");
                        const dateString = `${year}-${month}-${day}`;
                        const currentUrl = new URL(window.location.href);
                        currentUrl.searchParams.set("date", dateString);
                        window.history.replaceState({}, "", currentUrl.toString());
                      }
                      onSelectEmployee(
                        {
                          id: report.employee.id,
                          name: report.employee.name,
                          department_name: report.employee.department_name,
                          department_no: report.employee.department_no,
                          pending_reports_count: 0,
                        },
                        report.id
                      );
                    }}
                    className="text-xs sm:text-sm text-blue-600 hover:text-blue-900 cursor-pointer hover:bg-blue-50 px-1 py-0.5 rounded transition-colors truncate max-w-[120px] sm:max-w-[140px] block"
                    title={report.sop_desc_c || "執行項目"}
                  >
                    {report.sop_desc_c || "執行項目"}
                    {report.emergency && (
                      <span className="ml-1 inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-red-100 text-red-800">
                        急
                      </span>
                    )}
                  </div>
                ) : (
                  <div className="text-xs sm:text-sm text-gray-400 px-1 py-0.5 truncate max-w-[120px] sm:max-w-[140px]" title={report.sop_desc_c || "執行項目"}>
                    {report.sop_desc_c || "執行項目"}
                    {report.emergency && (
                      <span className="ml-1 inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-red-100 text-red-800">
                        急
                      </span>
                    )}
                  </div>
                )}
              </div>
            </td>
            {/* 執行項目列 - 只在md及以上顯示 */}
            <td className="hidden md:table-cell px-2 sm:px-3 md:px-4 py-2 sm:py-3">
              {report.can_view_detail ? (
                <div
                  onClick={() => {
                    // ✅ 在導航到詳細頁前，先更新 URL 的日期參數
                    if (selectedDate) {
                      const year = selectedDate.getFullYear();
                      const month = String(selectedDate.getMonth() + 1).padStart(2, "0");
                      const day = String(selectedDate.getDate()).padStart(2, "0");
                      const dateString = `${year}-${month}-${day}`;
                      const currentUrl = new URL(window.location.href);
                      currentUrl.searchParams.set("date", dateString);
                      window.history.replaceState({}, "", currentUrl.toString());
                    }
                    onSelectEmployee(
                      {
                        id: report.employee.id,
                        name: report.employee.name,
                        department_name: report.employee.department_name,
                        department_no: report.employee.department_no,
                        pending_reports_count: 0,
                      },
                      report.id
                    );
                  }}
                  className="text-sm md:text-base text-blue-600 hover:text-blue-900 cursor-pointer hover:bg-blue-50 p-2 rounded transition-colors truncate block"
                >
                  <span className="truncate block">{report.sop_desc_c || "執行項目"}</span>
                  {report.emergency && (
                    <span className="ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                      緊急
                    </span>
                  )}
                </div>
              ) : (
                <div className="text-sm md:text-base text-gray-400 p-2 truncate">
                  <span className="truncate block">{report.sop_desc_c || "執行項目"}</span>
                  {report.emergency && (
                    <span className="ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                      緊急
                    </span>
                  )}
                </div>
              )}
            </td>
            <td className="px-1 sm:px-2 md:px-3 py-2.5 text-center whitespace-nowrap">
              {renderContentStatus(report)}
            </td>
            <td className="px-1 sm:px-2 md:px-3 py-2.5 text-center whitespace-nowrap">
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
                    <div className="flex items-center justify-center gap-1.5 sm:gap-2">
                      <button
                        onClick={() => handleEditReport(report.date)}
                        className="hover:opacity-75 transition-opacity"
                        title="編輯日報"
                      >
                        <img
                          src="/MyReportAI/edit.png"
                          alt="編輯"
                          className="w-5 h-5 sm:w-6 sm:h-6"
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
                          className="w-5 h-5 sm:w-6 sm:h-6"
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
    </>
  );

  return (
    <div className="p-2 sm:p-4 md:p-6">
      <div className="mb-4 sm:mb-6">
        <h2 className="text-lg sm:text-xl md:text-2xl font-bold text-gray-900 mb-3 sm:mb-4">日報首頁</h2>

        <SupervisorDateBar
          selectedDate={selectedDate}
          onChange={handleDateChange}
          className="w-full"
        />
      </div>

      {/* 區塊1: 轉寄給我的日報 (綠色表頭) */}
      {forwardedReports.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto mb-4 sm:mb-6">
          <table className="min-w-full divide-y divide-gray-200">
            {renderReportsSection(
              forwardedReports,
              "轉寄給我的日報",
              "bg-blue-100"
            )}
          </table>
        </div>
      )}

      {/* 區塊2: 日報 (藍色表頭) */}
      {subordinateReports.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto mb-4 sm:mb-6">
          <table className="min-w-full divide-y divide-gray-200">
            {renderReportsSection(subordinateReports, "日報", "bg-gray-100")}
          </table>
        </div>
      )}

      {/* 無資料提示 */}
      {subordinateReports.length === 0 &&
        forwardedReports.length === 0 &&
        !isLoading && (
          <div className="text-center py-16 text-gray-500 bg-white border border-gray-200 rounded-lg">
            <p>這天沒有任何相關的日報。</p>
          </div>
        )}
    </div>
  );
};
export default EmployeeListTab;
