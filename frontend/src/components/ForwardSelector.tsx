// frontend/src/components/ForwardSelector.tsx

import React, { useState, useEffect } from "react";
import { ChevronDown, ChevronUp, Forward, Users } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import toast from "react-hot-toast";

interface Visor {
  empno: string;
  empname: string;
}

interface Employee {
  empno: string;
  empname: string;
  cocode: string;
  deptno: string;
  duty: string;
  dclass: string;
  adm_rank: string;
}

interface ForwardData {
  visors: Visor[];
  employees: Record<string, Record<string, Employee[]>>;
}

interface ForwardSelectorProps {
  selectedForwardUsers: string[];
  onForwardUsersChange: (users: string[]) => void;
  className?: string;
}

const ForwardSelector: React.FC<ForwardSelectorProps> = ({
  selectedForwardUsers,
  onForwardUsersChange,
  className = "",
}) => {
  const [forwardData, setForwardData] = useState<ForwardData | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"visors" | "employees">("visors");
  const [expandedCompanies, setExpandedCompanies] = useState<Set<string>>(new Set());
  const { authFetch } = useAuth();

  const loadForwardData = async () => {
    if (forwardData) return; // 已載入過就不重複載入
    
    setIsLoading(true);
    try {
      const [visorsResponse, employeesResponse] = await Promise.all([
        authFetch("/api/forward/visors"),
        authFetch("/api/forward/employees")
      ]);

      if (!visorsResponse.ok || !employeesResponse.ok) {
        throw new Error("無法載入轉寄名單");
      }

      const visorsData = await visorsResponse.json();
      const employeesData = await employeesResponse.json();

      setForwardData({
        visors: visorsData.data || [],
        employees: employeesData.data || {}
      });
    } catch (error) {
      console.error("載入轉寄名單失敗:", error);
      toast.error("載入轉寄名單失敗");
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleExpanded = () => {
    setIsExpanded(!isExpanded);
    if (!isExpanded && !forwardData) {
      loadForwardData();
    }
  };

  const handleToggleUser = (empno: string) => {
    const newSelectedUsers = selectedForwardUsers.includes(empno)
      ? selectedForwardUsers.filter(id => id !== empno)
      : [...selectedForwardUsers, empno];
    
    onForwardUsersChange(newSelectedUsers);
  };

  const handleToggleCompany = (coabbv: string) => {
    const newExpanded = new Set(expandedCompanies);
    if (newExpanded.has(coabbv)) {
      newExpanded.delete(coabbv);
    } else {
      newExpanded.add(coabbv);
    }
    setExpandedCompanies(newExpanded);
  };

  const clearAllSelections = () => {
    onForwardUsersChange([]);
  };

  const selectedCount = selectedForwardUsers.length;

  return (
    <div className={`border border-blue-300 rounded-lg bg-blue-25 ${className}`}>
      <div 
        className="flex items-center justify-between p-3 cursor-pointer hover:bg-blue-100 transition-colors"
        onClick={handleToggleExpanded}
      >
        <div className="flex items-center space-x-2">
          <Forward className="w-4 h-4 text-blue-600" />
          <span className="text-sm font-medium text-blue-800">
            轉寄給其他主管
          </span>
          {selectedCount > 0 && (
            <span className="bg-blue-500 text-white text-xs px-2 py-0.5 rounded-full">
              已選 {selectedCount} 人
            </span>
          )}
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-blue-600" />
        ) : (
          <ChevronDown className="w-4 h-4 text-blue-600" />
        )}
      </div>

      {isExpanded && (
        <div className="border-t border-blue-200 bg-blue-50">
          {isLoading ? (
            <div className="p-4 text-center text-blue-600">載入轉寄名單中...</div>
          ) : forwardData ? (
            <>
              {/* 標籤切換 */}
              <div className="flex border-b border-blue-200">
                <button
                  onClick={() => setActiveTab("visors")}
                  className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                    activeTab === "visors"
                      ? "bg-blue-500 text-white"
                      : "text-blue-700 hover:bg-blue-100"
                  }`}
                >
                  職稱列表
                </button>
                <button
                  onClick={() => setActiveTab("employees")}
                  className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                    activeTab === "employees"
                      ? "bg-blue-500 text-white"
                      : "text-blue-700 hover:bg-blue-100"
                  }`}
                >
                  部門員工
                </button>
              </div>

              <div className="p-3">
                {selectedCount > 0 && (
                  <div className="mb-3 flex justify-between items-center">
                    <span className="text-xs text-blue-700">已選擇 {selectedCount} 人</span>
                    <button
                      onClick={clearAllSelections}
                      className="text-xs text-red-600 hover:text-red-800 underline"
                    >
                      清除全選
                    </button>
                  </div>
                )}

                <div className="max-h-64 overflow-y-auto">
                  {activeTab === "visors" ? (
                    <div className="space-y-1">
                      {forwardData.visors.map((visor) => (
                        <label
                          key={visor.empno}
                          className="flex items-center space-x-2 p-2 hover:bg-blue-100 rounded cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={selectedForwardUsers.includes(visor.empno)}
                            onChange={() => handleToggleUser(visor.empno)}
                            className="text-blue-600 focus:ring-blue-500"
                          />
                          <span className="text-sm text-blue-800">
                            {visor.empname} ({visor.empno})
                          </span>
                        </label>
                      ))}
                      {forwardData.visors.length === 0 && (
                        <div className="text-sm text-gray-500 text-center py-4">
                          暫無職稱資料
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {Object.entries(forwardData.employees).map(([coabbv, departments]) => (
                        <div key={coabbv} className="border border-blue-200 rounded">
                          <div
                            className="flex items-center justify-between p-2 bg-blue-100 cursor-pointer"
                            onClick={() => handleToggleCompany(coabbv)}
                          >
                            <div className="flex items-center space-x-2">
                              <Users className="w-4 h-4 text-blue-600" />
                              <span className="text-sm font-medium text-blue-800">
                                {coabbv}
                              </span>
                            </div>
                            {expandedCompanies.has(coabbv) ? (
                              <ChevronUp className="w-4 h-4 text-blue-600" />
                            ) : (
                              <ChevronDown className="w-4 h-4 text-blue-600" />
                            )}
                          </div>

                          {expandedCompanies.has(coabbv) && (
                            <div className="p-2 space-y-2">
                              {Object.entries(departments).map(([deptabbv, employees]) => (
                                <div key={deptabbv} className="border-l-2 border-blue-300 pl-2">
                                  <div className="text-xs font-medium text-blue-700 mb-1">
                                    {deptabbv}
                                  </div>
                                  <div className="space-y-1">
                                    {employees.map((employee) => (
                                      <label
                                        key={employee.empno}
                                        className="flex items-center space-x-2 p-1 hover:bg-blue-50 rounded cursor-pointer"
                                      >
                                        <input
                                          type="checkbox"
                                          checked={selectedForwardUsers.includes(employee.empno)}
                                          onChange={() => handleToggleUser(employee.empno)}
                                          className="text-blue-600 focus:ring-blue-500"
                                        />
                                        <span className="text-xs text-blue-800">
                                          {employee.empname} ({employee.empno})
                                          {employee.duty && (
                                            <span className="text-gray-500 ml-1">
                                              - {employee.duty}
                                            </span>
                                          )}
                                        </span>
                                      </label>
                                    ))}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                      {Object.keys(forwardData.employees).length === 0 && (
                        <div className="text-sm text-gray-500 text-center py-4">
                          暫無員工資料
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="p-4 text-center text-red-600">載入轉寄名單失敗</div>
          )}
        </div>
      )}
    </div>
  );
};

export default ForwardSelector;