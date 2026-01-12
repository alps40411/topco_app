// frontend/src/contexts/WorkDataContext.tsx
// ✅ 週報系統：簡化為 Mock 數據，不再調用 API

import React, { createContext, useState, ReactNode } from 'react';

interface WorkPlan {
  planno: string;
  plan_subj_c: string;
}

interface WorkItem {
  seq: string;
  name: string;
  unique_id?: string;
}

interface ExecutionWork {
  sopno: string;
  sop_desc_c: string;
  work_items: WorkItem[];
}

interface ServiceCompany {
  id: string;
  cocode: string;
  coabbv: string;
}

interface ServiceTarget {
  cocode: string;
  coabbv: string;
  deptno: string;
  deptabbv: string;
  empno: string;
  empnamec: string;
}

interface WorkData {
  work_plans: WorkPlan[];
  basic_execution_works: ExecutionWork[];
  project_execution_works: { [key: string]: ExecutionWork[] };
  service_companies: ServiceCompany[];
  service_targets: ServiceTarget[];
}

interface WorkDataContextType {
  workData: WorkData | null;
  isLoading: boolean;
  refetch: () => Promise<void>;
}

export const WorkDataContext = createContext<WorkDataContextType | undefined>(undefined);

export const WorkDataProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // ✅ 週報系統：提供最簡單的 Mock 數據
  const mockWorkData: WorkData = {
    work_plans: [],
    basic_execution_works: [],
    project_execution_works: {},
    service_companies: [],
    service_targets: []
  };

  const [workData] = useState<WorkData | null>(mockWorkData);
  const [isLoading] = useState(false);

  const refetch = async () => {
    // ✅ 週報系統：不做任何事情
    console.log('🧪 測試模式：WorkDataContext 不刷新數據');
  };

  // ✅ 不再調用 API，直接提供 Mock 數據
  console.log('🧪 測試模式：WorkDataContext 使用 Mock 數據');

  return (
    <WorkDataContext.Provider value={{ workData, isLoading, refetch }}>
      {children}
    </WorkDataContext.Provider>
  );
};
