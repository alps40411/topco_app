// frontend/src/components/DataInputTab.tsx

import React, { useRef, useState, useEffect } from 'react';
import { Save, Upload, Plus, X, FileText, Image, File, BrainCircuit } from 'lucide-react';
import type { WorkRecord, FileAttachment, WorkRecordCreate, Project, FileForUpload } from '../App';
import { getProjectColors, blueButtonStyle } from '../utils/colorUtils';
import { useAuth } from '../contexts/AuthContext';
import AttachedFilesDisplay from './AttachedFilesDisplay';
import AttachedFilesManager from './AttachedFilesManager';
import { toast } from 'react-hot-toast';

const DataInputTab: React.FC = () => {
  const [workRecords, setWorkRecords] = useState<WorkRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [currentRecord, setCurrentRecord] = useState<Partial<WorkRecordCreate>>({
    content: '',
    project_id: undefined,
    files: [],
  });
  const [projects, setProjects] = useState<Project[]>([]);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const { authFetch } = useAuth();
  const [isSaving, setIsSaving] = useState(false);
  const fetchTodayRecords = async () => {
    setIsLoading(true);
    try {
      const response = await authFetch('/api/records/today');
      if (response.ok) {
        setWorkRecords(await response.json());
      }
    } catch (error) {
      console.error("取得今日筆記失敗:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchProjects = async () => {
    try {
      const response = await authFetch('/api/projects/');
      if (response.ok) {
        setProjects(await response.json());
      }
    } catch (error) {
      console.error("無法獲取專案列表:", error);
    }
  };

  useEffect(() => {
    fetchTodayRecords();
    fetchProjects();
  }, []);

  const onSave = async () => {
    if (!currentRecord.project_id || !currentRecord.content) {
      toast.error('請選擇工作計劃並填寫內容');
      return;
    }
    setIsSaving(true);
    try {
      const response = await authFetch('/api/records/', {
        method: 'POST',
        body: JSON.stringify({
          project_id: currentRecord.project_id,
          content: currentRecord.content,
          files: currentRecord.files || [],
        }),
      });
      if (!response.ok) throw new Error('儲存筆記失敗');
      await fetchTodayRecords();
      setCurrentRecord({ content: '', project_id: undefined, files: [] });
      toast.success('記錄儲存成功！');
    } catch (error) {
      console.error("儲存筆記時發生錯誤:", error);
      toast.error('儲存失敗，請稍後再試。');
    } finally {
      setIsSaving(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    setIsUploading(true);
    const uploadedFiles: FileForUpload[] = [];
    const uploadPromises = Array.from(files).map(async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      try {
        const response = await authFetch('/api/records/upload', { method: 'POST', body: formData });
        if (!response.ok) throw new Error(`檔案 ${file.name} 上傳失敗`);
        const uploadedFile = await response.json();
        uploadedFiles.push({
          name: uploadedFile.name,
          type: uploadedFile.type,
          size: uploadedFile.size,
          url: uploadedFile.url,
          is_selected_for_ai: false, // 預設為 false
        });
      } catch (error) { console.error(error); alert(`檔案 ${file.name} 上傳失敗`); }
    });
    await Promise.all(uploadPromises);
    setCurrentRecord(prev => ({ ...prev, files: [...(prev.files || []), ...uploadedFiles] }));
    setIsUploading(false);
  };

  const handleAiSelectionChange = (fileUrl: string, isSelected: boolean) => {
    setCurrentRecord(prev => ({
      ...prev,
      files: (prev.files || []).map(f => f.url === fileUrl ? { ...f, is_selected_for_ai: isSelected } : f)
    }));
  };

  const removeFile = (fileUrl: string) => {
    setCurrentRecord(prev => ({ ...prev, files: (prev.files || []).filter(file => file.url !== fileUrl) }));
  };

  const formatTime = (timestamp: string) => new Date(timestamp).toLocaleString('zh-TW', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });

  return (
    <div className="flex gap-6 p-6">
      <div className="w-1/2">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">記錄新筆記</h2>
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">工作計劃</label>
              <select value={currentRecord.project_id || ''} onChange={(e) => setCurrentRecord({ ...currentRecord, project_id: parseInt(e.target.value, 10) || undefined })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                <option value="">請選擇工作計劃</option>
                {projects.map((proj) => (<option key={proj.id} value={proj.id}>{proj.name}</option>))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">內容</label>
              <textarea rows={4} placeholder="記錄您的想法..." value={currentRecord.content || ''} onChange={(e) => setCurrentRecord({ ...currentRecord, content: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
            </div>
            
            <AttachedFilesManager 
              files={currentRecord.files || []}
              onFileUpload={handleFileUpload}
              onRemoveFile={removeFile}
              onAiSelectionChange={handleAiSelectionChange}
              isUploading={isUploading}
            />

            <button
              onClick={onSave}
              disabled={isUploading || isSaving}
              className={`w-full py-3 px-4 rounded-lg flex items-center justify-center ${blueButtonStyle} disabled:bg-gray-200 disabled:text-gray-400`}
            >
              <Save className="w-4 h-4 mr-2" />
              {isUploading ? '檔案處理中...' : isSaving ? '儲存中...' : '儲存筆記'}
            </button>
          </div>
        </div>
      </div>
      <div className="w-1/2">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">今日筆記 ({workRecords.length})</h2>
          <div className="space-y-4 h-[600px] overflow-y-auto pr-2">
            {isLoading ? ( <div className="text-center py-8 text-gray-500">載入中...</div> ) 
            : workRecords.length === 0 ? ( <div className="text-center py-8 text-gray-500"><FileText className="w-12 h-12 mx-auto mb-2 opacity-50" /><p>今天還沒有記錄，開始您的工作吧！</p></div> ) 
            : (
              workRecords.map((record) => (
                <div key={record.id} className="bg-gray-50 rounded-lg p-4 border border-gray-100">
                  <div className="flex items-start justify-between mb-2">
                    <div className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-md ${getProjectColors(record.project.name).tag}`}>
                      {record.project.name}
                    </div>
                    <span className="text-xs text-gray-500">{formatTime(record.created_at)}</span>
                  </div>
                  <p className="text-sm text-gray-700 whitespace-pre-wrap">{record.content}</p>
                  <AttachedFilesDisplay files={record.files} />
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
export default DataInputTab;