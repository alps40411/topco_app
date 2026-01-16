// frontend/src/components/RevenueTable.tsx

import React, { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { RevenueData } from "../services/types";

interface RevenueTableProps {
  data: RevenueData[];
  isLoading?: boolean;
}

// 格式化金額（加千分位）
const formatAmount = (amount?: number): string => {
  if (amount === 0.0 || amount === undefined || amount === null) return "0";
  return amount.toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
};

// 計算達成率
const formatRate = (target?: number): string => {
  if (target === 0.0 || target === undefined || target === null) return "0%";
  return `${target.toFixed(2)}%`;
};

const RevenueTable: React.FC<RevenueTableProps> = ({
  data,
  isLoading = false,
}) => {
  // 從 localStorage 讀取摺疊狀態，預設為 false（展開）
  const [isCollapsed, setIsCollapsed] = useState(() => {
    const saved = localStorage.getItem("revenueTableCollapsed");
    return saved === "true";
  });

  // 當摺疊狀態改變時，保存到 localStorage
  const handleToggleCollapse = () => {
    const newState = !isCollapsed;
    setIsCollapsed(newState);
    localStorage.setItem("revenueTableCollapsed", String(newState));
  };

  // ✅ 載入中或沒有資料時都不顯示，避免畫面閃爍
  if (isLoading || !data || data.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6">
      <div
        className="flex items-center justify-between px-6 py-2 border-b border-gray-200"
        style={{ backgroundColor: "#d8d8c3" }}
      >
        <h3 className="text-gray-900" style={{ fontSize: "16px" }}>
          營收達成率
        </h3>
        <button
          onClick={handleToggleCollapse}
          className="p-1 hover:bg-gray-100 rounded transition-colors"
          aria-label={isCollapsed ? "展開" : "收合"}
        >
          {isCollapsed ? (
            <ChevronDown className="w-5 h-5 text-gray-600" />
          ) : (
            <ChevronUp className="w-5 h-5 text-gray-600" />
          )}
        </button>
      </div>

      {!isCollapsed && (
        <div className="overflow-x-auto">
          <table className="min-w-full border-collapse">
            <thead className="bg-gray-50">
              <tr>
                <th
                  className="text-center font-medium text-gray-700 uppercase tracking-wider border border-gray-300"
                  style={{ padding: "5px 3px", fontSize: "15px" }}
                >
                  產品
                </th>
                <th
                  className="text-center font-medium text-gray-700 uppercase tracking-wider border border-gray-300"
                  style={{ padding: "5px 3px", fontSize: "15px" }}
                >
                  年度目標
                </th>
                <th
                  className="text-center font-medium text-gray-700 uppercase tracking-wider border border-gray-300"
                  style={{ padding: "5px 3px", fontSize: "15px" }}
                >
                  年度出貨
                </th>
                <th
                  className="text-center font-medium text-gray-700 uppercase tracking-wider border border-gray-300"
                  style={{ padding: "5px 3px", fontSize: "15px" }}
                >
                  累計達成
                </th>
                <th
                  className="text-center font-medium text-gray-700 uppercase tracking-wider border border-gray-300"
                  style={{ padding: "5px 3px", fontSize: "15px" }}
                >
                  月目標
                </th>
                <th
                  className="text-center font-medium text-gray-700 uppercase tracking-wider border border-gray-300"
                  style={{ padding: "5px 3px", fontSize: "15px" }}
                >
                  月累計營收
                </th>
                <th
                  className="text-center font-medium text-gray-700 uppercase tracking-wider border border-gray-300"
                  style={{ padding: "5px 3px", fontSize: "15px" }}
                >
                  月達成率
                </th>
              </tr>
            </thead>
            <tbody className="bg-white">
              {data.map((row, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td
                    className="whitespace-nowrap text-sm text-gray-900 border border-gray-300"
                    style={{ padding: "5px 3px" }}
                  >
                    {row.catedesc1 || "-"}
                  </td>
                  <td
                    className="whitespace-nowrap text-sm text-gray-900 text-right border border-gray-300"
                    style={{ padding: "5px 3px" }}
                  >
                    {formatAmount(row.ym_bg_rev_amt)}
                  </td>
                  <td
                    className="whitespace-nowrap text-sm text-gray-900 text-right border border-gray-300"
                    style={{ padding: "5px 3px" }}
                  >
                    {formatAmount(row.ym_rev_amt)}
                  </td>
                  <td
                    className="whitespace-nowrap text-sm text-gray-900 text-right font-medium border border-gray-300"
                    style={{ padding: "5px 3px" }}
                  >
                    {formatRate(row.y_rev_amt)}
                  </td>
                  <td
                    className="whitespace-nowrap text-sm text-gray-900 text-right border border-gray-300"
                    style={{ padding: "5px 3px" }}
                  >
                    {formatAmount(row.ym_bg_rev_amt)}
                  </td>
                  <td
                    className="whitespace-nowrap text-sm text-gray-900 text-right border border-gray-300"
                    style={{ padding: "5px 3px" }}
                  >
                    {formatAmount(row.rev_amt)}
                  </td>
                  <td
                    className="whitespace-nowrap text-sm text-gray-900 text-right font-medium border border-gray-300"
                    style={{ padding: "5px 3px" }}
                  >
                    {formatRate(row.m_rev_amt)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default RevenueTable;
