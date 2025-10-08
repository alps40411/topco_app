// frontend/src/components/SearchableDropdown.tsx

import React, { useState, useEffect, useRef } from "react";
import { ChevronDown, Search, X } from "lucide-react";

interface Option {
  id: string | number;
  name: string;
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
      const name = option.name.toLowerCase();
      let score = 0;

      if (name === term) {
        score = 1000;
      } else if (name.startsWith(term)) {
        score = 900;
      } else if (name.includes(term)) {
        score = 800;
      } else {
        let lastIndex = -1;
        let allFound = true;

        for (const char of term) {
          const index = name.indexOf(char, lastIndex + 1);
          if (index === -1) {
            allFound = false;
            break;
          }
          lastIndex = index;
        }

        if (allFound) {
          score = 500;
        }
      }

      return { option, score };
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
        <span className={selectedOption ? "text-gray-900" : "text-gray-500"}>
          {isLoading ? "載入中..." : selectedOption?.name || placeholder}
        </span>
        <div className="flex items-center space-x-1">
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
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-64 overflow-hidden">
          <div className="p-2 border-b border-gray-200 bg-gray-50">
            <div className="relative">
              <Search className="absolute left-3 top-2 h-3.5 w-3.5 text-gray-400" />
              <input
                ref={searchInputRef}
                type="text"
                placeholder="輸入姓名搜尋 (如：張、元、林...)"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          <div className="max-h-52 overflow-y-auto" key={searchTerm}>
            {displayOptions.length === 0 ? (
              <div className="px-3 py-3 text-gray-500 text-center">
                <div className="text-xs font-medium">沒有找到相符的選項</div>
                <div className="text-xs mt-1">請嘗試其他關鍵字</div>
              </div>
            ) : (
              displayOptions.map((option, index) => (
                <div
                  key={`${searchTerm}-${option.id}-${index}`}
                  onClick={() => handleOptionSelect(option)}
                  className={`
                    px-3 py-1 cursor-pointer hover:bg-blue-50 text-xs transition-colors
                    ${
                      selectedValue === option.id
                        ? "bg-blue-100 text-blue-800 font-medium"
                        : "text-gray-900"
                    }
                  `}
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
