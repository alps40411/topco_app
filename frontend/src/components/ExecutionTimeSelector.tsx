// frontend/src/components/ExecutionTimeSelector.tsx

import React from 'react';
import { Clock } from 'lucide-react';

interface ExecutionTimeSelectorProps {
  totalMinutes: number;
  onChange: (minutes: number) => void;
  className?: string;
  required?: boolean;
}

const ExecutionTimeSelector: React.FC<ExecutionTimeSelectorProps> = ({
  totalMinutes,
  onChange,
  className = "",
  required = false
}) => {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  const handleHoursChange = (newHours: number) => {
    onChange(newHours * 60 + minutes);
  };

  const handleMinutesChange = (newMinutes: number) => {
    onChange(hours * 60 + newMinutes);
  };

  const formatTotalTime = () => {
    if (totalMinutes === 0) return "未設定";
    const hours = totalMinutes / 60;
    return `共 ${hours.toFixed(2)} 小時`;
  };

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="flex items-center space-x-2">
        <Clock className="w-4 h-4 text-gray-600" />
        <label className="text-sm font-medium text-gray-700">
          執行時間 {required && <span className="text-red-500">*</span>}
        </label>
      </div>
      
      <div className="flex items-center space-x-2">
        {/* 小時選擇器 */}
        <div className="flex-1">
          <select 
            value={hours}
            onChange={(e) => handleHoursChange(parseInt(e.target.value))}
            className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {Array.from({ length: 9 }, (_, i) => (
              <option key={i} value={i}>
                {i} 小時
              </option>
            ))}
          </select>
        </div>

        {/* 分鐘選擇器 */}
        <div className="flex-1">
          <select 
            value={minutes}
            onChange={(e) => handleMinutesChange(parseInt(e.target.value))}
            className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {Array.from({ length: 12 }, (_, i) => i * 5).map((minute) => (
              <option key={minute} value={minute}>
                {minute} 分鐘
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 總時間顯示 */}
      <div className={`text-sm font-medium p-2 rounded ${
        totalMinutes === 0 
          ? 'text-red-600 bg-red-50 border border-red-200' 
          : 'text-blue-600 bg-blue-50 border border-blue-200'
      }`}>
        {formatTotalTime()}
      </div>

      {required && totalMinutes === 0 && (
        <div className="text-xs text-red-500">
          請設定執行時間
        </div>
      )}
    </div>
  );
};

export default ExecutionTimeSelector;