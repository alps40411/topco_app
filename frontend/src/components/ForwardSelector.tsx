// frontend/src/components/ForwardSelector.tsx

import React, { useState, useEffect } from "react";
import { Forward } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import toast from "react-hot-toast";

// 原有的職稱轉寄資料結構
interface ForwardCandidate {
  empno: string;
  empname: string;
  type: "title" | "department";
  cocode?: string;
  deptabbv?: string;
  dutyscript?: string;
}

interface ForwardData {
  user_adm_rank: number;
  candidates: ForwardCandidate[];
}

// 新的部門轉寄資料結構
interface Employee {
  empno: string;
  empname: string;
  duty: string;
  cocode: string;
  deptno: string;
  dclass: number;
  adm_rank: number;
}

interface ForwardEmployeeData {
  success: boolean;
  data: { [categoryName: string]: { [deptName: string]: Employee[] } };
}

interface ForwardSelectorProps {
  selectedForwardUsers: string[];
  onForwardUsersChange: (users: string[]) => void;
  className?: string;
}

// ✅ 全局快取 (模組層級)
let globalForwardDataCache: {
  forwardData: ForwardData | null;
  departmentData: ForwardEmployeeData | null;
  timestamp: number;
} | null = null;

const CACHE_DURATION = 10 * 60 * 1000; // 10 分鐘

const ForwardSelector: React.FC<ForwardSelectorProps> = ({
  selectedForwardUsers,
  onForwardUsersChange,
  className = "",
}) => {
  const [forwardData, setForwardData] = useState<ForwardData | null>(null);
  const [departmentData, setDepartmentData] =
    useState<ForwardEmployeeData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDeptLoading, setIsDeptLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<string>("all");
  const { authFetch } = useAuth();

  useEffect(() => {
    loadForwardData();
  }, []);

  const loadForwardData = async () => {
    // ✅ 檢查全局快取
    const now = Date.now();
    if (
      globalForwardDataCache &&
      now - globalForwardDataCache.timestamp < CACHE_DURATION
    ) {
      console.log("[ForwardSelector] 使用快取資料");
      setForwardData(globalForwardDataCache.forwardData);
      setDepartmentData(globalForwardDataCache.departmentData);
      return;
    }

    console.log("[ForwardSelector] 載入新資料");
    setIsLoading(true);
    try {
      const response = await authFetch("/api/supervisor/forward/candidates");

      if (!response.ok) {
        throw new Error("無法載入轉寄名單");
      }

      const data = await response.json();
      setForwardData(data);

      let deptData = null;
      // 如果是高管，同時載入部門轉寄資料
      if (data.user_adm_rank <= 5) {
        deptData = await loadDepartmentData();
      }

      // ✅ 更新全局快取
      globalForwardDataCache = {
        forwardData: data,
        departmentData: deptData,
        timestamp: now,
      };
    } catch (error) {
      console.error("載入轉寄名單失敗:", error);
      toast.error("載入轉寄名單失敗");
    } finally {
      setIsLoading(false);
    }
  };

  const loadDepartmentData = async (): Promise<ForwardEmployeeData | null> => {
    setIsDeptLoading(true);
    try {
      const response = await authFetch("/api/forward/employees");

      if (!response.ok) {
        throw new Error("無法載入部門轉寄名單");
      }

      const data = await response.json();
      setDepartmentData(data);
      return data;
    } catch (error) {
      console.error("載入部門轉寄名單失敗:", error);
      toast.error("載入部門轉寄名單失敗");
      return null;
    } finally {
      setIsDeptLoading(false);
    }
  };

  const handleToggleUser = (empno: string) => {
    const newSelectedUsers = selectedForwardUsers.includes(empno)
      ? selectedForwardUsers.filter((id) => id !== empno)
      : [...selectedForwardUsers, empno];

    onForwardUsersChange(newSelectedUsers);
  };

  // 為部門員工創建唯一標識符的處理函數
  const handleToggleDepartmentUser = (uniqueId: string, empno: string) => {
    const newSelectedUsers = selectedForwardUsers.includes(uniqueId)
      ? selectedForwardUsers.filter((id) => id !== uniqueId)
      : [...selectedForwardUsers, uniqueId];

    onForwardUsersChange(newSelectedUsers);
  };

  const clearAllSelections = () => {
    onForwardUsersChange([]);
  };

  // 個別取消選取的函數
  const handleRemoveSelection = (idToRemove: string) => {
    const newSelectedUsers = selectedForwardUsers.filter(
      (id) => id !== idToRemove
    );
    onForwardUsersChange(newSelectedUsers);
  };

  // 獲取已選取項目的詳細資訊
  const getSelectedItems = () => {
    const items: Array<{
      id: string;
      name: string;
      type: "title" | "department";
    }> = [];

    // 處理職稱轉寄
    titleCandidates.forEach((candidate, index) => {
      const uniqueTitleId = `title_${candidate.empno}_${candidate.type}_${index}`;
      if (selectedForwardUsers.includes(uniqueTitleId)) {
        items.push({
          id: uniqueTitleId,
          name: candidate.empname,
          type: "title",
        });
      }
    });

    // 處理部門轉寄
    if (departmentData?.data) {
      Object.entries(departmentData.data).forEach(
        ([categoryName, departments]) => {
          Object.entries(departments).forEach(([deptName, employees]) => {
            const employeeGroups = groupEmployeesByDuty(employees);
            Object.entries(employeeGroups).forEach(([duty, dutyEmployees]) => {
              dutyEmployees.forEach((employee, empIndex) => {
                const uniqueId = `dept_${categoryName}_${deptName}_${duty}_${employee.empno}_${empIndex}`;
                if (selectedForwardUsers.includes(uniqueId)) {
                  items.push({
                    id: uniqueId,
                    name: employee.empname,
                    type: "department",
                  });
                }
              });
            });
          });
        }
      );
    }

    return items;
  };

  const selectedCount = selectedForwardUsers.length;

  const titleCandidates =
    forwardData?.candidates.filter((c) => c.type === "title") || [];
  const deptCandidates =
    forwardData?.candidates.filter((c) => c.type === "department") || [];

  const selectedNames =
    titleCandidates
      .map((candidate, index) => {
        const uniqueTitleId = `title_${candidate.empno}_${candidate.type}_${index}`;
        return selectedForwardUsers.includes(uniqueTitleId)
          ? candidate.empname
          : null;
      })
      .filter(Boolean) || [];

  // 根據職級分組員工
  const groupEmployeesByDuty = (employees: Employee[]) => {
    const groups: { [duty: string]: Employee[] } = {};
    employees.forEach((emp) => {
      if (!groups[emp.duty]) {
        groups[emp.duty] = [];
      }
      groups[emp.duty].push(emp);
    });
    return groups;
  };

  // 獲取部門員工名稱
  const getDepartmentEmployeeNames = () => {
    if (!departmentData?.data) return [];
    const selectedDeptNames: string[] = [];

    Object.entries(departmentData.data).forEach(
      ([categoryName, departments]) => {
        Object.entries(departments).forEach(([deptName, employees]) => {
          const employeeGroups = groupEmployeesByDuty(employees);
          Object.entries(employeeGroups).forEach(([duty, dutyEmployees]) => {
            dutyEmployees.forEach((employee, empIndex) => {
              const uniqueId = `dept_${categoryName}_${deptName}_${duty}_${employee.empno}_${empIndex}`;
              if (selectedForwardUsers.includes(uniqueId)) {
                selectedDeptNames.push(employee.empname);
              }
            });
          });
        });
      }
    );

    return selectedDeptNames;
  };

  const allSelectedNames = [...selectedNames, ...getDepartmentEmployeeNames()];

  // 獲取分類列表
  const categories = departmentData?.data
    ? Object.keys(departmentData.data)
    : [];

  // 職級到 CSS 類別的映射
  const getDutyClass = (duty: string) => {
    if (duty.includes("總經理")) return "un2";
    if (duty.includes("協理") || duty.includes("副總")) return "un4";
    if (duty.includes("經理")) return "un6";
    if (duty.includes("副理")) return "un8";
    return "un10";
  };

  return (
    <div
      className={`border border-blue-300 rounded-lg bg-blue-25 ${className}`}
    >
      {/* 標題區塊 */}
      <div className="p-4 border-b border-blue-200">
        <div className="flex items-center space-x-2 mb-3">
          <Forward className="w-5 h-5 text-blue-600" />
          <span className="text-lg font-medium text-blue-800">
            跨群轉寄 (請勾選轉寄對象)
          </span>
        </div>
        {selectedCount > 0 && (
          <div className="flex flex-wrap gap-2">
            {getSelectedItems().map((item) => (
              <div
                key={item.id}
                className="inline-flex items-center px-3 py-1 rounded-full font-medium bg-blue-100 text-blue-800 border border-blue-200"
                style={{ fontSize: "16px" }}
              >
                <span className="mr-2">{item.name}</span>
                <button
                  onClick={() => handleRemoveSelection(item.id)}
                  className="ml-1 inline-flex items-center justify-center w-4 h-4 rounded-full bg-blue-200 hover:bg-blue-300 text-blue-600 hover:text-blue-800 focus:outline-none"
                  title={`移除 ${item.name}`}
                >
                  <svg
                    className="w-3 h-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 內容區塊 - 始終顯示 */}
      <div className="p-4">
        {isLoading ? (
          <div className="text-center text-blue-600 py-8">
            載入轉寄名單中...
          </div>
        ) : forwardData ? (
          <>
            {/* 職稱轉寄區塊 */}
            <div
              className="mb-6"
              style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}
            >
              {titleCandidates.map((candidate, index) => {
                const uniqueTitleId = `title_${candidate.empno}_${candidate.type}_${index}`;
                return (
                  <b
                    key={uniqueTitleId}
                    style={{
                      display: "inline-block",
                      flex: "0 0 calc(20% - 8px)",
                      minWidth: "0",
                      boxSizing: "border-box",
                    }}
                  >
                    <input
                      type="checkbox"
                      id={uniqueTitleId}
                      checked={selectedForwardUsers.includes(uniqueTitleId)}
                      onChange={() => handleToggleUser(uniqueTitleId)}
                      style={{ marginRight: "4px" }}
                    />
                    <label
                      htmlFor={uniqueTitleId}
                      className="text-sm cursor-pointer hover:text-blue-600"
                      style={{ color: "#374151" }}
                    >
                      {candidate.empname}
                    </label>
                  </b>
                );
              })}
              {titleCandidates.length === 0 && (
                <span className="text-sm text-gray-500">暫無職稱資料</span>
              )}
            </div>

            {/* 部門轉寄區塊 - 只有高管才顯示 */}
            {forwardData.user_adm_rank <= 5 && (
              <div>
                {isDeptLoading ? (
                  <div className="text-center text-blue-600 py-4">
                    載入部門轉寄名單中...
                  </div>
                ) : departmentData?.data ? (
                  <>
                    {/* 標籤導覽列 - 每行6-7個固定寬度 */}
                    <div
                      className="unitsmenu mb-0"
                      style={{
                        display: "flex",
                        flexWrap: "wrap",
                        borderTop: "1px solid rgb(204, 204, 204)",
                        borderRight: "1px solid rgb(204, 204, 204)",
                        borderBottom: "none",
                        borderLeft: "1px solid rgb(204, 204, 204)",
                        borderImage: "initial",
                        width: "100%",
                      }}
                    >
                      <a
                        className="t0 text-sm cursor-pointer no-underline"
                        style={{
                          padding: "8px 12px",
                          backgroundColor:
                            activeTab === "all" ? "#333" : "#666",
                          color: "#fff",
                          border: "none",
                          borderRight: "1px solid rgb(204, 204, 204)",
                          borderBottom: "1px solid rgb(204, 204, 204)",
                          textAlign: "center",
                          width: "calc(100% / 7)",
                          boxSizing: "border-box",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                        onClick={() => setActiveTab("all")}
                      >
                        顯示全部
                      </a>
                      {categories.map((category, index) => (
                        <a
                          key={category}
                          className={`t${
                            index + 1
                          } text-sm cursor-pointer no-underline`}
                          style={{
                            padding: "8px 12px",
                            backgroundColor:
                              activeTab === category ? "#333" : "#666",
                            color: "#fff",
                            border: "none",
                            borderRight: "1px solid rgb(204, 204, 204)",
                            borderBottom: "1px solid rgb(204, 204, 204)",
                            textAlign: "center",
                            width: "calc(100% / 7)",
                            boxSizing: "border-box",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                          onClick={() => setActiveTab(category)}
                        >
                          {category}
                        </a>
                      ))}
                    </div>

                    {/* 內容顯示區 - 保持原本結構只改配色 */}
                    <div className="fwtbl">
                      {categories.map((category, categoryIndex) => {
                        const isVisible =
                          activeTab === "all" || activeTab === category;
                        const departments = departmentData.data[category];

                        return (
                          <table
                            key={category}
                            id={`t${categoryIndex + 1}`}
                            width="100%"
                            border={0}
                            cellSpacing={0}
                            cellPadding={0}
                            style={{
                              display: isVisible ? "table" : "none",
                              marginBottom: "16px",
                              border: "1px solid #ccc",
                            }}
                          >
                            <tbody>
                              <tr>
                                <th
                                  colSpan={2}
                                  scope="col"
                                  style={{
                                    backgroundColor: "#fFF0B4",
                                    padding: "8px",
                                    textAlign: "center",
                                    fontWeight: "bold",
                                    color: "#000",
                                    border: "1px solid #ccc",
                                  }}
                                >
                                  {category}
                                </th>
                              </tr>
                              {Object.entries(departments).map(
                                ([deptName, employees], deptIndex) => {
                                  const employeeGroups =
                                    groupEmployeesByDuty(employees);

                                  return (
                                    <tr
                                      key={`${category}-${deptName}`}
                                      style={{ borderTop: "1px solid #ccc" }}
                                    >
                                      <td
                                        style={{
                                          padding: "8px",
                                          borderRight: "1px solid #ccc",
                                          backgroundColor: "#1F8EB8",
                                          color: "#fff",
                                          fontWeight: "bold",
                                          verticalAlign: "middle",
                                          width: "200px",
                                          textAlign: "center",
                                        }}
                                      >
                                        {deptName}
                                      </td>
                                      <td
                                        style={{
                                          padding: "8px",
                                          backgroundColor: "#f8fafc",
                                        }}
                                      >
                                        {Object.entries(employeeGroups).map(
                                          ([duty, dutyEmployees]) => (
                                            <span
                                              key={duty}
                                              className={getDutyClass(duty)}
                                              style={{
                                                display: "inline-block",
                                                marginRight: "16px",
                                                marginBottom: "8px",
                                                verticalAlign: "top",
                                              }}
                                            >
                                              <h5
                                                className="text-sm font-bold mb-1"
                                                style={{ color: "#0ea5e9" }}
                                              >
                                                {duty}
                                              </h5>
                                              <i
                                                style={{ display: "block" }}
                                              ></i>
                                              {dutyEmployees.map(
                                                (employee, empIndex) => {
                                                  const uniqueId = `dept_${category}_${deptName}_${duty}_${employee.empno}_${empIndex}`;
                                                  const checkboxId = `emp_${employee.empno}_${categoryIndex}_${deptIndex}_${empIndex}`;
                                                  return (
                                                    <b
                                                      key={uniqueId}
                                                      style={{
                                                        display: "inline-block",
                                                        width: "auto",
                                                        marginRight: "8px",
                                                        marginBottom: "4px",
                                                        boxSizing: "border-box",
                                                      }}
                                                    >
                                                      <input
                                                        type="checkbox"
                                                        id={checkboxId}
                                                        value={uniqueId}
                                                        checked={selectedForwardUsers.includes(
                                                          uniqueId
                                                        )}
                                                        onChange={() =>
                                                          handleToggleDepartmentUser(
                                                            uniqueId,
                                                            employee.empno
                                                          )
                                                        }
                                                        style={{
                                                          marginRight: "4px",
                                                        }}
                                                      />
                                                      <label
                                                        htmlFor={checkboxId}
                                                        className="text-sm cursor-pointer hover:text-blue-600"
                                                        style={{
                                                          color: "#374151",
                                                        }}
                                                      >
                                                        {employee.empname}
                                                      </label>
                                                    </b>
                                                  );
                                                }
                                              )}
                                            </span>
                                          )
                                        )}
                                      </td>
                                    </tr>
                                  );
                                }
                              )}
                            </tbody>
                          </table>
                        );
                      })}
                    </div>
                  </>
                ) : (
                  <div className="text-center text-red-600 py-4">
                    載入部門轉寄名單失敗
                  </div>
                )}
              </div>
            )}
          </>
        ) : (
          <div className="text-center text-red-600 py-8">載入轉寄名單失敗</div>
        )}
      </div>
    </div>
  );
};

export default ForwardSelector;
