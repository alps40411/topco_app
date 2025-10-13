// frontend/src/components/SearchableDropdown.tsx

import React, { useState, useEffect, useRef } from "react";
import { ChevronDown, Search, X } from "lucide-react";

interface Option {
  id: string | number;
  name: string;
  // 新增可選欄位以支援多欄位搜尋和顯示
  empno?: string;
  empnamec?: string;
  coabbv?: string;
  deptabbv?: string;
  [key: string]: any; // 允許其他動態欄位
}

interface SearchableDropdownProps {
  label: string;
  placeholder: string;
  options: Option[];
  selectedValue?: string | number;
  onSelectionChange: (value?: string | number) => void;
  isLoading?: boolean;
  required?: boolean;
  className?: string;
  disabled?: boolean;
  // 新增多欄位搜尋相關屬性
  enableMultiFieldSearch?: boolean;
  searchFields?: string[];
  displayTemplate?: "default" | "table";
  maxVisibleItems?: number; // 最多顯示幾筆（控制下拉選單高度）
}

const SearchableDropdown: React.FC<SearchableDropdownProps> = ({
  label,
  placeholder,
  options,
  selectedValue,
  onSelectionChange,
  isLoading = false,
  required = false,
  className = "",
  disabled = false,
  enableMultiFieldSearch = false,
  searchFields = ["name"],
  displayTemplate = "default",
  maxVisibleItems = 8, // 預設顯示 8 筆
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setSearchTerm("");
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selectedOption = options.find((option) => option.id === selectedValue);

  const handleOptionSelect = (option: Option) => {
    onSelectionChange(option.id);
    setIsOpen(false);
    setSearchTerm("");
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelectionChange(undefined);
    setSearchTerm("");
  };

  const handleToggle = () => {
    if (disabled || isLoading) return;
    setIsOpen(!isOpen);
    if (!isOpen) {
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 100);
    }
  };

  // 計算顯示的選項
  let displayOptions: Option[];

  if (!searchTerm.trim()) {
    // 空搜尋詞：返回原始資料（保持原始順序）
    displayOptions = [...options];
  } else {
    // 有搜尋詞：從原始資料篩選並排序
    const term = searchTerm.toLowerCase().trim();

    const scoredOptions = options.map((option) => {
      let maxScore = 0;
      let matchedField = "";

      // 如果啟用多欄位搜尋，則搜尋所有指定欄位
      const fieldsToSearch = enableMultiFieldSearch ? searchFields : ["name"];

      fieldsToSearch.forEach((field) => {
        const fieldValue = (option[field] || "").toString().toLowerCase();
        let fieldScore = 0;

        if (fieldValue === term) {
          fieldScore = 1000;
        } else if (fieldValue.startsWith(term)) {
          fieldScore = 900;
        } else if (fieldValue.includes(term)) {
          fieldScore = 800;
        } else {
          // 模糊匹配：檢查是否包含所有搜尋字元（按順序）
          let lastIndex = -1;
          let allFound = true;

          for (const char of term) {
            const index = fieldValue.indexOf(char, lastIndex + 1);
            if (index === -1) {
              allFound = false;
              break;
            }
            lastIndex = index;
          }

          if (allFound) {
            fieldScore = 500;
          }
        }

        // 根據欄位類型調整權重（姓名優先）
        if (field === "empnamec") {
          fieldScore *= 1.2;
        } else if (field === "empno") {
          fieldScore *= 1.1;
        }

        if (fieldScore > maxScore) {
          maxScore = fieldScore;
          matchedField = field;
        }
      });

      return { option, score: maxScore, matchedField };
    });

    displayOptions = scoredOptions
      .filter((item) => item.score > 0)
      .sort((a, b) => {
        if (b.score !== a.score) {
          return b.score - a.score;
        }
        return a.option.name.length - b.option.name.length;
      })
      .map((item) => item.option);
  }

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label} {required && <span className="text-red-500">*</span>}
      </label>

      <div
        onClick={handleToggle}
        className={`
          w-full px-3 py-2 pr-8 border rounded-lg cursor-pointer flex items-center justify-between
          ${
            disabled || isLoading
              ? "bg-gray-50 text-gray-500 cursor-not-allowed"
              : "bg-white hover:border-blue-300"
          }
          ${isOpen ? "border-blue-500 ring-2 ring-blue-200" : "border-gray-300"}
        `}
      >
        {/* 選中後顯示內容 */}
        {isLoading ? (
          <span className="text-gray-500">載入中...</span>
        ) : selectedOption ? (
          displayTemplate === "table" && enableMultiFieldSearch ? (
            // 表格模式：將資訊組合成一行
            <span
              className="text-gray-900 truncate"
              style={{ fontSize: "15px" }}
            >
              {selectedOption.coabbv || "-"} {selectedOption.deptabbv || "-"}{" "}
              {selectedOption.empno || "-"} {selectedOption.empnamec || "-"}
            </span>
          ) : (
            // 預設模式：只顯示名稱
            <span className="text-gray-900" style={{ fontSize: "15px" }}>
              {selectedOption.name}
            </span>
          )
        ) : (
          <span className="text-gray-500" style={{ fontSize: "15px" }}>
            {placeholder}
          </span>
        )}

        <div className="flex items-center space-x-1 ml-2">
          {selectedOption && !disabled && !isLoading && (
            <button
              onClick={handleClear}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="h-4 w-4" />
            </button>
          )}
          <ChevronDown
            className={`h-4 w-4 text-gray-400 transition-transform ${
              isOpen ? "rotate-180" : ""
            }`}
          />
        </div>
      </div>

      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg overflow-hidden">
          <div className="p-2 border-b border-gray-200 bg-gray-50">
            <div className="relative">
              <Search className="absolute left-3 top-2 h-3.5 w-3.5 text-gray-400" />
              <input
                ref={searchInputRef}
                type="text"
                placeholder={
                  enableMultiFieldSearch
                    ? "輸入工號、姓名、公司或部門搜尋..."
                    : "輸入姓名搜尋 (如：張、元、林...)"
                }
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                style={{ fontSize: "15px" }}
              />
            </div>
          </div>

          <div
            className="overflow-y-auto"
            style={{ maxHeight: `${maxVisibleItems * 32}px` }}
            key={searchTerm}
          >
            {displayOptions.length === 0 ? (
              <div className="px-3 py-3 text-gray-500 text-center">
                <div className="text-xs font-medium">沒有找到相符的選項</div>
                <div className="text-xs mt-1">請嘗試其他關鍵字</div>
              </div>
            ) : displayTemplate === "table" && enableMultiFieldSearch ? (
              // 表格模式顯示 - 15px 字體
              <div style={{ fontSize: "15px" }}>
                {/* 表頭 */}
                <div className="sticky top-0 bg-blue-50 border-b border-blue-200 grid grid-cols-4 gap-2 px-3 py-2 font-semibold text-blue-900">
                  <div>公司名稱</div>
                  <div>部門名稱</div>
                  <div>員工工號</div>
                  <div>員工姓名</div>
                </div>
                {/* 資料行 */}
                {displayOptions.map((option, index) => (
                  <div
                    key={`${searchTerm}-${option.id}-${index}`}
                    onClick={() => handleOptionSelect(option)}
                    className={`
                      grid grid-cols-4 gap-2 px-3 py-2 cursor-pointer hover:bg-blue-50 transition-colors border-b border-gray-100
                      ${
                        selectedValue === option.id
                          ? "bg-blue-100 text-blue-800 font-medium"
                          : "text-gray-900"
                      }
                    `}
                  >
                    <div className="truncate">{option.coabbv || "-"}</div>
                    <div className="truncate">{option.deptabbv || "-"}</div>
                    <div className="truncate">{option.empno || "-"}</div>
                    <div className="truncate">{option.empnamec || "-"}</div>
                  </div>
                ))}
              </div>
            ) : (
              // 預設單行模式顯示 - 15px 字體
              displayOptions.map((option, index) => (
                <div
                  key={`${searchTerm}-${option.id}-${index}`}
                  onClick={() => handleOptionSelect(option)}
                  className={`
                    px-3 py-2 cursor-pointer hover:bg-blue-50 transition-colors
                    ${
                      selectedValue === option.id
                        ? "bg-blue-100 text-blue-800 font-medium"
                        : "text-gray-900"
                    }
                  `}
                  style={{ fontSize: "15px" }}
                >
                  {option.name}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchableDropdown;
