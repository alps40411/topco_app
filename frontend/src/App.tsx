// frontend/src/App.tsx

import { useState, useEffect } from "react";
import { Edit3, FileText, LogOut } from "lucide-react";
import DataInputTab from "./components/DataInputTab";
import DailyReportTab from "./components/DailyReportTab";
import MyReportsTab from "./components/MyReportsTab";
// import AIDailyReportTab from './components/AIDailyReportTab';
// import ComprehensiveEditTab from './components/ComprehensiveEditTab';
import EmployeeListTab from "./components/EmployeeListTab";
import EmployeeDetailTab from "./components/EmployeeDetailTab";
import { useAuth } from "./contexts/AuthContext";
import { useHasSubordinates } from "./hooks/useHasSubordinates";
import { Toaster } from "react-hot-toast";

interface EmployeeEditingStatus {
  can_edit_records: boolean;
  can_edit_reports: boolean;
  can_submit_report: boolean;
  message: string;
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
  files: FileForUpload[];
  execution_time_minutes: number;
}
export interface ConsolidatedReport {
  project: Project;
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
  const { user, logout, authFetch } = useAuth();
  const { hasSubordinates, loading: subordinatesLoading } =
    useHasSubordinates();
  const [activeTab, setActiveTab] = useState<
    "input" | "daily" | "myreports" | "supervisor" | "ai" | "comprehensive"
  >("input"); // 預設為隨筆紀錄

  const [selectedEmployee, setSelectedEmployee] =
    useState<EmployeeInList | null>(null);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [editingStatus, setEditingStatus] =
    useState<EmployeeEditingStatus | null>(null);

  const handleSelectEmployee = (employee: EmployeeInList, reportId: number) => {
    setSelectedEmployee(employee);
    setSelectedReportId(reportId);
    setActiveTab("supervisor"); // 切換到審閱模式
  };

  const handleBackFromDetail = () => {
    setSelectedEmployee(null);
    setSelectedReportId(null);
    // 保持在supervisor標籤
  };

  const handleReviewCompleted = () => {
    // 主管評分完成後，跳轉回審閱列表
    setSelectedEmployee(null);
    setSelectedReportId(null);
    // 刷新編輯狀態，因為主管審閱會影響員工的編輯權限
    fetchEditingStatus();
  };

  const fetchEditingStatus = async () => {
    if (!authFetch || !user?.employee) return;

    try {
      const response = await authFetch(
        "/api/supervisor/employee-editing-status"
      );
      if (response.ok) {
        const status: EmployeeEditingStatus = await response.json();
        setEditingStatus(status);
      }
    } catch (error) {
      console.error("獲取編輯狀態失敗:", error);
    }
  };

  useEffect(() => {
    if (authFetch && user?.employee) {
      fetchEditingStatus();
    }
  }, [authFetch, user?.employee]);

  // 當編輯狀態變化時，確保當前活動標籤是可用的
  useEffect(() => {
    if (editingStatus) {
      // 如果當前在不可編輯的標籤，切換到可用標籤
      if (activeTab === "input" && !editingStatus.can_edit_records) {
        if (editingStatus.can_edit_reports) {
          setActiveTab("daily");
        } else {
          setActiveTab("myreports");
        }
      } else if (activeTab === "daily" && !editingStatus.can_edit_reports) {
        if (editingStatus.can_edit_records) {
          setActiveTab("input");
        } else {
          setActiveTab("myreports");
        }
      }
    }
  }, [editingStatus, activeTab]);

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
              <div className="w-10 h-10 bg-green-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">TSC</span>
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">
                  TSC 業務日誌
                </h1>
                <p className="text-sm text-gray-500">崇越科技</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex space-x-1">
                {/* 隨筆紀錄 */}
                {editingStatus?.can_edit_records && (
                  <button
                    onClick={() => {
                      setActiveTab("input");
                      setSelectedEmployee(null);
                      setSelectedReportId(null);
                    }}
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                      activeTab === "input"
                        ? "bg-green-100 text-green-700"
                        : "text-gray-600 hover:bg-gray-100"
                    }`}
                  >
                    隨筆紀錄
                  </button>
                )}

                {/* 日報編輯 */}
                {editingStatus?.can_edit_reports && (
                  <button
                    onClick={() => {
                      setActiveTab("daily");
                      setSelectedEmployee(null);
                      setSelectedReportId(null);
                    }}
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                      activeTab === "daily"
                        ? "bg-green-100 text-green-700"
                        : "text-gray-600 hover:bg-gray-100"
                    }`}
                  >
                    日報編輯
                  </button>
                )}

                {/* 我的日報 */}
                <button
                  onClick={() => {
                    setActiveTab("myreports");
                    setSelectedEmployee(null);
                    setSelectedReportId(null);
                  }}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                    activeTab === "myreports"
                      ? "bg-green-100 text-green-700"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  我的日報
                </button>

                {/* 日報審閱 (僅主管) */}
                {!subordinatesLoading && hasSubordinates && (
                  <button
                    onClick={() => {
                      setActiveTab("supervisor");
                      setSelectedEmployee(null);
                      setSelectedReportId(null);
                    }}
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                      activeTab === "supervisor"
                        ? "bg-green-100 text-green-700"
                        : "text-gray-600 hover:bg-gray-100"
                    }`}
                  >
                    日報審閱
                  </button>
                )}
              </div>
              <div className="flex items-center space-x-3">
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900">
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
        {/* 顯示編輯狀態消息 */}
        {editingStatus &&
          !editingStatus.can_edit_records &&
          !editingStatus.can_edit_reports && (
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
                  <p className="text-sm text-yellow-700">
                    {editingStatus.message}
                  </p>
                </div>
              </div>
            </div>
          )}

        {/* 內容區域 */}
        {activeTab === "input" && editingStatus?.can_edit_records && (
          <DataInputTab />
        )}
        {activeTab === "daily" && editingStatus?.can_edit_reports && (
          <DailyReportTab />
        )}
        {activeTab === "myreports" && <MyReportsTab />}

        {/* 主管審閱區域 */}
        {activeTab === "supervisor" && !selectedEmployee && (
          <EmployeeListTab onSelectEmployee={handleSelectEmployee} />
        )}
        {activeTab === "supervisor" && selectedEmployee && selectedReportId && (
          <EmployeeDetailTab
            employee={selectedEmployee}
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
