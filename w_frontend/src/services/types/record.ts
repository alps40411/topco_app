// frontend/src/services/types/record.ts
/**
 * 記錄相關型別定義
 */

export interface ReportSubmitRequest {
  daily_no: string;
  empno: string;
  cocode: string;
  deptno: string;
  doc_date: string; // YYYYMMDD
  emergency?: string;
  classify?: string;
  score?: number;
  leader: string;
  g_deptno: string;
  empnamec: string;
  deptnamec: string;
  sop_desc_c: string;
  word_count: number;
  att_file1?: string;
  att_file2?: string;
  work_items: Record<string, any>[]; // 工作項目列表
}

export interface SubmitResponse {
  success: boolean;
  daily_no: string;
  status?: string;
  message: string;
  work_items_count?: number;
  upload_time?: string;
}

export interface UploadFileResponse {
  success: boolean;
  filename: string;
  filepath: string;
  message: string;
}

export interface DeleteFileResponse {
  success: boolean;
  message: string;
}

export interface ConsolidatedRecord {
  daily_no: string;
  content: string;
  planno?: string;
  plan_subj_c?: string;
  sopno?: string;
  sop_desc_c?: string;
  work_item_seq?: string;
  service_cocode?: string;
  service_empno?: string;
  service_empnamec?: string;
  service_target_cocode?: string;
  service_deptno?: string;
  execution_time_minutes?: number;
  files?: any[];
  ai_content?: string;
  status?: string;
}
