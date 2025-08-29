// frontend/src/components/CascadingWorkSelector.tsx

import React, { useState, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import type { Project, ExecutionWork, WorkItem } from '../App';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'react-hot-toast';

interface CascadingWorkSelectorProps {
  selectedProjectId?: number;
  selectedExecutionWorkId?: number;
  selectedWorkItemId?: number;
  onProjectChange: (projectId?: number) => void;
  onExecutionWorkChange: (executionWorkId?: number) => void;
  onWorkItemChange: (workItemId?: number) => void;
  required?: boolean;
  className?: string;
}

const CascadingWorkSelector: React.FC<CascadingWorkSelectorProps> = ({
  selectedProjectId,
  selectedExecutionWorkId,
  selectedWorkItemId,
  onProjectChange,
  onExecutionWorkChange,
  onWorkItemChange,
  required = false,
  className = ""
}) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [executionWorks, setExecutionWorks] = useState<ExecutionWork[]>([]);
  const [workItems, setWorkItems] = useState<WorkItem[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [isLoadingExecutionWorks, setIsLoadingExecutionWorks] = useState(false);
  const [isLoadingWorkItems, setIsLoadingWorkItems] = useState(false);

  const { authFetch } = useAuth();

  // 載入專案列表
  const fetchProjects = async () => {
    if (!authFetch) return;
    setIsLoadingProjects(true);
    try {
      const response = await authFetch('/api/projects/');
      if (response.ok) {
        const projectsData = await response.json();
        setProjects(projectsData);
      } else {
        // 使用假資料
        setProjects([
          { id: 1, planno: 'PRJ001', plan_subj_c: 'ERP系統升級專案', pm_empno: 'E001', is_active: true },
          { id: 2, planno: 'PRJ002', plan_subj_c: '客戶管理系統開發', pm_empno: 'E002', is_active: true },
          { id: 3, planno: 'PRJ003', plan_subj_c: '行動APP改版', pm_empno: 'E003', is_active: true },
          { id: 4, planno: 'PRJ004', plan_subj_c: '資安防護強化', pm_empno: 'E004', is_active: true },
          { id: 5, planno: 'PRJ005', plan_subj_c: '雲端遷移計畫', pm_empno: 'E005', is_active: true },
          { id: 6, planno: 'PRJ006', plan_subj_c: 'AI智慧客服', pm_empno: 'E006', is_active: true },
          { id: 7, planno: 'PRJ007', plan_subj_c: '數據分析平台', pm_empno: 'E007', is_active: true },
        ]);
      }
    } catch (error) {
      console.error('無法獲取專案列表:', error);
      // 使用假資料作為fallback
      setProjects([
        { id: 1, planno: 'PRJ001', plan_subj_c: 'ERP系統升級專案', pm_empno: 'E001', is_active: true },
        { id: 2, planno: 'PRJ002', plan_subj_c: '客戶管理系統開發', pm_empno: 'E002', is_active: true },
        { id: 3, planno: 'PRJ003', plan_subj_c: '行動APP改版', pm_empno: 'E003', is_active: true },
        { id: 4, planno: 'PRJ004', plan_subj_c: '資安防護強化', pm_empno: 'E004', is_active: true },
        { id: 5, planno: 'PRJ005', plan_subj_c: '雲端遷移計畫', pm_empno: 'E005', is_active: true },
        { id: 6, planno: 'PRJ006', plan_subj_c: 'AI智慧客服', pm_empno: 'E006', is_active: true },
        { id: 7, planno: 'PRJ007', plan_subj_c: '數據分析平台', pm_empno: 'E007', is_active: true },
      ]);
    } finally {
      setIsLoadingProjects(false);
    }
  };

  // 載入執行工作列表 - 直接使用假資料
  const fetchExecutionWorks = async (projectId: number) => {
    setIsLoadingExecutionWorks(true);
    // 模擬API請求延遲
    setTimeout(() => {
      setExecutionWorks([
        { id: 1, name: '系統開發', project_id: projectId, is_active: true },
        { id: 2, name: '系統維護', project_id: projectId, is_active: true },
        { id: 3, name: '需求分析', project_id: projectId, is_active: true },
        { id: 4, name: '測試執行', project_id: projectId, is_active: true },
        { id: 5, name: '文件撰寫', project_id: projectId, is_active: true },
        { id: 6, name: '專案管理', project_id: projectId, is_active: true },
      ]);
      setIsLoadingExecutionWorks(false);
    }, 200);
  };

  // 載入工作項目列表 - 直接使用假資料
  const fetchWorkItems = async (executionWorkId: number) => {
    setIsLoadingWorkItems(true);
    // 模擬API請求延遲
    setTimeout(() => {
      setWorkItems([
        { id: 1, name: '前端開發', execution_work_id: executionWorkId, is_active: true },
        { id: 2, name: '後端開發', execution_work_id: executionWorkId, is_active: true },
        { id: 3, name: '資料庫設計', execution_work_id: executionWorkId, is_active: true },
        { id: 4, name: 'API設計', execution_work_id: executionWorkId, is_active: true },
        { id: 5, name: 'UI/UX設計', execution_work_id: executionWorkId, is_active: true },
        { id: 6, name: '系統測試', execution_work_id: executionWorkId, is_active: true },
        { id: 7, name: '部署作業', execution_work_id: executionWorkId, is_active: true },
        { id: 8, name: '文件整理', execution_work_id: executionWorkId, is_active: true },
      ]);
      setIsLoadingWorkItems(false);
    }, 150);
  };

  useEffect(() => {
    fetchProjects();
  }, [authFetch]);

  useEffect(() => {
    if (selectedProjectId) {
      fetchExecutionWorks(selectedProjectId);
    } else {
      setExecutionWorks([]);
      setWorkItems([]);
    }
  }, [selectedProjectId]);

  useEffect(() => {
    if (selectedExecutionWorkId) {
      fetchWorkItems(selectedExecutionWorkId);
    } else {
      setWorkItems([]);
    }
  }, [selectedExecutionWorkId]);

  const handleProjectChange = (value: string) => {
    const projectId = value ? parseInt(value, 10) : undefined;
    onProjectChange(projectId);
    onExecutionWorkChange(undefined);
    onWorkItemChange(undefined);
    setExecutionWorks([]);
    setWorkItems([]);
  };

  const handleExecutionWorkChange = (value: string) => {
    const executionWorkId = value ? parseInt(value, 10) : undefined;
    onExecutionWorkChange(executionWorkId);
    onWorkItemChange(undefined);
    setWorkItems([]);
  };

  const handleWorkItemChange = (value: string) => {
    const workItemId = value ? parseInt(value, 10) : undefined;
    onWorkItemChange(workItemId);
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 工作計畫選擇 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          工作計畫 {required && <span className="text-red-500">*</span>}
        </label>
        <div className="relative">
          <select
            value={selectedProjectId || ""}
            onChange={(e) => handleProjectChange(e.target.value)}
            className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white"
            disabled={isLoadingProjects}
          >
            <option value="">請選擇工作計畫</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.plan_subj_c}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-2.5 h-4 w-4 text-gray-400 pointer-events-none" />
        </div>
      </div>

      {/* 執行工作選擇 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          執行工作 {required && <span className="text-red-500">*</span>}
        </label>
        <div className="relative">
          <select
            value={selectedExecutionWorkId || ""}
            onChange={(e) => handleExecutionWorkChange(e.target.value)}
            className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white disabled:bg-gray-50 disabled:text-gray-500"
            disabled={!selectedProjectId || isLoadingExecutionWorks}
          >
            <option value="">
              {!selectedProjectId ? '請先選擇工作計畫' : '請選擇執行工作'}
            </option>
            {executionWorks.map((work) => (
              <option key={work.id} value={work.id}>
                {work.name}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-2.5 h-4 w-4 text-gray-400 pointer-events-none" />
        </div>
        {isLoadingExecutionWorks && (
          <div className="text-xs text-gray-500 mt-1">載入執行工作中...</div>
        )}
      </div>

      {/* 工作項目選擇 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          工作項目 {required && <span className="text-red-500">*</span>}
        </label>
        <div className="relative">
          <select
            value={selectedWorkItemId || ""}
            onChange={(e) => handleWorkItemChange(e.target.value)}
            className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white disabled:bg-gray-50 disabled:text-gray-500"
            disabled={!selectedExecutionWorkId || isLoadingWorkItems}
          >
            <option value="">
              {!selectedExecutionWorkId ? '請先選擇執行工作' : '請選擇工作項目'}
            </option>
            {workItems.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-2.5 h-4 w-4 text-gray-400 pointer-events-none" />
        </div>
        {isLoadingWorkItems && (
          <div className="text-xs text-gray-500 mt-1">載入工作項目中...</div>
        )}
      </div>
    </div>
  );
};

export default CascadingWorkSelector;