// frontend/src/contexts/WorkDataContext.tsx

import React, { createContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { LegacyApi } from '../services/legacyApi';
import { toast } from 'react-hot-toast';

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
  const [workData, setWorkData] = useState<WorkData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { user, authFetch } = useAuth();

  const fetchWorkData = useCallback(async () => {
    console.log('[WorkDataContext] fetchWorkData called, user empno:', user?.employee?.empno);
    if (!user?.employee?.empno) {
      console.log('[WorkDataContext] No empno, skipping fetch');
      return;
    }

    setIsLoading(true);
    try {
      console.log('[WorkDataContext] Calling LegacyApi.getAllWorkData...');
      const data = await LegacyApi.getAllWorkData(user.employee.empno, authFetch);
      console.log('[WorkDataContext] Received data:', data);
      setWorkData({
        work_plans: data.work_plans || [],
        basic_execution_works: data.basic_execution_works || [],
        project_execution_works: data.project_execution_works || {},
        service_companies: data.service_companies || [],
        service_targets: data.service_targets || []
      });
      console.log('✅ WorkDataContext: 載入工作資料成功');
    } catch (error) {
      console.error('WorkDataContext: 無法獲取工作資料:', error);
      toast.error('載入工作資料失敗');
      setWorkData(null);
    } finally {
      setIsLoading(false);
    }
  }, [user?.employee?.empno, authFetch]);

  useEffect(() => {
    if (user?.employee?.empno) {
      fetchWorkData();
    }
  }, [user?.employee?.empno, fetchWorkData]);

  const refetch = useCallback(async () => {
    await fetchWorkData();
  }, [fetchWorkData]);

  return (
    <WorkDataContext.Provider value={{ workData, isLoading, refetch }}>
      {children}
    </WorkDataContext.Provider>
  );
};
