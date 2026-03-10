// frontend/src/components/EmployeeDetailTab.tsx

import React, { useState, useEffect, useCallback } from "react";
import { ArrowLeft, Star } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import ChatInterface from "./ChatInterface";
import AttachedFilesDisplay from "./AttachedFilesDisplay";
import type { SupervisorApprovalInfo } from "../types/supervisor";
import ForwardSelector from "./ForwardSelector";
import { TypographyClasses } from "../styles/typography";
import OverdueARTable from "./OverdueARTable";
import RevenueTable from "./RevenueTable";
import {
  OverdueARData,
  RevenueData,
  ShowWeeklyReportResponse,
} from "../services/types";
import { WeeklyReportApi } from "../services/weeklyReportApi";
import { processHtmlImageUrls } from "../utils/urlUtils";

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
  // 週報詳情資料
  const [weeklyReportData, setWeeklyReportData] = useState<
    ShowWeeklyReportResponse | null | false
  >(null);
  const [approvals, setApprovals] = useState<SupervisorApprovalInfo[]>([]);
  const [reviewers, setReviewers] = useState<string[]>([]); // 可評分主管工號陣列
  const [isLoading, setIsLoading] = useState(true);
  const [selectedForwardUsers, setSelectedForwardUsers] = useState<string[]>(
    []
  );
  // 報告作者資訊
  const [reportAuthor, setReportAuthor] = useState<{
    empno: string;
    empname: string;
  } | null>(null);
  const { authFetch } = useAuth();

  // 逾期應收帳款和營收達成率資料
  const [overdueARData, setOverdueARData] = useState<OverdueARData[]>([]);
  const [revenueData, setRevenueData] = useState<RevenueData[]>([]);
  const [isLoadingTables, setIsLoadingTables] = useState(false);

  // 從 URL 獲取 status 和 replyid 參數（從郵件進入時使用）
  const urlParams = new URLSearchParams(window.location.search);
  const status = urlParams.get("status") || undefined;
  const replyid = urlParams.get("replyid") || undefined;

  const fetchReportDetails = useCallback(async () => {
    setIsLoading(true);
    try {
      // 使用 reportId 作為 weekly_no 調用週報詳情 API
      const weeklyNo = String(reportId);
      const response: ShowWeeklyReportResponse =
        await WeeklyReportApi.getWeeklyReportDetail(weeklyNo, authFetch);

      if (
        response.ResponseNo === "0000" &&
        response.ResponseData?.weeklyReportDetails?.length === 0
      ) {
        setWeeklyReportData(false);
      } else if (response.ResponseNo === "0000" && response.ResponseData) {
        setWeeklyReportData(response);

        // 提取作者資訊
        const master = response.ResponseData.weeklyReportMaster;
        if (master.empno && master.XUSER) {
          setReportAuthor({
            empno: String(master.empno).padStart(5, "0"),
            empname: master.XUSER,
          });
        }

        // 從 weeklyReportReplies 提取評分資訊
        const replies = response.ResponseData.weeklyReportReplies || [];
        const approvalsData: SupervisorApprovalInfo[] = replies
          .filter((reply) => reply.score && reply.score !== "") // 只保留有評分的回覆
          .map((reply, index) => ({
            supervisor_id: index + 1,
            supervisor_name: reply.xuser || "未知主管",
            supervisor_empno: reply.empno
              ? String(reply.empno).padStart(5, "0")
              : "00000",
            status: "approved" as const,
            approved_at:
              reply.xdate && reply.xtime
                ? `${reply.xdate.replace(
                    /(\d{4})(\d{2})(\d{2})/,
                    "$1-$2-$3"
                  )} ${reply.xtime}`
                : undefined,
            rating: reply.score ? parseInt(reply.score) : undefined,
            feedback: reply.memo || undefined,
          }));

        setApprovals(approvalsData);

        // 提取可評分主管名單（從 weeklyReportMaster 中）
        setReviewers(response.ResponseData.weeklyReportMaster.reviewers || []);
      } else {
        console.error("獲取週報詳情失敗:", response.ResponseNa);
        setWeeklyReportData(null);
      }
    } catch (error) {
      console.error("無法獲取週報詳情:", error);
      setWeeklyReportData(null);
    } finally {
      setIsLoading(false);
    }
  }, [reportId, authFetch]);

  useEffect(() => {
    // 組件掛載時滾動到頂部
    window.scrollTo(0, 0);
    fetchReportDetails();
  }, [reportId, fetchReportDetails]);

  // 載入逾期應收帳款和營收達成率資料（使用週報作者的工號、年份和週次）
  const loadTableData = useCallback(async () => {
    if (!authFetch || !weeklyReportData || weeklyReportData === false) return;

    const reportYear = weeklyReportData.ResponseData?.weeklyReportMaster?.YY;
    const reportWeek =
      weeklyReportData.ResponseData?.weeklyReportMaster?.Week_No;
    const reportEmpno =
      weeklyReportData.ResponseData?.weeklyReportMaster?.empno;

    if (!reportYear || !reportWeek || !reportEmpno) return;

    // 將工號補齊為 5 位數
    const empnoStr = String(reportEmpno).padStart(5, "0");

    setIsLoadingTables(true);
    try {
      // 同時載入兩個 API 的資料（使用該週報作者的工號、年份和週次）
      const [overdueARResult, revenueResult] = await Promise.allSettled([
        WeeklyReportApi.getOverdueAR(
          Number(reportYear),
          Number(reportWeek),
          authFetch,
          empnoStr
        ),
        WeeklyReportApi.getRevenue(
          Number(reportYear),
          Number(reportWeek),
          authFetch,
          empnoStr
        ),
      ]);

      // 處理逾期應收帳款資料
      if (overdueARResult.status === "fulfilled") {
        const data = overdueARResult.value?.ResponseData || [];
        setOverdueARData(data);
      } else {
        console.warn("載入逾期應收帳款失敗:", overdueARResult.reason);
        setOverdueARData([]);
      }

      // 處理營收達成率資料
      if (revenueResult.status === "fulfilled") {
        const data = revenueResult.value?.ResponseData || [];
        setRevenueData(data);
      } else {
        console.warn("載入營收達成率失敗:", revenueResult.reason);
        setRevenueData([]);
      }
    } catch (error) {
      console.error("載入表格資料失敗:", error);
      // 不顯示錯誤訊息，因為不是所有人都會有這些資料
    } finally {
      setIsLoadingTables(false);
    }
  }, [authFetch, weeklyReportData]);

  useEffect(() => {
    loadTableData();
  }, [loadTableData]);

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
    return <div className="p-6 text-center">載入週報詳情中...</div>;
  }
  if (weeklyReportData === false) {
    // 權限不足：API 回傳成功但 weeklyReportDetails 為空
    return (
      <div className="p-6 text-center">
        <div className="text-gray-500 mb-4">您沒有權限查看此週報。</div>
        <button
          onClick={onBack}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          返回
        </button>
      </div>
    );
  }
  if (!weeklyReportData || !weeklyReportData.ResponseData) {
    return <div className="p-6 text-center">找不到指定的週報。</div>;
  }

  const { weeklyReportMaster, weeklyReportDetails, weeklyReportReplies } =
    weeklyReportData.ResponseData;

  return (
    <div className="p-2 sm:p-4 md:p-6">
      {/* 大螢幕：標題列 */}
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
              {weeklyReportMaster.empno &&
                String(weeklyReportMaster.empno).padStart(5, "0")}{" "}
              {weeklyReportMaster.XUSER} {weeklyReportMaster.YY}年 第
              {weeklyReportMaster.Week_No}週 週報
            </h2>
            <div className="text-base text-gray-500">
              {weeklyReportMaster.DEPTABBV || ""}
            </div>
          </div>
        </div>
        {/* 平均評分 - 右上角 */}
        <div className="flex items-center space-x-4">
          {approvals &&
            approvals.length > 0 &&
            (() => {
              const ratedApprovals = approvals.filter(
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
              {weeklyReportMaster.empno &&
                String(weeklyReportMaster.empno).padStart(5, "0")}{" "}
              {weeklyReportMaster.XUSER}
            </h2>
            <div className="text-xs sm:text-sm text-gray-500 truncate">
              {weeklyReportMaster.DEPTABBV || ""}
            </div>
            <div className="text-xs text-gray-500 mt-0.5">
              {weeklyReportMaster.YY}年 第{weeklyReportMaster.Week_No}週
            </div>
          </div>
        </div>

        {/* 平均評分 - 獨立一行 */}
        {approvals &&
          approvals.length > 0 &&
          (() => {
            const ratedApprovals = approvals.filter(
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
                <span className="text-xs sm:text-sm text-gray-600 font-medium whitespace-nowrap">
                  平均評分:
                </span>
                {renderFiveLevelStars(Math.round(clampedAvg))}
              </div>
            );
          })()}
      </div>

      {/* 逾期應收帳款和營收達成率表格 */}
      <RevenueTable data={revenueData} isLoading={isLoadingTables} />
      <OverdueARTable data={overdueARData} isLoading={isLoadingTables} />

      {/* 上方 - 週報內容 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3 sm:p-4 md:p-6 mb-4 sm:mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-4 mb-3 sm:mb-4">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 flex items-center">
            週報內容
          </h3>
        </div>
        <div className="space-y-3 sm:space-y-4">
          {weeklyReportDetails.map((detail, index) => (
            <div
              key={detail.seq || index}
              className="border border-gray-100 rounded-lg p-3 sm:p-4 min-w-0"
            >
              <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mb-2 sm:mb-3">
                {/* 工作項目標籤 */}
                {detail.job_item && (
                  <div className="inline-flex items-center px-2 sm:px-3 py-1 text-sm sm:text-base font-medium rounded-md bg-indigo-100 text-indigo-800">
                    <span className="truncate max-w-[200px] sm:max-w-none">
                      {detail.job_item}
                    </span>
                  </div>
                )}
                {/* 主旨標籤 */}
                {detail.subject && (
                  <div className="inline-flex items-center px-1.5 sm:px-2 py-0.5 sm:py-1 text-xs font-medium rounded-md bg-green-100 text-green-800">
                    <span className="truncate max-w-[200px] sm:max-w-none">
                      {detail.subject}
                    </span>
                  </div>
                )}
              </div>
              {/* 內容 */}
              <div
                className={TypographyClasses.richTextDisplay}
                dangerouslySetInnerHTML={{
                  __html: processHtmlImageUrls(detail.content || ""),
                }}
              />
              {/* 附件 */}
              <AttachedFilesDisplay
                files={detail.files}
                content={detail.content || ""}
              />
              {/* 建立時間 */}
              {detail.xdate && detail.xtime && (
                <div className="mt-2 text-right text-xs text-gray-400">
                  {detail.xdate.replace(/(\d{4})(\d{2})(\d{2})/, "$1/$2/$3")}{" "}
                  {detail.xtime}
                </div>
              )}
            </div>
          ))}
        </div>
        {/* 最後修改日期時間 */}
      </div>

      {/* 下方 - 回覆與評分區域 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-4 sm:mb-6 overflow-hidden">
        <div className="p-3 sm:p-4 md:p-6 border-b border-gray-200">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 flex items-center">
            回覆與評分
          </h3>
        </div>

        <ChatInterface
          initialComments={
            // ✅ 轉換 weeklyReportReplies 為 Comment[] 格式
            weeklyReportReplies
              ? weeklyReportReplies.map((reply, index) => ({
                  id: reply.reply_nos || index,
                  content: reply.memo || "",
                  created_at:
                    reply.xdate && reply.xtime
                      ? `${reply.xdate} ${reply.xtime}`
                      : "",
                  user_id: reply.empno ? String(reply.empno) : "",
                  author: {
                    id: reply.empno ? String(reply.empno) : "",
                    name: reply.xuser || "未知用戶",
                  },
                  rating: reply.score ? parseInt(reply.score) : undefined,
                  forwarded_to: undefined,
                  replies: [],
                }))
              : []
          }
          reportId={reportId}
          reportOwnerId={0}
          reportOwnerEmpno={weeklyReportMaster.empno || ""}
          reportOwnerName={weeklyReportMaster.XUSER || ""}
          reportAuthor={reportAuthor}
          className="min-h-[300px] sm:min-h-[400px]"
          reportStatus={
            weeklyReportMaster.reply_status === "Y" ? "reviewed" : "pending"
          }
          approvals={approvals}
          onReviewSubmitted={fetchReportDetails}
          onReviewCompleted={onReviewCompleted}
          selectedForwardUsers={selectedForwardUsers}
          onForwardUsersChange={setSelectedForwardUsers}
          urlStatus={status}
          urlReplyId={replyid}
          reviewers={reviewers}
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
