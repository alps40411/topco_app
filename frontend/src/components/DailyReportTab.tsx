// frontend/src/components/DailyReportTab.tsx

import React, { useState, useEffect, useRef } from 'react';
import { Upload, Edit, Save, Plus, X, Image, File, BrainCircuit } from 'lucide-react';
import type { ConsolidatedReport, FileAttachment, FileForUpload } from '../App';
import { getProjectColors, blueButtonStyle } from '../utils/colorUtils';
import { useAuth } from '../contexts/AuthContext';
import AttachedFilesManager from './AttachedFilesManager';
import AttachedFilesDisplay from './AttachedFilesDisplay';
import { toast } from 'react-hot-toast';

const DailyReportTab: React.FC = () => {
  const [reports, setReports] = useState<ConsolidatedReport[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false); // 新增儲存狀態
  const [editingProjectId, setEditingProjectId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState<string>('');
  const [editFiles, setEditFiles] = useState<FileForUpload[]>([]);
  const { authFetch } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchReports = async () => {
    setIsLoading(true);
    try {
      const response = await authFetch('/api/records/consolidated/today');
      if (response.ok) setReports(await response.json());
    } catch (error) { console.error("無法取得彙整報告:", error); } 
    finally { setIsLoading(false); }
  };

  useEffect(() => { fetchReports(); }, []);

  const startEdit = (report: ConsolidatedReport) => {
    setEditingProjectId(report.project.id);
    setEditContent(report.content);
    setEditFiles(report.files.map(f => ({ 
      name: f.name, 
      type: f.type, 
      size: f.size, 
      url: f.url, 
      is_selected_for_ai: !!f.is_selected_for_ai 
    })));
  };

  const cancelEdit = () => {
    setEditingProjectId(null);
    setEditContent('');
    setEditFiles([]);
  };

  const saveEdit = async () => {
    if (editingProjectId === null) return;
    setIsSaving(true);
    try {
      const reportToUpdate = reports.find(r => r.project.id === editingProjectId);
      if (!reportToUpdate) throw new Error("找不到原始報告");
      
      console.log('DEBUG: 即將發送的數據:', {
        content: editContent.substring(0, 100) + '...',
        files: editFiles.map(f => ({ name: f.name, url: f.url, is_selected_for_ai: f.is_selected_for_ai }))
      });
      
      const response = await authFetch(`/api/records/consolidated/${editingProjectId}`, {
        method: 'PUT',
        body: JSON.stringify({
          content: editContent,
          files: editFiles.map(f => ({
            name: f.name,
            type: f.type,
            size: f.size,
            url: f.url,
            is_selected_for_ai: f.is_selected_for_ai || false
          }))
        }),
      });
      if (!response.ok) throw new Error('更新報告失敗');
      toast.success('報告草稿更新成功！');
      cancelEdit();
      await fetchReports();
    } catch (error) { 
      console.error(error); 
      toast.error('更新失敗，請稍後再試。');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSubmitReport = async () => {
    if (reports.length === 0) {
      toast.error("沒有可提交的報告內容。");
      return;
    }
    if (!window.confirm("確定要提交此版本作為今日的最終日報嗎？")) {
      return;
    }
    setIsSubmitting(true);
    try {
      const response = await authFetch('/api/supervisor/reports/submit', {
        method: 'POST',
        body: JSON.stringify(reports),
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: '提交失敗' }));
        throw new Error(errData.detail);
      }
      toast.success('日報已成功提交，等待主管審核！');
    } catch (error) {
      console.error(error);
      toast.error(`提交日報時發生錯誤: ${error}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    setIsUploading(true);
    const uploadPromises = Array.from(files).map(async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      try {
        const response = await authFetch('/api/records/upload', { method: 'POST', body: formData });
        if (!response.ok) throw new Error(`檔案 ${file.name} 上傳失敗`);
        const uploadedFile: FileAttachment = await response.json();
        const newFile: FileForUpload = { name: uploadedFile.name, type: uploadedFile.type, size: uploadedFile.size, url: uploadedFile.url, is_selected_for_ai: false };
        setEditFiles(prev => [...prev, newFile]);
      } catch (error) { console.error(error); alert(`檔案 ${file.name} 上傳失敗`); }
    });
    await Promise.all(uploadPromises);
    setIsUploading(false);
  };

  const handleAiSelectionChange = (fileUrl: string, isSelected: boolean) => {
    setEditFiles(prev => prev.map(f => f.url === fileUrl ? { ...f, is_selected_for_ai: isSelected } : f));
  };

  const removeFile = (fileUrl: string) => {
    setEditFiles(prev => prev.filter(file => file.url !== fileUrl));
  };

  if (isLoading) { return <div className="p-6 text-center">載入中...</div>; }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">日報編輯</h2>
        <button 
          onClick={handleSubmitReport} 
          disabled={isSubmitting}
          className={`inline-flex items-center px-4 py-2 text-sm rounded-lg ${blueButtonStyle} disabled:opacity-50`}
        >
          <Upload className="w-4 h-4 mr-2" /> 
          {isSubmitting ? '提交中...' : '上傳'}
        </button>
      </div>
      <div className="space-y-6">
        {reports.map((report) => (
          <div key={report.project.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                <div className={`inline-flex items-center px-3 py-1 text-sm font-medium rounded-md ${getProjectColors(report.project.name).tag}`}>
                  {report.project.name}
                </div>
                <span className="text-sm text-gray-500">({report.record_count} 筆記錄)</span>
              </div>
              {editingProjectId !== report.project.id && (
                <button onClick={() => startEdit(report)} className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-lg ${getProjectColors(report.project.name).button}`}>
                  <Edit className="w-4 h-4 mr-1" /> 編輯
                </button>
              )}
            </div>
            {editingProjectId === report.project.id ? (
                <div className="space-y-4">
                  <textarea value={editContent} onChange={(e) => setEditContent(e.target.value)} className="w-full min-h-[200px] p-4 border rounded-lg" />
                  <AttachedFilesManager 
                    files={editFiles}
                    onFileUpload={handleFileUpload}
                    onRemoveFile={removeFile}
                    onAiSelectionChange={handleAiSelectionChange}
                    isUploading={isUploading}
                  />
                  <div className="flex space-x-3">
                    <button 
                      onClick={saveEdit} 
                      disabled={isSaving}
                      className={`inline-flex items-center px-4 py-2 text-sm rounded-lg ${blueButtonStyle} disabled:opacity-50`}
                    >
                      <Save className="w-4 h-4 mr-2" /> 
                      {isSaving ? '儲存中...' : '儲存草稿'}
                    </button>
                    <button onClick={cancelEdit} className="px-4 py-2 bg-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-300">取消</button>
                  </div>
                </div>
            ) : ( 
              <div>
                <p className="prose max-w-none text-gray-700 whitespace-pre-wrap">{report.content}</p>
                <AttachedFilesDisplay files={report.files} />
              </div>
            )}
          </div>
        ))}
        {reports.length === 0 && !isLoading && (
          <div className="text-center py-12 text-gray-500">
            <p>今天還沒有記錄，請先到資料輸入頁面新增筆記。</p>
          </div>
        )}
      </div>
    </div>
  );
};
export default DailyReportTab;