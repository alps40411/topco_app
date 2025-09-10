// frontend/src/components/SupervisorDateBar.tsx

import React from "react";

interface SupervisorDateBarProps {
  selectedDate: Date | null;
  onChange: (date: Date) => void;
  className?: string;
}

const SupervisorDateBar: React.FC<SupervisorDateBarProps> = ({
  selectedDate,
  onChange,
  className = "",
}) => {
  const today = new Date();
  const currentDate = selectedDate || today;
  const currentMonth = today.getMonth();
  const currentYear = today.getFullYear();

  // 獲取上個月的最後部分日期（從今天往前推30天但按月分組）
  const getPrevMonthDates = () => {
    const dates = [];
    const prevMonth = currentMonth - 1;
    const prevMonthYear = prevMonth < 0 ? currentYear - 1 : currentYear;
    const actualPrevMonth = prevMonth < 0 ? 11 : prevMonth;
    
    // 從今天往前推，找到上個月的日期
    for (let i = 29; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);
      
      if (date.getMonth() === actualPrevMonth) {
        const dateString = `${date.getFullYear()}${String(date.getMonth() + 1).padStart(2, "0")}${String(date.getDate()).padStart(2, "0")}`;
        const dayOfWeek = date.getDay();

        dates.push({
          day: String(date.getDate()).padStart(2, "0"),
          dateString,
          isWeekend: dayOfWeek === 0 || dayOfWeek === 6,
          isSaturday: dayOfWeek === 6,
          isSunday: dayOfWeek === 0,
          isToday: date.toDateString() === today.toDateString(),
        });
      }
    }

    return dates;
  };

  // 獲取當前月的日期
  const getCurrentMonthDates = () => {
    const dates = [];
    
    // 從今天往前推，找到當前月的日期
    for (let i = 29; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);
      
      if (date.getMonth() === currentMonth) {
        const dateString = `${date.getFullYear()}${String(date.getMonth() + 1).padStart(2, "0")}${String(date.getDate()).padStart(2, "0")}`;
        const dayOfWeek = date.getDay();

        dates.push({
          day: String(date.getDate()).padStart(2, "0"),
          dateString,
          isWeekend: dayOfWeek === 0 || dayOfWeek === 6,
          isSaturday: dayOfWeek === 6,
          isSunday: dayOfWeek === 0,
          isToday: date.toDateString() === today.toDateString(),
        });
      }
    }

    return dates;
  };

  const isSelected = (dateString: string) => {
    const selectedDateString = currentDate
      .toISOString()
      .slice(0, 10)
      .replace(/-/g, "");
    return selectedDateString === dateString;
  };

  const handleDateClick = (dateString: string) => {
    const year = parseInt(dateString.substring(0, 4));
    const month = parseInt(dateString.substring(4, 6)) - 1; // JavaScript 月份從0開始
    const day = parseInt(dateString.substring(6, 8));
    // 使用本地時間中午12點避免時區問題
    const date = new Date(year, month, day, 12, 0, 0);
    onChange(date);
  };

  const formatTodayDate = () => {
    return `${currentYear}${String(currentMonth + 1).padStart(2, "0")}${String(today.getDate()).padStart(2, "0")}`;
  };

  const prevMonthDates = getPrevMonthDates();
  const currentMonthDates = getCurrentMonthDates();
  
  const prevMonth = currentMonth - 1;
  const actualPrevMonth = prevMonth < 0 ? 11 : prevMonth;
  
  const monthNames = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"];

  return (
    <div className={`w-full ${className}`}>
      <div className="w-full border-collapse bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        <table className="w-full">
          <tbody>
            <tr className="border border-gray-300">
              {/* Previous Month Header */}
              <td className="bg-gray-100 text-center p-3 border-r border-gray-300 min-w-[80px]">
                <div className="text-lg font-bold text-gray-600">
                  <span className="text-2xl">{monthNames[actualPrevMonth]}</span>月
                </div>
                <div className="text-xs text-gray-500 mt-1">month</div>
              </td>

              {/* Previous Month Dates */}
              <td className="p-2 border-r border-gray-300">
                <div className="flex flex-wrap gap-1">
                  {prevMonthDates.map((dateInfo) => (
                    <button
                      key={dateInfo.dateString}
                      onClick={() => handleDateClick(dateInfo.dateString)}
                      className={`
                        min-w-[32px] h-8 text-sm border border-gray-200 hover:bg-blue-50 transition-colors
                        ${dateInfo.isSaturday ? "bg-blue-100 text-blue-700" : ""}
                        ${dateInfo.isSunday ? "bg-red-100 text-red-700" : ""}
                        ${isSelected(dateInfo.dateString) ? "bg-blue-500 text-white" : ""}
                        ${dateInfo.isToday ? "bg-green-500 text-white ring-2 ring-green-300" : ""}
                      `}
                    >
                      {dateInfo.day}
                    </button>
                  ))}
                </div>
              </td>

              {/* Current Month Header */}
              <td className="bg-yellow-100 text-center p-3 border-r border-gray-300 min-w-[80px]">
                <div className="text-lg font-bold text-gray-800">
                  <span className="text-2xl">{monthNames[currentMonth]}</span>月
                </div>
                <div className="text-xs text-gray-600 mt-1">month</div>
              </td>

              {/* Current Month Dates */}
              <td className="p-2 border-r border-gray-300">
                <div className="flex flex-wrap gap-1">
                  {currentMonthDates.map((dateInfo) => (
                    <button
                      key={dateInfo.dateString}
                      onClick={() => handleDateClick(dateInfo.dateString)}
                      className={`
                        min-w-[32px] h-8 text-sm border border-gray-200 hover:bg-blue-50 transition-colors
                        ${dateInfo.isSaturday ? "bg-blue-100 text-blue-700" : ""}
                        ${dateInfo.isSunday ? "bg-red-100 text-red-700" : ""}
                        ${isSelected(dateInfo.dateString) ? "bg-blue-500 text-white" : ""}
                        ${dateInfo.isToday ? "bg-green-500 text-white ring-2 ring-green-300" : ""}
                      `}
                    >
                      {dateInfo.day}
                    </button>
                  ))}
                </div>
              </td>

              {/* Today Indicator */}
              <td className="bg-green-100 text-center p-3 min-w-[120px]">
                <div className="text-sm">
                  <span className="text-gray-700">今天是</span>
                  <button
                    onClick={() => handleDateClick(formatTodayDate())}
                    className={`
                      mx-1 px-2 py-1 bg-green-200 hover:bg-green-300 rounded transition-colors
                      ${isSelected(formatTodayDate()) ? "bg-green-500 text-white" : ""}
                    `}
                  >
                    {today.getDate()}
                  </button>
                </div>
                <div className="text-xs text-gray-600 mt-1">
                  (星期{['日', '一', '二', '三', '四', '五', '六'][today.getDay()]})
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SupervisorDateBar;
