// frontend/src/App.tsx

import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate, useLocation, useSearchParams } from "react-router-dom";
import { LogOut } from "lucide-react";
import { toast } from "react-hot-toast";
import DataInputTab from "./components/DataInputTab";
import DailyReportTab from "./components/DailyReportTab";
// import MyReportsTab from "./components/MyReportsTab"; // 已移除我的日報功能
// import AIDailyReportTab from './components/AIDailyReportTab';
// import ComprehensiveEditTab from './components/ComprehensiveEditTab';
import EmployeeListTab from "./components/EmployeeListTab";
import EmployeeDetailTab from "./components/EmployeeDetailTab";
import { useAuth } from "./hooks/useAuth";
import { Toaster } from "react-hot-toast";

interface WritingStatus {
  allowed: boolean;
  message: string;
  current_date: string;
  current_time: string;
  next_available_time: string;
  has_other_writable_dates?: boolean;
}
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
  const {
    user,
    logout,
    authFetch,
    hasSubordinates,
    writingStatus,
    refreshWritingStatus,
  } = useAuth(); // ✅ 從 AuthContext 獲取全域狀態
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [activeTab, setActiveTab] = useState<
    "input" | "daily" | "supervisor" | "ai" | "comprehensive"
  >("supervisor"); // 預設為日報首頁

  const [selectedEmployee, setSelectedEmployee] =
    useState<EmployeeInList | null>(null);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  // ✅ writingStatus 已移至 AuthContext，不再需要本地狀態

  // 全局日期狀態，讓隨筆紀錄頁和日報編輯頁共享
  const [globalSelectedDate, setGlobalSelectedDate] = useState<string | null>(
    null
  );

  // ✅ 使用 ref 追蹤已載入的 report ID，避免重複查詢
  const loadedReportRef = useRef<number | null>(null);

  // 添加歷史管理的標籤切換函數
  const changeTab = useCallback(
    (tab: "input" | "daily" | "supervisor" | "ai" | "comprehensive") => {
      setActiveTab(tab);
      setSelectedEmployee(null);
      setSelectedReportId(null);
      // 使用 navigate 更新 URL (相對於 basename)
      navigate(`?tab=${tab}`, { replace: false });
    },
    [navigate]
  );

  const handleSelectEmployee = (employee: EmployeeInList, reportId: number) => {
    setSelectedEmployee(employee);
    setSelectedReportId(reportId);
    setActiveTab("supervisor"); // 切換到審閱模式

    // 保留當前的日期參數（如果有的話）
    const dateParam = searchParams.get("date");
    const url = dateParam
      ? `?tab=supervisor&date=${dateParam}&employee=${employee.id}&report=${reportId}`
      : `?tab=supervisor&employee=${employee.id}&report=${reportId}`;

    // 使用 navigate 更新 URL (相對於 basename)
    navigate(url, {
      replace: false,
    });
  };

  const handleBackFromDetail = () => {
    setSelectedEmployee(null);
    setSelectedReportId(null);
    setActiveTab("supervisor");

    // 保留當前的日期參數（如果有的話）
    const dateParam = searchParams.get("date");
    const url = dateParam
      ? `?tab=supervisor&date=${dateParam}`
      : "?tab=supervisor";

    // 使用 navigate 返回列表頁 (相對於 basename)
    navigate(url, { replace: false });
  };

  const handleReviewCompleted = () => {
    // 主管評分完成後，跳轉回審閱列表
    setSelectedEmployee(null);
    setSelectedReportId(null);
    setActiveTab("supervisor");

    // 保留當前的日期參數（如果有的話）
    const dateParam = searchParams.get("date");
    const url = dateParam
      ? `?tab=supervisor&date=${dateParam}`
      : "?tab=supervisor";

    // 使用 navigate 返回列表頁 (相對於 basename)
    navigate(url, { replace: false });
    // ✅ 刷新寫入狀態，因為主管審閱會影響員工的編輯權限
    if (refreshWritingStatus) {
      const docDate = globalSelectedDate
        ? globalSelectedDate.replace(/-/g, "")
        : undefined;
      refreshWritingStatus(docDate);
    }
  };

  // 處理上傳完成後的跳轉
  const handleUploadComplete = useCallback(
    (uploadedDate: string) => {
      // 立即跳轉到日報首頁（supervisor tab）
      setActiveTab("supervisor");
      // 設定顯示上傳的那天日報
      setGlobalSelectedDate(uploadedDate);
      // 使用 navigate 更新 URL (相對於 basename)
      navigate(`?tab=supervisor&date=${uploadedDate}`, { replace: false });
    },
    [navigate]
  );

  // ✅ 修復: 使用 AuthContext 的 refreshWritingStatus，避免重複 API 呼叫
  useEffect(() => {
    if (refreshWritingStatus && user?.employee) {
      // 使用全局選中的日期，如果沒有則不傳入doc_date讓後端使用預設邏輯
      const docDate = globalSelectedDate
        ? globalSelectedDate.replace(/-/g, "")
        : undefined;
      refreshWritingStatus(docDate);
    }
  }, [refreshWritingStatus, user?.employee, globalSelectedDate]);

  // 監聽 URL 參數變化並同步狀態
  useEffect(() => {
    const tab = searchParams.get("tab") as
      | "input"
      | "daily"
      | "supervisor"
      | "ai"
      | "comprehensive"
      | null;
    const dateParam = searchParams.get("date");
    const reportParam = searchParams.get("report");
    const employeeParam = searchParams.get("employee");

    // 同步 tab
    if (tab) {
      if (tab !== activeTab) {
        setActiveTab(tab);
      }
    } else {
      // 如果沒有 tab 參數，設置預設值並更新 URL
      if (activeTab !== "supervisor") {
        setActiveTab("supervisor");
      }
      // 只在沒有任何參數時設置預設 URL
      if (!searchParams.toString()) {
        navigate("?tab=supervisor", { replace: true });
      }
    }

    // 同步日期
    if (dateParam && dateParam !== globalSelectedDate) {
      setGlobalSelectedDate(dateParam);
    }

    // 同步 report 和 employee - 必須同時存在或同時不存在
    if (reportParam && employeeParam) {
      const reportId = parseInt(reportParam);
      if (reportId !== selectedReportId) {
        setSelectedReportId(reportId);
      }
    } else {
      // 如果 URL 沒有 report 或 employee，清空狀態
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

  // 獲取員工詳細資訊
  useEffect(() => {
    if (!authFetch || !selectedReportId) return;

    // ✅ 如果已經載入過這個 report，就跳過
    if (loadedReportRef.current === selectedReportId) return;

    // ✅ 如果已經有正確的 employee 資料，也跳過
    if (selectedEmployee?.latest_report_id === selectedReportId) return;

    const fetchEmployeeInfo = async () => {
      try {
        const response = await authFetch(
          `/api/supervisor/reports/${selectedReportId}`
        );
        if (response.ok) {
          const reportData = await response.json();
          setSelectedEmployee({
            id: reportData.employee.id,
            empno: reportData.employee.empno,
            name: reportData.employee.name,
            latest_report_id: selectedReportId,
            latest_report_date: reportData.doc_date,
          });
          loadedReportRef.current = selectedReportId;
        }
      } catch (error) {
        console.error("無法獲取員工資訊:", error);
      }
    };
    fetchEmployeeInfo();
  }, [authFetch, selectedReportId]); // ✅ 移除 selectedEmployee 依賴

  // 當寫入狀態變化時，確保當前活動標籤是可用的
  useEffect(() => {
    if (writingStatus && !writingStatus.allowed) {
      // 如果不允許寫入，且當前在編輯標籤，切換到日報首頁
      if (activeTab === "input" || activeTab === "daily") {
        changeTab("supervisor");
      }
    }
  }, [writingStatus, activeTab, changeTab]);

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
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <div className="w-40 h-10 rounded-lg flex items-center justify-center max-w-40 min-w-40">
                <img
                  src="/MyReportAI/top_logoA.jpg"
                  alt="業務日誌"
                  className="w-40 h-10 rounded-lg max-w-40 min-w-40"
                />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">
                  業務日報
                </h1>
                <p className="text-sm text-gray-500">崇越科技</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex space-x-1">
                {/* 隨筆紀錄 - 只有在允許寫入時才顯示 */}
                {writingStatus?.allowed && (
                  <button
                    onClick={() => changeTab("input")}
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                      activeTab === "input"
                        ? "bg-green-100 text-green-700"
                        : "text-gray-600 hover:bg-gray-100"
                    }`}
                  >
                    隨筆紀錄
                  </button>
                )}

                {/* 日報編輯 - 只有在允許寫入時才顯示 */}
                {writingStatus?.allowed && (
                  <button
                    onClick={() => changeTab("daily")}
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                      activeTab === "daily"
                        ? "bg-green-100 text-green-700"
                        : "text-gray-600 hover:bg-gray-100"
                    }`}
                  >
                    日報編輯
                  </button>
                )}

                {/* 日報首頁 (所有用戶都可見) */}
                <button
                  onClick={() => changeTab("supervisor")}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                    activeTab === "supervisor"
                      ? "bg-green-100 text-green-700"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  日報首頁
                </button>
              </div>
              <div className="flex items-center space-x-3">
                <div className="text-right">
                  <p className="text-base font-medium text-gray-900">
                    {user?.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {user?.employee?.dutyscript ||
                      (hasSubordinates ? "主管" : "員工")}
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
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 bg-gray-50 min-h-screen">
        {/* 顯示寫入狀態消息 - 只在日報首頁列表顯示 */}
        {writingStatus &&
          !writingStatus.allowed &&
          !writingStatus.has_other_writable_dates &&
          activeTab === "supervisor" &&
          !selectedEmployee && (
            <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <svg
                    className="h-5 w-5 text-yellow-400"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-base text-yellow-700">
                    {writingStatus.message}
                  </p>
                </div>
              </div>
            </div>
          )}

        {/* 內容區域 */}
        {activeTab === "input" && (
          <DataInputTab
            key="data-input"
            selectedDate={globalSelectedDate}
            onDateChange={setGlobalSelectedDate}
          />
        )}
        {activeTab === "daily" && (
          <DailyReportTab
            key="daily-report"
            selectedDate={globalSelectedDate}
            onDateChange={setGlobalSelectedDate}
            onUploadComplete={handleUploadComplete}
            onSwitchToDaily={() => changeTab("daily")}
          />
        )}

        {/* 日報首頁區域 */}
        {activeTab === "supervisor" && !selectedEmployee && (
          <EmployeeListTab
            key="employee-list"
            onSelectEmployee={handleSelectEmployee}
          />
        )}
        {activeTab === "supervisor" && selectedEmployee && selectedReportId && (
          <EmployeeDetailTab
            key={`employee-detail-${selectedReportId}`}
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
