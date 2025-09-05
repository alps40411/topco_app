// frontend/src/components/MultiSelectChips.tsx

import React, { useState } from "react";
import { X } from "lucide-react";

interface Option {
  id: string;
  name: string;
}

interface MultiSelectChipsProps {
  label: string;
  options: Option[];
  selectedValues: string[];
  onSelectionChange: (values: string[]) => void;
  placeholder?: string;
  required?: boolean;
  className?: string;
  disabled?: boolean;
}

const MultiSelectChips: React.FC<MultiSelectChipsProps> = ({
  label,
  options,
  selectedValues,
  onSelectionChange,
  placeholder = "請選擇項目",
  required = false,
  className = "",
  disabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const handleToggle = () => {
    if (disabled) return;
    setIsOpen(!isOpen);
  };

  const handleOptionToggle = (optionId: string) => {
    if (disabled) return;

    const isSelected = selectedValues.includes(optionId);
    let newValues;

    if (isSelected) {
      newValues = selectedValues.filter((id) => id !== optionId);
    } else {
      newValues = [...selectedValues, optionId];
    }

    onSelectionChange(newValues);
  };

  const handleRemoveChip = (optionId: string) => {
    if (disabled) return;
    const newValues = selectedValues.filter((id) => id !== optionId);
    onSelectionChange(newValues);
  };

  const selectedOptions = options.filter((option) =>
    selectedValues.includes(option.id)
  );

  return (
    <div className={`relative ${className}`}>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label} {required && <span className="text-red-500">*</span>}
      </label>

      {/* 已選擇的項目顯示為 chips */}
      {selectedOptions.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2">
          {selectedOptions.map((option) => (
            <div
              key={option.id}
              className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800 border border-blue-200"
            >
              <span>{option.name}</span>
              {!disabled && (
                <button
                  onClick={() => handleRemoveChip(option.id)}
                  className="ml-2 text-blue-600 hover:text-blue-800"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 選擇區域 */}
      <div
        onClick={handleToggle}
        className={`
          w-full px-3 py-2 border rounded-lg cursor-pointer flex items-center justify-between
          ${
            disabled
              ? "bg-gray-50 text-gray-500 cursor-not-allowed"
              : "bg-white hover:border-blue-300"
          }
          ${isOpen ? "border-blue-500 ring-2 ring-blue-200" : "border-gray-300"}
        `}
      >
        <span
          className={
            selectedOptions.length > 0 ? "text-gray-900" : "text-gray-500"
          }
        >
          {selectedOptions.length > 0
            ? `${selectedOptions.length} 個項目已選擇`
            : placeholder}
        </span>
        <div className="text-gray-400">{isOpen ? "▲" : "▼"}</div>
      </div>

      {/* 選項列表 */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {options.length === 0 ? (
            <div className="px-3 py-2 text-gray-500 text-center">
              暫無可選項目
            </div>
          ) : (
            options.map((option) => (
              <div
                key={option.id}
                onClick={() => handleOptionToggle(option.id)}
                className={`
                  px-3 py-2 cursor-pointer hover:bg-blue-50 flex items-center
                  ${
                    selectedValues.includes(option.id)
                      ? "bg-blue-100 text-blue-800"
                      : "text-gray-900"
                  }
                `}
              >
                <div className="flex items-center">
                  <div
                    className={`
                    w-4 h-4 border rounded mr-3 flex items-center justify-center
                    ${
                      selectedValues.includes(option.id)
                        ? "bg-blue-600 border-blue-600"
                        : "border-gray-300"
                    }
                  `}
                  >
                    {selectedValues.includes(option.id) && (
                      <div className="w-2 h-2 bg-white rounded-sm"></div>
                    )}
                  </div>
                  <span>{option.name}</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default MultiSelectChips;
