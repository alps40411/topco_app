// frontend/src/components/MyReportsTab.tsx

import React, { useState, useEffect } from 'react';
import { Calendar, ChevronLeft, ChevronRight, Eye, MessageCircle, Star } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import ChatInterface from './ChatInterface';
import AttachedFilesDisplay from './AttachedFilesDisplay';
import { getProjectColors } from '../utils/colorUtils';
import type { DailyReport } from '../App';
import DatePicker from 'react-datepicker';
import "react-datepicker/dist/react-datepicker.css";
import toast from 'react-hot-toast';

const MyReportsTab: React.FC = () => {
  const [reports, setReports] = useState<DailyReport[]>([]);
  const [selectedReport, setSelectedReport] = useState<DailyReport | null>(null);
  const [selectedDate, setSelectedDate] = useState<Date | null>(new Date());
  const [isLoading, setIsLoading] = useState(true);
  const { authFetch, user } = useAuth();

  const fetchMyReports = async () => {
    if (!selectedDate || !user) return;

    setIsLoading(true);
    try {
      const dateString = selectedDate.toISOString().split('T')[0];
      const response = await authFetch(`/api/supervisor/reports-by-date?date=${dateString}`);
      if (response.ok) {
        const allReports: DailyReport[] = await response.json();
        // 只顯示自己的日報 - 根據用戶ID進行篩選
        const myReports = allReports.filter(report => {
          // 如果是主管，只顯示主管自己提交的日報（如果有的話）
          // 如果是員工，只顯示該員工的日報
          if (user.is_supervisor) {
            // 主管通常不會有employee記錄，這裡可能需要根據實際資料結構調整
            return report.employee.id === user.id; 
          } else {
            // 員工只能看到自己的日報
            return report.employee.name === user.name || report.employee.id === user.id;
          }
        });
        setReports(myReports);
      } else {
        setReports([]);
      }
    } catch (error) {
      console.error('獲取日報失敗:', error);
      toast.error('載入日報失敗');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMyReports();
  }, [selectedDate]);

  const changeDate = (offset: number) => {
    setSelectedDate(prevDate => {
      if (!prevDate) return new Date();
      const newDate = new Date(prevDate);
      newDate.setDate(newDate.getDate() + offset);
      return newDate;
    });
  };

  const handleDateChange = (date: Date | null) => {
    if (date) {
      setSelectedDate(date);
      setSelectedReport(null);
    }
  };

  const formatDate = (dateString: string) =>
    new Date(dateString).toLocaleDateString("zh-TW", {
      year: "numeric",
      month: "numeric",
      day: "numeric",
    });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return (
          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
            <MessageCircle className="w-3 h-3 mr-1" />
            待審核
          </span>
        );
      case 'reviewed':
        return (
          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
            <Eye className="w-3 h-3 mr-1" />
            已審核
          </span>
        );
      default:
        return null;
    }
  };

  if (selectedReport) {
    return (
      <div className="p-6 h-screen flex flex-col">
        {/* 標題列 */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setSelectedReport(null)}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">
                我的日報 - {formatDate(selectedReport.date)}
              </h2>
              <div className="flex items-center space-x-3 mt-1">
                {getStatusBadge(selectedReport.status)}
                {selectedReport.rating && (
                  <div className="flex items-center space-x-1">
                    <span className="text-sm text-gray-600">評分:</span>
                    <div className="flex items-center text-yellow-500">
                      {[...Array(5)].map((_, i) => (
                        <Star
                          key={i}
                          className={`w-4 h-4 ${
                            i < (selectedReport.rating || 0)
                              ? "fill-current"
                              : "text-gray-300"
                          }`}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* 主要內容區域 - 左右分欄 */}
        <div className="flex-1 flex gap-6 min-h-0">
          {/* 左側 - 日報內容 */}
          <div className="flex-1 bg-white rounded-lg shadow-sm border border-gray-200 p-6 overflow-y-auto">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">我的日報內容</h3>
            <div className="space-y-4">
              {(selectedReport.consolidated_content || []).map(
                (projectReport, index) => (
                  <div
                    key={index}
                    className="border border-gray-100 rounded-lg p-4"
                  >
                    <div
                      className={`inline-flex items-center px-3 py-1 text-sm font-medium rounded-md mb-3 ${
                        getProjectColors(projectReport.project.name).tag
                      }`}
                    >
                      {projectReport.project.name}
                    </div>
                    <p className="text-gray-700 whitespace-pre-wrap">
                      {projectReport.content}
                    </p>
                    <AttachedFilesDisplay files={projectReport.files} />
                  </div>
                )
              )}
            </div>
          </div>

          {/* 右側 - 對話區域 */}
          <div className="w-96">
            <ChatInterface reportId={selectedReport.id} className="h-full" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* 標題和日期選擇器 */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">我的日報</h2>
        <div className="flex items-center space-x-2 bg-white border border-gray-200 rounded-lg p-1">
          <button 
            onClick={() => changeDate(-1)} 
            className="p-2 rounded hover:bg-gray-100"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <DatePicker
            selected={selectedDate}
            onChange={handleDateChange}
            dateFormat="yyyy / MM / dd"
            className="text-center font-semibold text-gray-700 w-32 bg-transparent focus:outline-none"
            customInput={
              <button className="flex items-center space-x-2 p-2 hover:bg-gray-100 rounded">
                <Calendar className="w-5 h-5 text-gray-500"/>
                <span>
                  {selectedDate ? 
                    selectedDate.toLocaleDateString('zh-TW', { 
                      year: 'numeric', 
                      month: '2-digit', 
                      day: '2-digit' 
                    }) : 
                    '選擇日期'
                  }
                </span>
              </button>
            }
          />
          <button 
            onClick={() => changeDate(1)} 
            className="p-2 rounded hover:bg-gray-100"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* 日報列表 */}
      {isLoading ? (
        <div className="p-6 text-center">載入日報中...</div>
      ) : reports.length === 0 ? (
        <div className="text-center py-16 text-gray-500 bg-white border border-gray-200 rounded-lg">
          <Calendar className="w-12 h-12 mx-auto mb-4 text-gray-300" />
          <p>這天沒有提交日報</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {reports.map((report) => (
            <div 
              key={report.id}
              className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => setSelectedReport(report)}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {formatDate(report.date)} 的日報
                  </h3>
                  {getStatusBadge(report.status)}
                </div>
                
                <div className="flex items-center space-x-4">
                  {report.rating && (
                    <div className="flex items-center space-x-1">
                      <span className="text-sm text-gray-600">評分:</span>
                      <div className="flex items-center text-yellow-500">
                        {[...Array(5)].map((_, i) => (
                          <Star
                            key={i}
                            className={`w-4 h-4 ${
                              i < (report.rating || 0)
                                ? "fill-current"
                                : "text-gray-300"
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
                    查看詳情 →
                  </button>
                </div>
              </div>

              {/* 預覽專案內容 */}
              <div className="space-y-2">
                {(report.consolidated_content || []).slice(0, 2).map((projectReport, index) => (
                  <div key={index} className="border-l-4 border-gray-200 pl-4">
                    <div
                      className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded mb-1 ${
                        getProjectColors(projectReport.project.name).tag
                      }`}
                    >
                      {projectReport.project.name}
                    </div>
                    <p className="text-sm text-gray-600 line-clamp-2">
                      {projectReport.content.length > 100 
                        ? projectReport.content.substring(0, 100) + '...'
                        : projectReport.content
                      }
                    </p>
                  </div>
                ))}
                {(report.consolidated_content || []).length > 2 && (
                  <p className="text-xs text-gray-500 mt-2">
                    還有 {(report.consolidated_content || []).length - 2} 個專案...
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MyReportsTab;