// frontend/src/App.tsx

import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate, useLocation, useSearchParams } from "react-router-dom";
import { LogOut } from "lucide-react";
import { toast } from "react-hot-toast";
// ✅ 週報系統 - 只保留週報相關組件
import EmployeeDetailTab from "./components/EmployeeDetailTab"; // 共用詳情頁面
import WeeklyReportTab from "./components/WeeklyReportTab";
import WeeklyEmployeeListTab from "./components/WeeklyEmployeeListTab";
import { useAuth } from "./hooks/useAuth";
import { Toaster } from "react-hot-toast";
import { getCompanyLogo, getCompanyName } from "./utils/companyLogo";

// --- Interface Definitions ---
export interface Project {
  id: number;
  planno: string;
  plan_subj_c: string; // 專案名稱
  pm_empno: string; // 專案經理工號
  is_active: boolean;
  department_id?: number;
}
export interface FileAttachment {
  id: number;
  name: string;
  type: string;
  size: number;
  url: string;
  file_path?: string; // ✅ CommonAPI 回傳的相對路徑（用於ATT_FILE2）
  is_selected_for_ai?: boolean;
}
export interface WorkRecord {
  id: number;
  content: string;
  created_at: string;
  project: Project;
  files: FileAttachment[];
  execution_time_minutes: number;
}
export interface FileForUpload extends Omit<FileAttachment, "id"> {
  is_selected_for_ai: boolean;
}
export interface WorkRecordCreate {
  content: string;
  project_id?: number;
  execution_work_id?: number;
  work_item_id?: number;
  service_company_id?: number;
  service_target_id?: number;
  files: FileForUpload[];
  execution_time_minutes: number;
}
export interface ConsolidatedReport {
  daily_no: string; // 添加 daily_no 字段
  sopno?: string; // 添加 sopno 字段用於精確識別記錄
  project: Project;
  execution_work_id?: number; // 執行工作ID
  execution_work_name?: string;
  work_item_ids?: number[]; // 工作項目ID列表
  work_item_name?: string;
  service_cocode?: string; // 服務公司代碼
  service_company_name?: string; // 服務公司中文名稱
  service_empno?: string; // 服務對象員工編號
  service_target_name?: string; // 服務對象名稱
  service_target_cocode?: string; // 服務對象公司別
  service_deptno?: string; // 服務對象部門
  content: string;
  files: FileAttachment[];
  record_count: number;
  ai_content: string | null;
  total_execution_time_minutes?: number;
  xdate?: string; // 最後修改日期 (YYYYMMDD)
  xtime?: string; // 最後修改時間 (HH:MM:SS)
}
export interface EmployeeInList {
  id: number;
  name: string;
  department_no?: string;
  department_name?: string;
  pending_reports_count: number;
}
export interface EmployeeSummary {
  id: number;
  name: string;
  empnamec?: string;
  department_no?: string;
  department_name?: string;
}
export interface DailyReport {
  id: number;
  date: string;
  status: string;
  rating: number | null;
  feedback: string | null;
  consolidated_content: ConsolidatedReport[];
  employee: EmployeeSummary;
  comments_count?: number;
  reply_count?: number;
}
export interface Employee {
  id: number;
  name: string;
  department_no?: string;
  department_name?: string;
  reports: DailyReport[];
}
export interface EmployeeForUser {
  id: number;
  empno: string;
  empnamec: string;
  dutyscript?: string; // 職稱
  deptabbv?: string; // 部門簡稱
  cocode?: string; // 公司代碼
}

export interface ExecutionWork {
  id: number;
  name: string;
  project_id: number;
  is_active: boolean;
}

export interface WorkItem {
  id: number;
  name: string;
  execution_work_id: number;
  is_active: boolean;
}

export interface ServiceCompany {
  id: number;
  name: string;
  is_active: boolean;
}

export interface ServiceTarget {
  id: number;
  name: string;
  company_id?: number;
  is_active: boolean;
}

export interface User {
  id: number;
  email: string;
  name: string;
  is_active: boolean;
  is_supervisor: boolean;
  employee?: EmployeeForUser;
}
function App() {
  const { user, logout, authFetch } = useAuth(); // ✅ 從 AuthContext 獲取全域狀態
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [activeTab, setActiveTab] = useState<"weekly" | "weeklyList">("weekly"); // ✅ 預設為週報編輯

  const [selectedEmployee, setSelectedEmployee] =
    useState<EmployeeInList | null>(null);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);

  // ✅ 使用 ref 追蹤已載入的 report ID，避免重複查詢
  const loadedReportRef = useRef<number | null>(null);

  // ✅ 週報系統的標籤切換函數
  const changeTab = useCallback(
    (tab: "weekly" | "weeklyList") => {
      setActiveTab(tab);
      setSelectedEmployee(null);
      setSelectedReportId(null);

      // ✅ 只有在切換到 weeklyList (週報首頁) 時才保留參數
      if (tab === "weeklyList") {
        const yearParam = searchParams.get("year");
        const weekParam = searchParams.get("week");
        const url =
          yearParam && weekParam
            ? `?tab=${tab}&year=${yearParam}&week=${weekParam}`
            : `?tab=${tab}`;
        navigate(url, { replace: false });
      } else {
        // 切換到週報編輯時，不帶參數
        navigate(`?tab=${tab}`, { replace: false });
      }
    },
    [navigate, searchParams]
  );

  // ✅ 週報系統：選擇員工查看詳情
  const handleSelectEmployee = (employee: EmployeeInList, reportId: number) => {
    setSelectedEmployee(employee);
    setSelectedReportId(reportId);
    setActiveTab("weeklyList"); // 保持在週報首頁模式

    // 保留當前的週次參數
    const yearParam = searchParams.get("year");
    const weekParam = searchParams.get("week");
    const url =
      yearParam && weekParam
        ? `?tab=weeklyList&year=${yearParam}&week=${weekParam}&employee=${employee.id}&report=${reportId}`
        : `?tab=weeklyList&employee=${employee.id}&report=${reportId}`;

    navigate(url, { replace: false });
  };

  // ✅ 週報系統：從詳情返回列表
  const handleBackFromDetail = () => {
    setSelectedEmployee(null);
    setSelectedReportId(null);
    setActiveTab("weeklyList");

    // 保留當前的週次參數
    const yearParam = searchParams.get("year");
    const weekParam = searchParams.get("week");
    const url =
      yearParam && weekParam
        ? `?tab=weeklyList&year=${yearParam}&week=${weekParam}`
        : "?tab=weeklyList";

    navigate(url, { replace: false });
  };

  // ✅ 週報系統：審閱完成後返回列表
  const handleReviewCompleted = () => {
    setSelectedEmployee(null);
    setSelectedReportId(null);
    setActiveTab("weeklyList");

    // 保留當前的週次參數
    const yearParam = searchParams.get("year");
    const weekParam = searchParams.get("week");
    const url =
      yearParam && weekParam
        ? `?tab=weeklyList&year=${yearParam}&week=${weekParam}`
        : "?tab=weeklyList";

    navigate(url, { replace: false });
  };

  // ✅ 週報系統：移除日報上傳完成處理
  // 原日報系統的 handleUploadComplete 已移除

  // ✅ 週報系統：移除日報寫入狀態刷新
  // 週報沒有時間限制，不需要檢查寫入狀態

  // ✅ 週報系統：監聽 URL 參數變化並同步狀態
  useEffect(() => {
    const tab = searchParams.get("tab") as "weekly" | "weeklyList" | null;
    const reportParam = searchParams.get("report");
    const employeeParam = searchParams.get("employee");

    // ✅ 同步 tab（週報系統）
    if (tab) {
      if (tab !== activeTab) {
        setActiveTab(tab);
      }
    } else {
      // 如果沒有 tab 參數，設置預設值為週報編輯
      if (activeTab !== "weekly") {
        setActiveTab("weekly");
      }
      // 只在沒有任何參數時設置預設 URL
      if (!searchParams.toString()) {
        navigate("?tab=weekly", { replace: true });
      }
    }

    // 同步 report - 週報系統可以只有 report 參數（從信件連結進入）
    if (reportParam) {
      const reportId = parseInt(reportParam);
      if (reportId !== selectedReportId) {
        setSelectedReportId(reportId);
      }
      // 確保 tab 是 weeklyList（從信件連結進入時可能沒有 tab 參數）
      if (activeTab !== "weeklyList") {
        setActiveTab("weeklyList");
      }
    } else {
      // 如果 URL 沒有 report，清空狀態
      if (selectedReportId !== null) {
        setSelectedReportId(null);
      }
      if (selectedEmployee !== null) {
        setSelectedEmployee(null);
      }
      // 清空 loadedReportRef
      if (loadedReportRef.current !== null) {
        loadedReportRef.current = null;
      }
    }
  }, [searchParams, navigate]); // 簡化依賴，只監聽 URL 變化

  // ✅ 週報系統：移除獲取員工詳細資訊的 API 調用
  // EmployeeDetailTab 已經通過 reportId 獲取所有需要的資訊
  // selectedEmployee 狀態只用於從列表選擇員工時的過渡，不需要額外的 API 調用

  // ✅ 週報系統：移除寫入狀態限制（週報沒有時間限制）
  // 原日報系統的寫入狀態檢查已移除

  // 處理週報上傳完成後的跳轉
  const handleWeeklyUploadComplete = useCallback(
    (year: number, week: number) => {
      setActiveTab("weeklyList");
      navigate(`?tab=weeklyList&year=${year}&week=${week}`, { replace: false });
    },
    [navigate]
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <Toaster
        position="top-center"
        reverseOrder={false}
        toastOptions={{
          success: {
            duration: 3000,
          },
          error: {
            duration: 5000,
          },
          style: {
            background: "#363636",
            color: "#fff",
          },
        }}
      />
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* 桌面版：單行佈局 (≥ lg) */}
          <div className="hidden lg:flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <div className="w-40 h-13 rounded-lg flex items-center justify-center">
                <img
                  src={getCompanyLogo(user?.employee?.cocode)}
                  alt="業務日誌"
                  className="w-40 h-13 rounded-lg object-contain"
                  onError={(e) => {
                    e.currentTarget.src = "/MyReportAI_Weekly/top_logoA.jpg";
                    console.log("圖片載入失敗，使用預設 logo");
                  }}
                />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">
                  業務週報
                </h1>
                <p className="text-sm text-gray-500">
                  {getCompanyName(user?.employee?.cocode)}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex space-x-1">
                {/* ✅ 週報編輯 */}
                <button
                  onClick={() => changeTab("weekly")}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                    activeTab === "weekly"
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  週報編輯
                </button>

                {/* ✅ 週報首頁 */}
                <button
                  onClick={() => changeTab("weeklyList")}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                    activeTab === "weeklyList"
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  週報首頁
                </button>
              </div>
              <div className="flex items-center space-x-3">
                <div className="text-right">
                  <p className="text-base font-medium text-gray-900">
                    {user?.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {user?.employee?.dutyscript || "員工"}
                  </p>
                </div>
                <button
                  onClick={logout}
                  className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg"
                  title="登出"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>

          {/* 平板/手機版：兩行佈局 (< lg) */}
          <div className="lg:hidden">
            {/* 第一行：Logo + 公司名稱 + 使用者資訊 + 登出 */}
            <div className="flex items-center justify-between h-16 border-b border-gray-100">
              <div className="flex items-center space-x-2 flex-1 min-w-0">
                <div className="w-32 sm:w-36 h-11 sm:h-12 rounded-lg flex items-center justify-center flex-shrink-0">
                  <img
                    src={getCompanyLogo(user?.employee?.cocode)}
                    alt="業務日誌"
                    className="w-32 sm:w-36 h-11 sm:h-12 rounded-lg object-contain"
                    onError={(e) => {
                      e.currentTarget.src = "/MyReportAI_Weekly/top_logoA.jpg";
                      console.log("圖片載入失敗，使用預設 logo");
                    }}
                  />
                </div>
                <div className="flex-1 min-w-0 hidden sm:block">
                  <h1 className="text-base font-semibold text-gray-900 truncate">
                    業務週報
                  </h1>
                  <p className="text-xs text-gray-500 truncate">
                    {getCompanyName(user?.employee?.cocode)}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2 flex-shrink-0">
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900 truncate max-w-[100px] sm:max-w-[150px]">
                    {user?.name}
                  </p>
                  <p className="text-xs text-gray-500 truncate">
                    {user?.employee?.dutyscript || "員工"}
                  </p>
                </div>
                <button
                  onClick={logout}
                  className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg flex-shrink-0"
                  title="登出"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* 第二行：導航按鈕 */}
            <div className="flex items-center justify-center h-12 sm:h-14">
              <div className="flex space-x-1 sm:space-x-2">
                {/* ✅ 週報編輯 */}
                <button
                  onClick={() => changeTab("weekly")}
                  className={`px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium rounded-lg transition-colors ${
                    activeTab === "weekly"
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  週報編輯
                </button>

                {/* ✅ 週報首頁 */}
                <button
                  onClick={() => changeTab("weeklyList")}
                  className={`px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium rounded-lg transition-colors ${
                    activeTab === "weeklyList"
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  週報首頁
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 bg-gray-50 min-h-screen">
        {/* ✅ 週報系統內容區域 */}

        {/* 週報編輯 */}
        {activeTab === "weekly" && (
          <WeeklyReportTab
            key="weekly-report"
            onUploadComplete={handleWeeklyUploadComplete}
          />
        )}

        {/* 週報首頁（列表） */}
        {activeTab === "weeklyList" && !selectedReportId && (
          <WeeklyEmployeeListTab
            key="weekly-employee-list"
            onSelectEmployee={handleSelectEmployee}
          />
        )}

        {/* 週報詳情（複用詳情頁面） */}
        {activeTab === "weeklyList" && selectedReportId && (
          <EmployeeDetailTab
            key={`weekly-detail-${selectedReportId}`}
            reportId={selectedReportId}
            onBack={handleBackFromDetail}
            onReviewCompleted={handleReviewCompleted}
          />
        )}
      </main>
    </div>
  );
}
export default App;
