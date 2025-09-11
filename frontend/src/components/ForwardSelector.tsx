// frontend/src/components/ForwardSelector.tsx

import React, { useState, useEffect } from "react";
import { ChevronDown, ChevronUp, Forward, Users } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import toast from "react-hot-toast";

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
  const [isLoading, setIsLoading] = useState(false);
  const { authFetch } = useAuth();

  useEffect(() => {
    loadForwardData();
  }, []);

  const loadForwardData = async () => {
    if (forwardData) return; // 已載入過就不重複載入
    
    setIsLoading(true);
    try {
      const response = await authFetch("/api/supervisor/forward/candidates");

      if (!response.ok) {
        throw new Error("無法載入轉寄名單");
      }

      const data = await response.json();
      setForwardData(data);
    } catch (error) {
      console.error("載入轉寄名單失敗:", error);
      toast.error("載入轉寄名單失敗");
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleUser = (empno: string) => {
    const newSelectedUsers = selectedForwardUsers.includes(empno)
      ? selectedForwardUsers.filter(id => id !== empno)
      : [...selectedForwardUsers, empno];
    
    onForwardUsersChange(newSelectedUsers);
  };

  const clearAllSelections = () => {
    onForwardUsersChange([]);
  };

  const selectedCount = selectedForwardUsers.length;
  const selectedNames = forwardData?.candidates
    .filter(c => selectedForwardUsers.includes(c.empno))
    .map(c => c.empname) || [];
  
  const titleCandidates = forwardData?.candidates.filter(c => c.type === "title") || [];
  const deptCandidates = forwardData?.candidates.filter(c => c.type === "department") || [];

  return (
    <div className={`border border-blue-300 rounded-lg bg-blue-25 ${className}`}>
      {/* 標題區塊 */}
      <div className="p-4 border-b border-blue-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Forward className="w-5 h-5 text-blue-600" />
            <span className="text-lg font-medium text-blue-800">
              轉寄給其他主管
            </span>
          </div>
          <div className="flex items-center space-x-2">
            {selectedCount > 0 && (
              <>
                <span className="text-sm text-blue-800">
                  已選擇: {selectedNames.join(', ')}
                </span>
                <button
                  onClick={clearAllSelections}
                  className="text-sm text-red-600 hover:text-red-800 underline"
                >
                  清除全選
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* 內容區塊 - 始終顯示 */}
      <div className="p-4">
        {isLoading ? (
          <div className="text-center text-blue-600 py-8">載入轉寄名單中...</div>
        ) : forwardData ? (
          <>
            {/* 職稱轉寄區塊 */}
            <div className="mb-6">
              <h4 className="text-md font-medium text-blue-800 mb-3 flex items-center">
                <Forward className="w-4 h-4 mr-2" />
                職稱轉寄
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2">
                {titleCandidates.map((candidate) => (
                  <label
                    key={candidate.empno}
                    className="flex items-center space-x-2 p-2 hover:bg-blue-100 rounded cursor-pointer text-sm border border-blue-200"
                  >
                    <input
                      type="checkbox"
                      checked={selectedForwardUsers.includes(candidate.empno)}
                      onChange={() => handleToggleUser(candidate.empno)}
                      className="text-blue-600 focus:ring-blue-500 h-4 w-4"
                    />
                    <span className="text-blue-800 truncate">
                      {candidate.empname}
                    </span>
                  </label>
                ))}
              </div>
              {titleCandidates.length === 0 && (
                <div className="text-sm text-gray-500 text-center py-4">
                  暫無職稱資料
                </div>
              )}
            </div>

            {/* 部門轉寄區塊 - 只有高管才顯示 */}
            {forwardData.user_adm_rank <= 5 && deptCandidates.length > 0 && (
              <div>
                <h4 className="text-md font-medium text-blue-800 mb-3 flex items-center">
                  <Users className="w-4 h-4 mr-2" />
                  部門轉寄 
                  <span className="text-sm text-blue-600 ml-2">(管理階層專用)</span>
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                  {deptCandidates.map((candidate) => (
                    <label
                      key={candidate.empno}
                      className="flex items-start space-x-2 p-3 hover:bg-blue-100 rounded cursor-pointer text-sm border border-blue-200"
                    >
                      <input
                        type="checkbox"
                        checked={selectedForwardUsers.includes(candidate.empno)}
                        onChange={() => handleToggleUser(candidate.empno)}
                        className="text-blue-600 focus:ring-blue-500 h-4 w-4 mt-0.5"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-blue-800 truncate">
                          {candidate.empname}
                        </div>
                        <div className="text-blue-600 truncate text-xs">
                          {candidate.deptabbv} - {candidate.dutyscript}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
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