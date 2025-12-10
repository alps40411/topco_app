// frontend/src/components/InlineMultiSelect.tsx

import React from "react";

interface Option {
  id: string;
  name: string;
}

interface InlineMultiSelectProps {
  label: string;
  options: Option[];
  selectedValues: string[];
  onSelectionChange: (values: string[]) => void;
  placeholder?: string;
  required?: boolean;
  className?: string;
  disabled?: boolean;
}

const InlineMultiSelect: React.FC<InlineMultiSelectProps> = ({
  label,
  options,
  selectedValues,
  onSelectionChange,
  placeholder = "請選擇項目",
  required = false,
  className = "",
  disabled = false,
}) => {
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

  return (
    <div className={`space-y-3 ${className}`}>
      <label className="block text-sm font-medium text-gray-700">
        {label} {required && <span className="text-red-500">*</span>}
      </label>

      {/* 可選項目列表 - 緊湊網格佈局 */}
      {options.length > 0 ? (
        <div className="grid grid-cols-2 gap-2 border border-gray-200 rounded-lg p-3">
          {options.map((option) => {
            const isSelected = selectedValues.includes(option.id);
            return (
              <label
                key={option.id}
                className={`
                  flex items-center space-x-2 p-1 rounded cursor-pointer transition-colors text-ss
                  ${
                    isSelected
                      ? "bg-blue-50 border border-blue-200"
                      : "hover:bg-gray-50 border border-transparent"
                  }
                  ${disabled ? "opacity-50 cursor-not-allowed" : ""}
                `}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => handleOptionToggle(option.id)}
                  disabled={disabled}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 w-4 h-4"
                />
                <span className="text-gray-700 flex-1 truncate">
                  {option.name}
                </span>
              </label>
            );
          })}
        </div>
      ) : (
        <div className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500 text-center">
          {placeholder}
        </div>
      )}
    </div>
  );
};

export default InlineMultiSelect;
