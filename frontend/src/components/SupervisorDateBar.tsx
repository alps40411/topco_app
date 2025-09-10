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

  // Gets the dates from the last 30 days that fall in the previous month.
  const getPrevMonthDates = () => {
    const dates = [];
    const prevMonth = currentMonth - 1;
    const actualPrevMonth = prevMonth < 0 ? 11 : prevMonth;

    for (let i = 29; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);

      if (date.getMonth() === actualPrevMonth) {
        const dateString = `${date.getFullYear()}${String(
          date.getMonth() + 1
        ).padStart(2, "0")}${String(date.getDate()).padStart(2, "0")}`;
        const dayOfWeek = date.getDay();

        dates.push({
          day: String(date.getDate()).padStart(2, "0"),
          dateString,
          isSaturday: dayOfWeek === 6,
          isSunday: dayOfWeek === 0,
        });
      }
    }
    return dates;
  };

  // Gets the dates from the last 30 days that fall in the current month, excluding today.
  const getCurrentMonthDates = () => {
    const dates = [];
    for (let i = 29; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);

      if (
        date.getMonth() === currentMonth &&
        date.toDateString() !== today.toDateString()
      ) {
        const dateString = `${date.getFullYear()}${String(
          date.getMonth() + 1
        ).padStart(2, "0")}${String(date.getDate()).padStart(2, "0")}`;
        const dayOfWeek = date.getDay();

        dates.push({
          day: String(date.getDate()).padStart(2, "0"),
          dateString,
          isSaturday: dayOfWeek === 6,
          isSunday: dayOfWeek === 0,
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
    const month = parseInt(dateString.substring(4, 6)) - 1;
    const day = parseInt(dateString.substring(6, 8));
    const date = new Date(year, month, day, 12, 0, 0);
    onChange(date);
  };

  const formatTodayDate = () => {
    return `${currentYear}${String(currentMonth + 1).padStart(2, "0")}${String(
      today.getDate()
    ).padStart(2, "0")}`;
  };

  const prevMonthDates = getPrevMonthDates();
  const currentMonthDates = getCurrentMonthDates();

  const prevMonth = currentMonth - 1;
  const actualPrevMonth = prevMonth < 0 ? 11 : prevMonth;
  const monthNames = [
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "11",
    "12",
  ];

  return (
    <div className={`w-full ${className}`}>
      <div className="w-full border-collapse bg-white border border-gray-300 rounded-lg shadow-sm overflow-hidden">
        <table className="w-full">
          <tbody>
            <tr className="border-b border-gray-300">
              {/* Previous Month Header */}
              <td className="bg-gray-200 text-center p-3 border-r border-gray-300 min-w-[80px]">
                <div className="text-lg font-bold text-gray-700">
                  <span className="text-2xl">
                    {monthNames[actualPrevMonth]}
                  </span>
                  月
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
                        min-w-[32px] h-8 text-sm rounded border transition-colors font-medium
                        ${dateInfo.isSaturday ? "text-[#C3D600]" : ""}
                        ${dateInfo.isSunday ? "text-[#FF0000]" : ""}
                        ${
                          isSelected(dateInfo.dateString)
                            ? "bg-gray-500 text-white border-gray-500"
                            : "bg-white text-gray-700 border-gray-300 hover:bg-gray-100"
                        }
                      `}
                    >
                      {dateInfo.day}
                    </button>
                  ))}
                </div>
              </td>

              {/* Current Month Header */}
              <td className="bg-gray-200 text-center p-3 border-r border-gray-300 min-w-[80px]">
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
                        min-w-[32px] h-8 text-sm rounded border transition-colors font-medium
                        ${dateInfo.isSaturday ? "text-[#C3D600]" : ""}
                        ${dateInfo.isSunday ? "text-[#FF0000]" : ""}
                        ${
                          isSelected(dateInfo.dateString)
                            ? "bg-gray-400 text-white border-gray-400"
                            : "bg-white text-gray-700 border-gray-300 hover:bg-gray-100"
                        }
                      `}
                    >
                      {dateInfo.day}
                    </button>
                  ))}
                </div>
              </td>

              {/* Today Indicator */}
              <td className="bg-gray-100 text-center p-3 min-w-[120px]">
                <div className="text-sm">
                  <span className="text-gray-700">今天是</span>
                  <button
                    onClick={() => handleDateClick(formatTodayDate())}
                    className={`
                      mx-1 px-2 py-1 rounded transition-colors font-semibold
                      ${
                        isSelected(formatTodayDate())
                          ? "bg-gray-400 text-white"
                          : "bg-white hover:bg-gray-200 text-gray-800 ring-1 ring-gray-400"
                      }
                    `}
                  >
                    {today.getDate()}
                  </button>
                </div>
                <div className="text-xs text-gray-600 mt-1">
                  (星期
                  {["日", "一", "二", "三", "四", "五", "六"][today.getDay()]})
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
