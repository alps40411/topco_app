// frontend/src/components/ComprehensiveEditTab.tsx

import React, { useState, useEffect } from "react";
import { Upload, Edit, Wand2, Save } from "lucide-react";
import type { ConsolidatedReport } from "../App";
import { getProjectColors, blueButtonStyle } from "../utils/colorUtils";
import { useAuth } from "../contexts/AuthContext"; // <-- 引入 useAuth

const ComprehensiveEditTab: React.FC = () => {
  const [reports, setReports] = useState<ConsolidatedReport[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [editingSide, setEditingSide] = useState<"manual" | "ai" | null>(null);
  const [editingProjectId, setEditingProjectId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState("");
  const { authFetch } = useAuth(); // <-- 取得 authFetch 函式

  const fetchReports = async () => {
    setIsLoading(true);
    try {
      const response = await authFetch("/api/records/consolidated/today"); // <-- 使用 authFetch
      if (response.ok) setReports(await response.json());
    } catch (error) {
      console.error("無法取得彙整報告:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const startEdit = (report: ConsolidatedReport, side: "manual" | "ai") => {
    setEditingSide(side);
    setEditingProjectId(report.project.id);
    setEditContent(
      side === "ai" ? report.ai_content || report.content : report.content
    );
  };

  const cancelEdit = () => {
    setEditingSide(null);
    setEditingProjectId(null);
    setEditContent("");
  };

  const saveEdit = async () => {
    if (editingProjectId === null || editingSide === null) return;

    const url =
      editingSide === "ai"
        ? `/api/records/ai/${editingProjectId}`
        : `/api/records/consolidated/${editingProjectId}`;

    const body =
      editingSide === "ai"
        ? { content: editContent, project_name: "" } // project_name is a placeholder
        : { content: editContent, files: [] }; // files update can be added later

    try {
      const response = await authFetch(url, {
        method: "PUT",
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error("儲存失敗");

      alert(`儲存成功！`);
      cancelEdit();
      await fetchReports();
    } catch (error) {
      console.error("儲存時發生錯誤:", error);
      alert("儲存失敗");
    }
  };

  const handleSubmitManual = async () => {
    if (reports.length === 0) {
      alert("沒有可提交的報告內容。");
      return;
    }
    if (!window.confirm("確定要提交此版本作為今日的最終日報嗎？")) {
      return;
    }
    try {
      const response = await authFetch("/api/supervisor/reports/submit", {
        method: "POST",
        body: JSON.stringify(reports),
      });
      if (!response.ok) throw new Error("提交失敗");
      alert("日報已成功提交，等待主管審核！");
    } catch (error) {
      console.error(error);
      alert("提交日報時發生錯誤。");
    }
  };

  const handleSubmitAI = async () => {
    const reportsToSubmit = reports.map((r) => ({
      ...r,
      // 如果有 AI 內容，就用 AI 內容覆蓋原文
      content: r.ai_content || r.content,
    }));

    if (reportsToSubmit.length === 0) {
      alert("沒有可提交的報告內容。");
      return;
    }
    if (
      !window.confirm(
        "將使用 AI 潤飾後的內容（若有）作為最終版本，確定要提交嗎？"
      )
    ) {
      return;
    }
    try {
      const response = await authFetch("/api/supervisor/reports/submit", {
        method: "POST",
        body: JSON.stringify(reportsToSubmit),
      });
      if (!response.ok) throw new Error("提交失敗");
      alert("AI 版日報已成功提交，等待主管審核！");
    } catch (error) {
      console.error(error);
      alert("提交日報時發生錯誤。");
    }
  };

  if (isLoading) {
    return <div className="p-6 text-center">載入中...</div>;
  }

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">綜合編輯</h2>
      <div className="flex gap-6">
        {/* --- 左欄：日報編輯 --- */}
        <div className="w-1/2">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="flex items-center justify-between p-4 border-b border-gray-100">
              <h3 className="text-lg font-medium text-gray-900">日報編輯</h3>
              <button
                onClick={handleSubmitManual}
                className={`inline-flex items-center px-4 py-2 text-sm rounded-lg ${blueButtonStyle}`}
              >
                <Upload className="w-4 h-4 mr-2" /> 上傳手動版本
              </button>
            </div>
            <div className="p-4 space-y-4">
              {reports.map((report) => (
                <div
                  key={`manual-${report.project.id}`}
                  className="border border-gray-200 rounded-lg p-4"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div
                      className={`inline-flex items-center px-3 py-1 text-sm font-medium rounded-md ${
                        getProjectColors(report.project.name).tag
                      }`}
                    >
                      {report.project.name}
                    </div>
                    {editingProjectId !== report.project.id && (
                      <button
                        onClick={() => startEdit(report, "manual")}
                        className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-lg ${
                          getProjectColors(report.project.name).button
                        }`}
                      >
                        <Edit className="w-3 h-3 mr-1" /> 編輯
                      </button>
                    )}
                  </div>

                  {editingSide === "manual" &&
                  editingProjectId === report.project.id ? (
                    <div className="space-y-3">
                      <textarea
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        className="w-full min-h-[150px] p-3 border border-gray-300 rounded-lg"
                      />
                      <div className="flex space-x-2">
                        <button
                          onClick={saveEdit}
                          className={`inline-flex items-center px-4 py-2 text-sm rounded-lg ${blueButtonStyle}`}
                        >
                          <Save className="w-4 h-4 mr-2" /> 儲存
                        </button>
                        <button
                          onClick={cancelEdit}
                          className="px-3 py-1 bg-gray-200 text-gray-700 text-xs font-medium rounded hover:bg-gray-300"
                        >
                          取消
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">
                      {report.content}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* --- 右欄：AI 日報編輯 --- */}
        <div className="w-1/2">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="flex items-center justify-between p-4 border-b border-gray-100">
              <h3 className="text-lg font-medium text-gray-900">AI 日報編輯</h3>
              <button
                onClick={handleSubmitAI}
                className={`inline-flex items-center px-4 py-2 text-sm rounded-lg ${blueButtonStyle}`}
              >
                <Upload className="w-4 h-4 mr-2" /> 上傳 AI 版本
              </button>
            </div>
            <div className="p-4 space-y-4">
              {reports.map((report) => (
                <div
                  key={`ai-${report.project.id}`}
                  className="border border-gray-200 rounded-lg p-4"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div
                      className={`inline-flex items-center px-3 py-1 text-sm font-medium rounded-md ${
                        getProjectColors(report.project.name).tag
                      }`}
                    >
                      {report.project.name}
                    </div>
                    {report.ai_content &&
                      editingProjectId !== report.project.id && (
                        <button
                          onClick={() => startEdit(report, "ai")}
                          className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-lg ${
                            getProjectColors(report.project.name).button
                          }`}
                        >
                          <Edit className="w-3 h-3 mr-1" /> 編輯
                        </button>
                      )}
                  </div>

                  {editingSide === "ai" &&
                  editingProjectId === report.project.id ? (
                    <div className="space-y-3">
                      <textarea
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        className="w-full min-h-[150px] p-3 border border-gray-300 rounded-lg"
                      />
                      <div className="flex space-x-2">
                        <button
                          onClick={saveEdit}
                          className={`inline-flex items-center px-4 py-2 text-sm rounded-lg ${blueButtonStyle}`}
                        >
                          <Save className="w-4 h-4 mr-2" /> 儲存
                        </button>
                        <button
                          onClick={cancelEdit}
                          className="px-3 py-1 bg-gray-200 text-gray-700 text-xs font-medium rounded hover:bg-gray-300"
                        >
                          取消
                        </button>
                      </div>
                    </div>
                  ) : report.ai_content ? (
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">
                      {report.ai_content}
                    </p>
                  ) : (
                    <p className="text-sm text-gray-400 italic">
                      請至「AI 日報編輯」分頁生成內容
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ComprehensiveEditTab;
