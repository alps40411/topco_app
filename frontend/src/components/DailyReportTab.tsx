// frontend/src/components/DailyReportTab.tsx

import React, { useState, useEffect } from 'react';
import { Upload, Edit, Save, Wand2, Plus, X } from 'lucide-react';
import type { ConsolidatedReport, FileAttachment, FileForUpload, Project, WorkRecordCreate } from '../App';
import { getProjectColors, blueButtonStyle, greenButtonStyle } from '../utils/colorUtils';
import { useAuth } from '../contexts/AuthContext';
import AttachedFilesManager from './AttachedFilesManager';
import AttachedFilesDisplay from './AttachedFilesDisplay';
import { toast } from 'react-hot-toast';

const DailyReportTab: React.FC = () => {
  const [reports, setReports] = useState<ConsolidatedReport[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingProjectId, setEditingProjectId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState<string>('');
  const [editFiles, setEditFiles] = useState<FileForUpload[]>([]);
  const { authFetch } = useAuth();
  
  const [isAiViewActive, setIsAiViewActive] = useState(false);
  const [isGeneratingAllAi, setIsGeneratingAllAi] = useState(false);
  const [generatingAiFor, setGeneratingAiFor] = useState<number | null>(null);

  // --- Modal and New Record State ---
  const [isAddNoteModalOpen, setIsAddNoteModalOpen] = useState(false);
  const [newRecord, setNewRecord] = useState<Partial<WorkRecordCreate>>({ content: '', project_id: undefined, files: [] });
  const [isSavingNewRecord, setIsSavingNewRecord] = useState(false);
  const [isUploadingNewFile, setIsUploadingNewFile] = useState(false);

  const fetchReports = async () => {
    setIsLoading(true);
    try {
      const response = await authFetch('/api/records/consolidated/today');
      if (response.ok) {
        const data: ConsolidatedReport[] = await response.json();
        setReports(data);
        if (data.some(report => report.ai_content)) {
          setIsAiViewActive(true);
        }
      }
    } catch (error) {
      console.error("無法取得彙整報告:", error);
      toast.error("無法取得彙整報告");
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
      toast.error("無法獲取專案列表");
    } 
  };

  useEffect(() => {
    fetchReports();
    fetchProjects();
  }, []);

  const handleEnhanceOne = async (projectId: number) => {
    setGeneratingAiFor(projectId);
    try {
      const response = await authFetch(`/api/records/ai/enhance_one/${projectId}`, { method: 'POST' });
      if (response.ok) {
        const enhancedReport = await response.json();
        setReports(prev => prev.map(r => r.project.id === projectId ? enhancedReport : r));
        if (!isAiViewActive) setIsAiViewActive(true);
        toast.success(`專案 ${enhancedReport.project.name} 已完成 AI 潤飾！`);
      } else {
        const err = await response.json().catch(() => ({ detail: 'AI 潤飾此專案時發生錯誤' }));
        throw new Error(err.detail);
      }
    } catch (error: any) {
      console.error(error);
      toast.error(error.message);
    } finally {
      setGeneratingAiFor(null);
    }
  };

  const handleEnhanceAll = async () => {
    setIsGeneratingAllAi(true);
    try {
      const response = await authFetch('/api/records/ai/enhance_all', { method: 'POST' });
      if (response.ok) {
        const enhancedReports = await response.json();
        setReports(enhancedReports);
        setIsAiViewActive(true);
        toast.success('所有報告皆已完成 AI 潤飾！');
      } else {
        throw new Error('AI 服務失敗');
      }
    } catch (error: any) {
      console.error(error);
      toast.error(error.message);
    } finally {
      setIsGeneratingAllAi(false);
    }
  };
  
  const startEdit = (report: ConsolidatedReport) => {
    setEditingProjectId(report.project.id);
    setEditContent(report.content);
    setEditFiles(report.files.map(f => ({ ...f, id: f.id || f.url, is_selected_for_ai: !!f.is_selected_for_ai })));
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
      
      const response = await authFetch(`/api/records/consolidated/${editingProjectId}`, {
        method: 'PUT',
        body: JSON.stringify({ ...reportToUpdate, content: editContent, files: editFiles }),
      });

      if (!response.ok) throw new Error('更新報告失敗');
      
      setReports(prevReports => prevReports.map(r =>
        r.project.id === editingProjectId
          ? { ...r, content: editContent, files: editFiles }
          : r
      ));
      toast.success('報告草稿更新成功！');
      cancelEdit();
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
    if (!window.confirm("確定要提交此版本作為今日的最終日報嗎？")) return;
    
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
      await fetchReports();
    } catch (error: any) {
      console.error(error);
      toast.error(`提交日報時發生錯誤: ${error.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditFileUpload = async (filesToUpload: FileList) => {
    if (!filesToUpload || filesToUpload.length === 0) return;
    // isUploading state is managed by the manager now, so we don't set it here.
    const uploadPromises = Array.from(filesToUpload).map(async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      try {
        const response = await authFetch('/api/records/upload', { method: 'POST', body: formData });
        if (!response.ok) throw new Error(`檔案 ${file.name} 上傳失敗`);
        const uploadedFile: FileAttachment = await response.json();
        const newFile: FileForUpload = { name: uploadedFile.name, type: uploadedFile.type, size: uploadedFile.size, url: uploadedFile.url, is_selected_for_ai: false };
        setEditFiles(prev => [...prev, newFile]);
      } catch (error: any) { console.error(error); toast.error(error.message); }
    });
    await Promise.all(uploadPromises);
  };

  const handleEditAiSelectionChange = (fileUrl: string, isSelected: boolean) => {
    setEditFiles(prev => prev.map(f => f.url === fileUrl ? { ...f, is_selected_for_ai: isSelected } : f));
  };
  const removeEditFile = (fileUrl: string) => {
    setEditFiles(prev => prev.filter(file => file.url !== fileUrl));
  };

  const handleNewRecordUpload = async (filesToUpload: FileList) => {
    if (!filesToUpload || filesToUpload.length === 0) return;
    setIsUploadingNewFile(true);
    const uploadPromises = Array.from(filesToUpload).map(async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      try {
        const response = await authFetch('/api/records/upload', { method: 'POST', body: formData });
        if (!response.ok) throw new Error(`檔案 ${file.name} 上傳失敗`);
        const uploadedFile: FileAttachment = await response.json();
        const newFile: FileForUpload = { name: uploadedFile.name, type: uploadedFile.type, size: uploadedFile.size, url: uploadedFile.url, is_selected_for_ai: false };
        setNewRecord(prev => ({ ...prev, files: [...(prev.files || []), newFile] }));
      } catch (error: any) { console.error(error); toast.error(error.message); }
    });
    await Promise.all(uploadPromises);
    setIsUploadingNewFile(false);
  };

  const handleNewRecordAiSelectionChange = (fileUrl: string, isSelected: boolean) => {
    setNewRecord(prev => ({ ...prev, files: (prev.files || []).map(f => f.url === fileUrl ? { ...f, is_selected_for_ai: isSelected } : f) }));
  };
  const removeNewRecordFile = (fileUrl: string) => {
    setNewRecord(prev => ({ ...prev, files: (prev.files || []).filter(file => file.url !== fileUrl) }));
  };

  const handleSaveNewRecord = async () => {
    if (!newRecord.project_id) {
      toast.error('請選擇工作計劃');
      return;
    }
    if (!newRecord.content?.trim() && (!newRecord.files || newRecord.files.length === 0)) {
      toast.error('請填寫內容或附加檔案');
      return;
    }
    setIsSavingNewRecord(true);
    try {
      const response = await authFetch('/api/records/', {
        method: 'POST',
        body: JSON.stringify({ project_id: newRecord.project_id, content: newRecord.content, files: newRecord.files || [] }),
      });
      if (!response.ok) throw new Error('儲存新筆記失敗');
      toast.success('新筆記儲存成功！');
      setNewRecord({ content: '', project_id: undefined, files: [] });
      setIsAddNoteModalOpen(false);
      await fetchReports();
    } catch (error: any) {
      console.error("儲存新筆記時發生錯誤:", error);
      toast.error(error.message);
    } finally {
      setIsSavingNewRecord(false);
    }
  };

  if (isLoading) { return <div className="p-6 text-center">載入中...</div>; }

  return (
    <>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">日報編輯</h2>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setIsAddNoteModalOpen(true)}
              disabled={editingProjectId !== null || generatingAiFor !== null}
              className={`inline-flex items-center px-4 py-2 text-sm rounded-lg ${blueButtonStyle} disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed`}
            >
              <Plus className="w-4 h-4 mr-2" />
              新增筆記
            </button>
            <button
              onClick={handleEnhanceAll}
              disabled={isGeneratingAllAi || reports.length === 0 || editingProjectId !== null || generatingAiFor !== null}
              className={`inline-flex items-center px-4 py-2 text-sm rounded-lg disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed ${greenButtonStyle}`}
            >
              <Wand2 className="w-4 h-4 mr-2" />
              {isGeneratingAllAi ? 'AI 處理中...' : 'AI 潤飾全部'}
            </button>
            <button 
              onClick={handleSubmitReport} 
              disabled={isSubmitting || editingProjectId !== null}
              className={`inline-flex items-center px-4 py-2 text-sm rounded-lg ${blueButtonStyle} disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed`}
            >
              <Upload className="w-4 h-4 mr-2" /> 
              {isSubmitting ? '提交中...' : '上傳最終版'}
            </button>
          </div>
        </div>
        
        <div className="space-y-8 mt-6">
          {reports.map((report) => (
            <div key={report.project.id} className={`grid grid-cols-1 ${isAiViewActive ? 'lg:grid-cols-2' : ''} gap-6 items-start bg-gray-50 p-4 rounded-xl border`}>
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 w-full flex flex-col h-full">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <div className={`inline-flex items-center px-3 py-1 text-sm font-medium rounded-md ${getProjectColors(report.project.name).tag}`}>
                      {report.project.name}
                    </div>
                    <span className="text-sm text-gray-500">({report.record_count} 筆記錄)</span>
                  </div>
                  {editingProjectId !== report.project.id && (
                    <div className="flex items-center space-x-2">
                      <button onClick={() => handleEnhanceOne(report.project.id)} disabled={generatingAiFor !== null || isGeneratingAllAi || editingProjectId !== null} className={`inline-flex items-center p-2 text-sm font-medium rounded-lg ${greenButtonStyle} disabled:bg-gray-300 disabled:cursor-not-allowed`}>
                        {generatingAiFor === report.project.id ? <div className="w-4 h-4 border-2 border-transparent border-t-white rounded-full animate-spin"></div> : <Wand2 className="w-4 h-4" />}
                      </button>
                      <button onClick={() => startEdit(report)} disabled={generatingAiFor !== null || isGeneratingAllAi} className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-lg ${getProjectColors(report.project.name).button} disabled:bg-gray-300 disabled:cursor-not-allowed`}>
                        <Edit className="w-4 h-4 mr-1" /> 編輯
                      </button>
                    </div>
                  )}
                </div>
                
                <div className="flex-grow">
                  {editingProjectId === report.project.id ? (
                    <div className="space-y-4">
                      <textarea value={editContent} onChange={(e) => setEditContent(e.target.value)} className="w-full min-h-[200px] p-4 border rounded-lg" />
                      <AttachedFilesManager 
                        files={editFiles}
                        onFileUpload={handleEditFileUpload}
                        onRemoveFile={removeEditFile}
                        onAiSelectionChange={handleEditAiSelectionChange}
                        isUploading={false} // This is now handled inside the manager
                      />
                      <div className="flex space-x-3">
                        <button onClick={saveEdit} disabled={isSaving} className={`inline-flex items-center px-4 py-2 text-sm rounded-lg ${blueButtonStyle} disabled:bg-gray-200`}>
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
              </div>

              {isAiViewActive && (
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 w-full h-full">
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="flex items-center px-2 py-1 bg-green-100 text-green-800 text-sm font-medium rounded-md">
                      <Wand2 className="w-4 h-4 mr-1.5" /> AI 參考資料
                    </div>
                  </div>
                  {generatingAiFor === report.project.id ? (
                     <p className="text-sm text-gray-500 italic">AI 正在為此專案生成潤飾內容...</p>
                  ) : report.ai_content ? (
                    <div className="prose max-w-none text-gray-700 whitespace-pre-wrap">
                      <div dangerouslySetInnerHTML={{ __html: report.ai_content.replace(/\n/g, '<br />') }} />
                    </div>
                  ) : (
                    <p className="text-sm text-gray-400 italic">此專案無 AI 潤飾內容。點擊魔法棒按鈕開始生成。</p>
                  )}
                </div>
              )}
            </div>
          ))}
          
          {reports.length === 0 && !isLoading && (
            <div className="text-center py-12 text-gray-500">
              <p>今天還沒有記錄，點擊右上角「新增筆記」來開始。</p>
            </div>
          )}
        </div>
      </div>

      {/* --- Add New Note Modal --- */}
      {isAddNoteModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 transition-opacity duration-300 ease-in-out animate-fade-in">
          <div className="bg-white rounded-lg shadow-xl p-8 w-full max-w-2xl m-4 transform transition-all duration-300 ease-in-out scale-95 animate-fade-in-scale">
            <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-semibold text-gray-900">新增筆記到今日報告</h3>
                <button onClick={() => setIsAddNoteModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                    <X className="w-6 h-6" />
                </button>
            </div>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">工作計劃</label>
                <select 
                  value={newRecord.project_id || ''} 
                  onChange={(e) => setNewRecord({ ...newRecord, project_id: parseInt(e.target.value, 10) || undefined })} 
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">請選擇工作計劃</option>
                  {projects.map((proj) => (<option key={proj.id} value={proj.id}>{proj.name}</option>))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">內容</label>
                <textarea 
                  rows={5} 
                  placeholder="記錄您的想法..." 
                  value={newRecord.content || ''} 
                  onChange={(e) => setNewRecord({ ...newRecord, content: e.target.value })} 
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" 
                />
              </div>
              
              <AttachedFilesManager 
                files={newRecord.files || []}
                onFileUpload={handleNewRecordUpload}
                onRemoveFile={removeNewRecordFile}
                onAiSelectionChange={handleNewRecordAiSelectionChange}
                isUploading={isUploadingNewFile}
              />

              <div className="flex justify-end space-x-4">
                <button
                  onClick={() => setIsAddNoteModalOpen(false)}
                  className="px-4 py-2 bg-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-300"
                >
                  取消
                </button>
                <button
                  onClick={handleSaveNewRecord}
                  disabled={isUploadingNewFile || isSavingNewRecord}
                  className={`w-32 py-2 px-4 rounded-lg flex items-center justify-center ${blueButtonStyle} disabled:bg-gray-200 disabled:text-gray-400`}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  {isSavingNewRecord ? '儲存中...' : '新增筆記'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      <style>{`
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes fade-in-scale {
          from { opacity: 0; transform: scale(0.95); }
          to { opacity: 1; transform: scale(1); }
        }
        .animate-fade-in {
          animation: fade-in 0.2s ease-in-out forwards;
        }
        .animate-fade-in-scale {
          animation: fade-in-scale 0.2s ease-in-out forwards;
        }
      `}</style>
    </>
  );
};

export default DailyReportTab;