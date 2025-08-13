// frontend/src/App.tsx

import { useState } from "react";
import { Edit3, FileText, LogOut } from "lucide-react";
import DataInputTab from "./components/DataInputTab";
import DailyReportTab from "./components/DailyReportTab";
// import AIDailyReportTab from './components/AIDailyReportTab';
// import ComprehensiveEditTab from './components/ComprehensiveEditTab';
import EmployeeListTab from "./components/EmployeeListTab";
import EmployeeDetailTab from "./components/EmployeeDetailTab";
import { useAuth } from "./contexts/AuthContext";
import { Toaster } from "react-hot-toast";
// --- Interface Definitions ---
export interface Project {
  id: number;
  name: string;
  is_active: boolean;
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
}
export interface FileForUpload extends Omit<FileAttachment, "id"> {
  is_selected_for_ai: boolean;
}
export interface WorkRecordCreate {
  content: string;
  project_id?: number;
  files: FileForUpload[];
}
export interface ConsolidatedReport {
  project: Project;
  content: string;
  files: FileAttachment[];
  record_count: number;
  ai_content: string | null;
}
export interface EmployeeInList {
  id: number;
  name: string;
  department: string;
  pending_reports_count: number;
}
export interface EmployeeSummary {
  id: number;
  name: string;
  department: string;
}
export interface DailyReport {
  id: number;
  date: string;
  status: string;
  rating: number | null;
  feedback: string | null;
  consolidated_content: ConsolidatedReport[];
  employee: EmployeeSummary;
}
export interface Employee {
  id: number;
  name: string;
  department: string;
  reports: DailyReport[];
}
export interface User {
  id: number;
  email: string;
  name: string;
  is_active: boolean;
  is_supervisor: boolean;
}
function App() {
  const { user, logout } = useAuth();
  const [mainTab, setMainTab] = useState<"employee" | "supervisor">("employee");
  const [activeTab, setActiveTab] = useState<
    "input" | "daily" | "ai" | "comprehensive"
  >("input");

  const [selectedEmployee, setSelectedEmployee] =
    useState<EmployeeInList | null>(null);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);

  const handleSelectEmployee = (employee: EmployeeInList, reportId: number) => {
    setSelectedEmployee(employee);
    setSelectedReportId(reportId);
  };

  const handleBackFromDetail = () => {
    setSelectedEmployee(null);
    setSelectedReportId(null);
  };

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
                <button
                  onClick={() => {
                    setMainTab("employee");
                    setSelectedEmployee(null);
                  }}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                    mainTab === "employee"
                      ? "bg-green-100 text-green-700"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  日報填寫
                </button>
                {user?.is_supervisor && (
                  <button
                    onClick={() => setMainTab("supervisor")}
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                      mainTab === "supervisor"
                        ? "bg-green-100 text-green-700"
                        : "text-gray-600 hover:bg-gray-100"
                    }`}
                  >
                    日報審核
                  </button>
                )}
              </div>
              <div className="flex items-center space-x-3">
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900">
                    {user?.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {user?.is_supervisor ? "主管" : "員工"}
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

      {mainTab === "employee" && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="border-b border-gray-200 bg-white">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab("input")}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === "input"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                <div className="flex items-center space-x-2">
                  <Edit3 className="w-4 h-4" />
                  <span>資料輸入</span>
                </div>
              </button>
              <button
                onClick={() => setActiveTab("daily")}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === "daily"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                <div className="flex items-center space-x-2">
                  <FileText className="w-4 h-4" />
                  <span>日報編輯</span>
                </div>
              </button>
              {/* <button onClick={() => setActiveTab('ai')} className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'ai' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}>
                <div className="flex items-center space-x-2"><Wand2 className="w-4 h-4" /><span>AI日報編輯</span></div>
              </button>
              <button onClick={() => setActiveTab('comprehensive')} className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'comprehensive' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}>
                <div className="flex items-center space-x-2"><Columns className="w-4 h-4" /><span>綜合編輯</span></div>
              </button> */}
            </nav>
          </div>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 bg-gray-50 min-h-screen">
        {mainTab === "employee" && (
          <>
            {activeTab === "input" && <DataInputTab />}
            {activeTab === "daily" && <DailyReportTab />}
            {/* {activeTab === 'ai' && <AIDailyReportTab />}
                {activeTab === 'comprehensive' && <ComprehensiveEditTab />} */}
          </>
        )}

        {mainTab === "supervisor" && !selectedEmployee && (
          <EmployeeListTab onSelectEmployee={handleSelectEmployee} />
        )}
        {mainTab === "supervisor" && selectedEmployee && selectedReportId && (
          <EmployeeDetailTab
            employee={selectedEmployee}
            reportId={selectedReportId}
            onBack={handleBackFromDetail}
          />
        )}
      </main>
    </div>
  );
}
export default App;
