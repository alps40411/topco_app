// frontend/src/services/types/workData.ts
/**
 * 工作資料相關型別定義
 */

export interface WorkPlan {
  empno: string;
  planno: string;
  plan_subj_c?: string;
  no?: string;
  sopno: string;
  sop_desc_c?: string;
  seq?: number;
  name?: string;
}

export interface WorkItem {
  seq: string;
  name: string;
  unique_id?: string;
}

export interface ExecutionWork {
  sopno: string;
  sop_desc_c: string;
  work_items?: WorkItem[];
}

export interface ServiceCompany {
  id: string;
  cocode: string;
  coabbv: string;
}

export interface ServiceTarget {
  cocode: string;
  coabbv: string;
  deptno: string;
  deptabbv: string;
  empno: string;
  empnamec: string;
}

export interface WorkDataResponse {
  success: boolean;
  data: {
    projects?: WorkPlan[];
    execution_works?: ExecutionWork[];
    service_companies?: ServiceCompany[];
    service_targets?: ServiceTarget[];
    work_plans?: WorkPlan[];
    basic_execution_works?: ExecutionWork[];
    project_execution_works?: { [key: string]: ExecutionWork[] };
  };
}
