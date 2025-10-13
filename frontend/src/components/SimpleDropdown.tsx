// frontend/src/components/SimpleDropdown.tsx

import React, { useState, useRef, useEffect } from "react";
import { ChevronDown, X } from "lucide-react";

interface Option {
  id: string | number;
  name: string;
}

interface SimpleDropdownProps {
  label: string;
  placeholder: string;
  options: Option[];
  selectedValue?: string | number;
  onSelectionChange: (value?: string | number) => void;
  isLoading?: boolean;
  required?: boolean;
  className?: string;
  disabled?: boolean;
  maxVisibleItems?: number; // 最多顯示幾筆（控制下拉選單高度）
}

const SimpleDropdown: React.FC<SimpleDropdownProps> = ({
  label,
  placeholder,
  options,
  selectedValue,
  onSelectionChange,
  isLoading = false,
  required = false,
  className = "",
  disabled = false,
  maxVisibleItems = 12, // 預設顯示 12 筆
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selectedOption = options.find((option) => option.id === selectedValue);

  const handleOptionSelect = (option: Option) => {
    onSelectionChange(option.id);
    setIsOpen(false);
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelectionChange(undefined);
  };

  const handleToggle = () => {
    if (disabled || isLoading) return;
    setIsOpen(!isOpen);
  };

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
        <div
          className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg overflow-y-auto"
          style={{ maxHeight: `${maxVisibleItems * 32}px` }}
        >
          {options.length === 0 ? (
            <div className="px-3 py-3 text-gray-500 text-center">
              <div className="font-medium" style={{ fontSize: "15px" }}>
                沒有可選項目
              </div>
            </div>
          ) : (
            options.map((option) => (
              <div
                key={option.id}
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
      )}
    </div>
  );
};

export default SimpleDropdown;
