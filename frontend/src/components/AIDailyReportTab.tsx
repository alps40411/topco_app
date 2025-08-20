// frontend/src/components/AIDailyReportTab.tsx

import React, { useState, useEffect, useCallback } from 'react';
import { Upload, Edit, Wand2, Save } from 'lucide-react';
import type { ConsolidatedReport } from '../App';
import { getProjectColors, blueButtonStyle, greenButtonStyle } from '../utils/colorUtils';
import { useAuth } from '../contexts/AuthContext'; // <-- 引入 useAuth
import { toast } from 'react-hot-toast';

const AIDailyReportTab: React.FC = () => {
  const [reports, setReports] = useState<ConsolidatedReport[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isBatchGenerating, setIsBatchGenerating] = useState(false);
  const [editingProjectId, setEditingProjectId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState('');
  const { authFetch } = useAuth(); // <-- 取得 authFetch 函式
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fetchReports = useCallback(async () => {
    console.log('📋 開始取得今日彙整報告');
    setIsLoading(true);
    try {
      const response = await authFetch('/api/records/consolidated/today');
      console.log('📥 fetchReports 回應:', {
        status: response.status,
        ok: response.ok
      });
      if (response.ok) {
        const reports = await response.json();
        console.log('✅ 成功取得報告:', reports);
        setReports(reports);
      } else {
        console.error('❌ fetchReports 失敗:', response.status);
      }
    } catch (error) { 
      console.error("❌ 無法取得彙整報告:", error); 
    } 
    finally { 
      setIsLoading(false); 
      console.log('🏁 fetchReports 完成');
    }
  }, []); // 移除authFetch依賴

  useEffect(() => { fetchReports(); }, [fetchReports]);

  const handleEnhanceAll = async () => {
    console.log('🚀 開始執行 AI 一鍵潤飾全部功能');
    setIsBatchGenerating(true);
    try {
      console.log('📤 發送 API 請求到 /api/records/ai/enhance_all');
      const response = await authFetch('/api/records/ai/enhance_all', { method: 'POST' });
      console.log('📥 收到 API 回應:', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log('✅ AI 潤飾成功，收到結果:', result);
        setReports(result);
        toast.success('AI 潤飾完成！');
      } else {
        const errorText = await response.text();
        console.error('❌ API 回應錯誤:', errorText);
        throw new Error(`AI 服務失敗: ${response.status} ${errorText}`);
      }
    } catch (error) {
      console.error('❌ handleEnhanceAll 錯誤:', error);
      toast.error(`AI 潤飾所有報告時發生錯誤: ${error}`);
    } finally {
      setIsBatchGenerating(false);
      console.log('🏁 handleEnhanceAll 執行完成');
    }
  };

  const startEdit = (report: ConsolidatedReport) => {
    setEditingProjectId(report.project.id);
    setEditContent(report.ai_content || report.content);
  };

  const cancelEdit = () => {
    setEditingProjectId(null);
    setEditContent('');
  };

  const saveEdit = async () => {
    if (editingProjectId === null) return;
    setIsSaving(true);
    try {
      const response = await authFetch(`/api/records/ai/${editingProjectId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: editContent, project_name: '' }),
      });
      if (!response.ok) throw new Error('儲存失敗');
      toast.success('AI 草稿儲存成功！');
      cancelEdit();
      await fetchReports();
    } catch (error) {
      console.error(error);
      toast.error('儲存 AI 草稿時發生錯誤');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSubmitReport = async () => {
    const reportsToSubmit = reports.map(r => ({
      ...r,
      content: r.ai_content || r.content, // 優先使用 AI 內容
    }));

    if (reportsToSubmit.length === 0) {
      alert("沒有可提交的報告內容。");
      return;
    }
    if (!window.confirm("將使用 AI 潤飾後的內容（若有）作為最終版本，確定要提交嗎？")) {
      return;
    }
    setIsSubmitting(true);
    try {
      const response = await authFetch('/api/supervisor/reports/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reportsToSubmit),
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || '提交失敗');
      }
      toast.success('AI 版日報已成功提交，等待主管審核！');
    } catch (error) {
      console.error(error);
      toast.error(`提交日報時發生錯誤: ${error}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) { return <div className="p-6 text-center">載入中...</div>; }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">AI日報編輯</h2>
        <div className="flex items-center space-x-3">
            <button
              onClick={handleEnhanceAll}
              disabled={isBatchGenerating || reports.length === 0}
              className={`inline-flex items-center px-4 py-2 text-sm rounded-lg disabled:bg-gray-200 disabled:text-gray-400 ${greenButtonStyle}`}
            >
              <Wand2 className="w-4 h-4 mr-2" />
              {isBatchGenerating ? 'AI 處理中...' : '一鍵潤飾全部'}
            </button>
            <button onClick={handleSubmitReport} disabled={isSubmitting} className={`inline-flex items-center px-4 py-2 text-sm rounded-lg ${blueButtonStyle} disabled:opacity-50`}>
              <Upload className="w-4 h-4 mr-2" /> {isSubmitting ? '提交中...' : '上傳 AI 版本'}
            </button>
        </div>
      </div>

      <div className="space-y-6">
        {reports.map((report) => (
          <div key={report.project.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                <div className={`inline-flex items-center px-3 py-1 text-sm font-medium rounded-md ${getProjectColors(report.project.plan_subj_c).tag}`}>
                  {report.project.plan_subj_c}
                </div>
                <span className="text-sm text-gray-500">({report.record_count} 筆記錄)</span>
                {report.ai_content && (
                  <div className="flex items-center px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded">
                    <Wand2 className="w-3 h-3 mr-1" /> AI 已潤飾
                  </div>
                )}
              </div>
              {editingProjectId !== report.project.id && (
                <button 
                  onClick={() => startEdit(report)}
                  className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-lg ${getProjectColors(report.project.plan_subj_c).button}`}
                >
                  <Edit className="w-4 h-4 mr-1" /> 編輯
                </button>
              )}
            </div>
            {editingProjectId === report.project.id ? (
                <div className="space-y-4">
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="w-full min-h-[250px] p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                  <div className="flex space-x-3">
                    <button onClick={saveEdit} disabled={isSaving} className={`inline-flex items-center px-4 py-2 text-sm rounded-lg ${blueButtonStyle} disabled:opacity-50`}>
                        <Save className="w-4 h-4 mr-2" /> {isSaving ? '儲存中...' : '儲存 AI 草稿'}
                    </button>
                    <button onClick={cancelEdit} className="px-4 py-2 bg-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-300">取消</button>
                  </div>
                </div>
            ) : (
              <div className="prose max-w-none text-gray-700 whitespace-pre-wrap">
                {/* 使用 dangerouslySetInnerHTML 來渲染 Markdown，但請注意 XSS 風險 */}
                <div dangerouslySetInnerHTML={{ __html: (report.ai_content || report.content).replace(/\n/g, '<br />') }} />
              </div>
            )}
          </div>
        ))}
        {reports.length === 0 && !isLoading && (
          <div className="text-center py-12 text-gray-500">
            <p>今天還沒有可供 AI 編輯的日報，請先到資料輸入頁面新增筆記。</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AIDailyReportTab;