// frontend/src/components/OverdueARTable.tsx

import React, { useState, useMemo } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { OverdueARData } from "../services/types";

interface OverdueARTableProps {
  data: OverdueARData[];
  isLoading?: boolean;
}

// 格式化日期 YYYYMMDD -> YYYY/MM/DD
const formatDate = (dateStr?: string): string => {
  if (!dateStr || dateStr.length !== 8) return "-";
  const year = dateStr.substring(0, 4);
  const month = dateStr.substring(4, 6);
  const day = dateStr.substring(6, 8);
  return `${year}/${month}/${day}`;
};

// 格式化金額（加千分位）
const formatAmount = (amount?: number): string => {
  if (amount === undefined || amount === null) return "-";
  return amount.toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
};

const OverdueARTable: React.FC<OverdueARTableProps> = ({
  data,
  isLoading = false,
}) => {
  // 從 localStorage 讀取摺疊狀態，預設為 false（展開）
  const [isCollapsed, setIsCollapsed] = useState(() => {
    const saved = localStorage.getItem("overdueARTableCollapsed");
    return saved === "true";
  });

  // 當摺疊狀態改變時，保存到 localStorage
  const handleToggleCollapse = () => {
    const newState = !isCollapsed;
    setIsCollapsed(newState);
    localStorage.setItem("overdueARTableCollapsed", String(newState));
  };

  // 依照銷貨日 (doc_date) 從小到大排序
  const sortedData = useMemo(() => {
    return [...data].sort((a, b) => {
      const dateA = a.doc_date || "";
      const dateB = b.doc_date || "";
      return dateA.localeCompare(dateB);
    });
  }, [data]);

  // ✅ 載入中或沒有資料時都不顯示，避免畫面閃爍
  if (isLoading || !data || data.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6">
      <div
        className="flex items-center justify-between px-6 py-2 border-b border-gray-200"
        style={{ backgroundColor: "#cad6c4" }}
      >
        <h3 className=" text-gray-900" style={{ fontSize: "16px" }}>
          逾期應收帳款
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
                  客戶簡稱
                </th>
                <th
                  className="text-center font-medium text-gray-700 uppercase tracking-wider border border-gray-300"
                  style={{ padding: "5px 3px", fontSize: "15px" }}
                >
                  發票號碼
                </th>
                <th
                  className="text-center font-medium text-gray-700 uppercase tracking-wider border border-gray-300"
                  style={{ padding: "5px 3px", fontSize: "15px" }}
                >
                  銷貨日
                </th>
                <th
                  className="text-center font-medium text-gray-700 uppercase tracking-wider border border-gray-300"
                  style={{ padding: "5px 3px", fontSize: "15px" }}
                >
                  銷貨單號
                </th>
                <th
                  className="text-center font-medium text-gray-700 uppercase tracking-wider border border-gray-300"
                  style={{ padding: "5px 3px", fontSize: "15px" }}
                >
                  預計付款日
                </th>
                <th
                  className="text-center font-medium text-gray-700 uppercase tracking-wider border border-gray-300"
                  style={{ padding: "5px 3px", fontSize: "15px" }}
                >
                  幣別
                </th>
                <th
                  className="text-center font-medium text-gray-700 uppercase tracking-wider border border-gray-300"
                  style={{ padding: "5px 3px", fontSize: "15px" }}
                >
                  原幣餘額
                </th>
              </tr>
            </thead>
            <tbody className="bg-white">
              {sortedData.map((row, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td
                    className="whitespace-nowrap text-sm text-gray-900 border border-gray-300"
                    style={{ padding: "5px 3px" }}
                  >
                    {row.abbv_c || "-"}
                  </td>
                  <td
                    className="whitespace-nowrap text-sm text-gray-900 border border-gray-300"
                    style={{ padding: "5px 3px" }}
                  >
                    {row.invoice || "-"}
                  </td>
                  <td
                    className="whitespace-nowrap text-sm text-gray-900 border border-gray-300"
                    style={{ padding: "5px 3px" }}
                  >
                    {formatDate(row.doc_date)}
                  </td>
                  <td
                    className="whitespace-nowrap text-sm text-gray-900 border border-gray-300"
                    style={{ padding: "5px 3px" }}
                  >
                    {row.doc_no || "-"}
                  </td>
                  <td
                    className="whitespace-nowrap text-sm text-gray-900 border border-gray-300"
                    style={{ padding: "5px 3px" }}
                  >
                    {formatDate(row.ppay_date)}
                  </td>
                  <td
                    className="whitespace-nowrap text-sm text-gray-900 border border-gray-300"
                    style={{ padding: "5px 3px" }}
                  >
                    {row.curr || "-"}
                  </td>
                  <td
                    className="whitespace-nowrap text-sm text-gray-900 text-right font-medium border border-gray-300"
                    style={{ padding: "5px 3px" }}
                  >
                    {formatAmount(row.curramt2)}
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

export default OverdueARTable;
