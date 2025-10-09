// frontend/src/services/types/draft.ts
/**
 * 草稿相關型別定義
 */

export interface DraftSaveRequest {
  daily_no: string;
  empno: string;
  cocode: string;
  doc_date: string; // YYYYMMDD
  draft_type?: 'TEMP' | 'AI';
  draft_content: Record<string, any>; // JSON 格式的暫存內容
}

export interface DraftResponse {
  draft_id: string;
  daily_no: string;
  message: string;
}

export interface DraftUpdateRequest {
  [key: string]: any;
}

export interface AIDraftSaveRequest {
  ai_draft_id: string;
  empno: string;
  planno?: string;
  sopno?: string;
  original_content: string;
  ai_content: string;
  ai_model?: string;
  prompt_used?: string;
}

export interface AIDraftResponse {
  ai_draft_id: string;
  message: string;
}

export interface Draft {
  draft_id: string;
  daily_no: string;
  empno: string;
  cocode: string;
  doc_date: string;
  draft_type: 'TEMP' | 'AI';
  draft_content: Record<string, any>;
  created_date?: string;
  created_time?: string;
  status?: string;
}
