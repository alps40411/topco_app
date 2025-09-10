// frontend/src/components/EnhancedDateSelector.tsx

import React, { useState, useEffect, useRef } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Calendar,
  ChevronDown,
} from "lucide-react";

interface EnhancedDateSelectorProps {
  selectedDate: Date | null;
  onChange: (date: Date) => void;
  className?: string;
}

const EnhancedDateSelector: React.FC<EnhancedDateSelectorProps> = ({
  selectedDate,
  onChange,
  className = "",
}) => {
  const [showCalendar, setShowCalendar] = useState(false);
  const [showQuickSelect, setShowQuickSelect] = useState(false);
  const [currentMonth, setCurrentMonth] = useState(
    selectedDate || new Date()
  );
  const calendarRef = useRef<HTMLDivElement>(null);
  const quickSelectRef = useRef<HTMLDivElement>(null);

  // 生成最近30天的選項
  const generateQuickSelectOptions = () => {
    const options = [];
    const today = new Date();
    
    for (let i = 0; i < 30; i++) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);
      
      const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
      const weekday = weekdays[date.getDay()];
      
      options.push({
        date: date,
        label: `${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')}(${weekday})`,
        value: date.toISOString().slice(0, 10).replace(/-/g, '')
      });
    }
    
    return options;
  };

  const quickSelectOptions = generateQuickSelectOptions();

  // 點擊外部關閉下拉選單
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (calendarRef.current && !calendarRef.current.contains(event.target as Node)) {
        setShowCalendar(false);
      }
      if (quickSelectRef.current && !quickSelectRef.current.contains(event.target as Node)) {
        setShowQuickSelect(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // 獲取當前月份的日期網格
  const getCalendarDays = () => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    
    // 獲取當月第一天和最後一天
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    
    // 獲取上個月的最後幾天
    const prevMonth = new Date(year, month - 1, 0);
    const daysInPrevMonth = prevMonth.getDate();
    const startDayOfWeek = firstDay.getDay(); // 0=Sunday, 1=Monday, etc.
    
    const days = [];
    
    // 上個月的日期
    for (let i = startDayOfWeek - 1; i >= 0; i--) {
      const date = new Date(year, month - 1, daysInPrevMonth - i);
      days.push({
        date,
        isCurrentMonth: false,
        isPrevMonth: true,
        isNextMonth: false,
      });
    }
    
    // 當前月份的日期
    for (let day = 1; day <= daysInMonth; day++) {
      const date = new Date(year, month, day);
      days.push({
        date,
        isCurrentMonth: true,
        isPrevMonth: false,
        isNextMonth: false,
      });
    }
    
    // 下個月的日期（補足42個格子，6週）
    const totalCells = 42;
    const remainingCells = totalCells - days.length;
    for (let day = 1; day <= remainingCells; day++) {
      const date = new Date(year, month + 1, day);
      days.push({
        date,
        isCurrentMonth: false,
        isPrevMonth: false,
        isNextMonth: true,
      });
    }
    
    return days;
  };

  const isToday = (date: Date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  const isSelected = (date: Date) => {
    return selectedDate && date.toDateString() === selectedDate.toDateString();
  };

  const isWeekend = (date: Date) => {
    const day = date.getDay();
    return day === 0 || day === 6; // Sunday or Saturday
  };

  const handleDateClick = (date: Date) => {
    onChange(date);
    setShowCalendar(false);
  };

  const handleQuickSelect = (option: any) => {
    onChange(option.date);
    setShowQuickSelect(false);
  };

  const navigateMonth = (direction: 'prev' | 'next') => {
    const newMonth = new Date(currentMonth);
    if (direction === 'prev') {
      newMonth.setMonth(currentMonth.getMonth() - 1);
    } else {
      newMonth.setMonth(currentMonth.getMonth() + 1);
    }
    setCurrentMonth(newMonth);
  };

  const calendarDays = getCalendarDays();
  const today = new Date();

  return (
    <div className={`relative ${className}`}>
      {/* 桌面版本 */}
      <div className="hidden sm:flex items-center space-x-2 bg-white border border-gray-200 rounded-lg p-1 shadow-sm">
        {/* 上一天按鈕 */}
        <button
          onClick={() => {
            if (selectedDate) {
              const prevDay = new Date(selectedDate);
              prevDay.setDate(selectedDate.getDate() - 1);
              onChange(prevDay);
            }
          }}
          className="p-2 rounded hover:bg-gray-100 transition-colors group"
          title="上一天"
        >
          <ChevronLeft className="w-5 h-5 text-gray-600 group-hover:text-gray-800" />
        </button>

        {/* 主要日期顯示按鈕 */}
        <button
          onClick={() => {
            setShowCalendar(!showCalendar);
            setShowQuickSelect(false);
          }}
          className="flex items-center space-x-2 p-2 hover:bg-gray-100 rounded transition-colors min-w-[140px] group"
        >
          <Calendar className="w-5 h-5 text-gray-500 group-hover:text-blue-600" />
          <span className="font-semibold text-gray-700 group-hover:text-gray-900">
            {selectedDate
              ? selectedDate.toLocaleDateString("zh-TW", {
                  year: "numeric",
                  month: "2-digit",
                  day: "2-digit",
                })
              : "選擇日期"}
          </span>
        </button>

        {/* 快速選擇下拉按鈕 */}
        <div className="relative" ref={quickSelectRef}>
          <button
            onClick={() => {
              setShowQuickSelect(!showQuickSelect);
              setShowCalendar(false);
            }}
            className="p-2 rounded hover:bg-gray-100 transition-colors group"
            title="快速選擇最近日期"
          >
            <ChevronDown className="w-5 h-5 text-gray-600 group-hover:text-blue-600" />
          </button>

          {/* 快速選擇下拉選單 */}
          {showQuickSelect && (
            <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-60 overflow-y-auto">
              <div className="py-1">
                {quickSelectOptions.map((option, index) => (
                  <button
                    key={index}
                    onClick={() => handleQuickSelect(option)}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-blue-50 hover:text-blue-700 transition-colors ${
                      isSelected(option.date) ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 下一天按鈕 */}
        <button
          onClick={() => {
            if (selectedDate) {
              const nextDay = new Date(selectedDate);
              nextDay.setDate(selectedDate.getDate() + 1);
              onChange(nextDay);
            }
          }}
          className="p-2 rounded hover:bg-gray-100 transition-colors group"
          title="下一天"
        >
          <ChevronRight className="w-5 h-5 text-gray-600 group-hover:text-gray-800" />
        </button>
      </div>

      {/* 手機版本 - 更緊湊的布局 */}
      <div className="sm:hidden flex items-center space-x-1 bg-white border border-gray-200 rounded-lg p-1 shadow-sm">
        <button
          onClick={() => {
            if (selectedDate) {
              const prevDay = new Date(selectedDate);
              prevDay.setDate(selectedDate.getDate() - 1);
              onChange(prevDay);
            }
          }}
          className="p-2 rounded hover:bg-gray-100 transition-colors"
          title="上一天"
        >
          <ChevronLeft className="w-4 h-4 text-gray-600" />
        </button>

        <button
          onClick={() => {
            setShowCalendar(!showCalendar);
            setShowQuickSelect(false);
          }}
          className="flex items-center space-x-2 p-2 hover:bg-gray-100 rounded transition-colors flex-1 min-w-0"
        >
          <Calendar className="w-4 h-4 text-gray-500 flex-shrink-0" />
          <span className="font-semibold text-gray-700 text-sm truncate">
            {selectedDate
              ? selectedDate.toLocaleDateString("zh-TW", {
                  month: "2-digit",
                  day: "2-digit",
                })
              : "選日期"}
          </span>
        </button>

        <div className="relative" ref={quickSelectRef}>
          <button
            onClick={() => {
              setShowQuickSelect(!showQuickSelect);
              setShowCalendar(false);
            }}
            className="p-2 rounded hover:bg-gray-100 transition-colors"
            title="快選"
          >
            <ChevronDown className="w-4 h-4 text-gray-600" />
          </button>

          {showQuickSelect && (
            <div className="absolute right-0 top-full mt-1 w-44 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-48 overflow-y-auto">
              <div className="py-1">
                {quickSelectOptions.slice(0, 14).map((option, index) => (
                  <button
                    key={index}
                    onClick={() => handleQuickSelect(option)}
                    className={`w-full text-left px-3 py-2 text-xs hover:bg-blue-50 hover:text-blue-700 transition-colors ${
                      isSelected(option.date) ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <button
          onClick={() => {
            if (selectedDate) {
              const nextDay = new Date(selectedDate);
              nextDay.setDate(selectedDate.getDate() + 1);
              onChange(nextDay);
            }
          }}
          className="p-2 rounded hover:bg-gray-100 transition-colors"
          title="下一天"
        >
          <ChevronRight className="w-4 h-4 text-gray-600" />
        </button>
      </div>

      {/* 月曆下拉面板 */}
      {showCalendar && (
        <div 
          ref={calendarRef}
          className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 p-4 w-80 sm:w-96"
        >
          {/* 月份導航 */}
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => navigateMonth('prev')}
              className="p-1 rounded hover:bg-gray-100 transition-colors"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            
            <h3 className="font-semibold text-gray-900">
              {currentMonth.toLocaleDateString("zh-TW", {
                year: "numeric",
                month: "long",
              })}
            </h3>
            
            <button
              onClick={() => navigateMonth('next')}
              className="p-1 rounded hover:bg-gray-100 transition-colors"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>

          {/* 星期標題 */}
          <div className="grid grid-cols-7 gap-1 mb-2">
            {['日', '一', '二', '三', '四', '五', '六'].map((day, index) => (
              <div
                key={day}
                className={`text-center text-xs font-medium p-2 ${
                  index === 0 || index === 6 ? 'text-red-500' : 'text-gray-500'
                }`}
              >
                {day}
              </div>
            ))}
          </div>

          {/* 日期網格 */}
          <div className="grid grid-cols-7 gap-1">
            {calendarDays.map((day, index) => (
              <button
                key={index}
                onClick={() => handleDateClick(day.date)}
                className={`
                  p-2 text-sm rounded transition-colors relative
                  ${!day.isCurrentMonth ? 'text-gray-300' : 'text-gray-700'}
                  ${isWeekend(day.date) && day.isCurrentMonth ? 'text-red-500' : ''}
                  ${isToday(day.date) ? 'bg-blue-100 text-blue-700 font-bold' : ''}
                  ${isSelected(day.date) ? 'bg-blue-500 text-white font-bold' : ''}
                  ${day.isCurrentMonth && !isSelected(day.date) && !isToday(day.date) 
                    ? 'hover:bg-gray-100' : ''}
                `}
                disabled={!day.isCurrentMonth}
              >
                {day.date.getDate()}
                {isToday(day.date) && !isSelected(day.date) && (
                  <div className="absolute bottom-1 left-1/2 transform -translate-x-1/2 w-1 h-1 bg-blue-500 rounded-full"></div>
                )}
              </button>
            ))}
          </div>

          {/* 今天快速跳轉 */}
          <div className="mt-4 pt-3 border-t border-gray-200">
            <button
              onClick={() => handleDateClick(today)}
              className="w-full text-center text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              跳轉到今天 ({today.toLocaleDateString("zh-TW", {
                month: "2-digit",
                day: "2-digit",
              })})
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default EnhancedDateSelector;