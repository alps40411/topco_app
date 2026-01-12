// frontend/src/services/draftsApi.ts
/**
 * 草稿管理 API
 * 職責：處理日報暫存和編輯
 */

import { apiClient, createAuthApiClient } from './apiClient';
import type {
  DraftSaveRequest,
  DraftResponse,
  DraftUpdateRequest,
  AIDraftSaveRequest,
  AIDraftResponse,
  Draft
} from './types';

export class DraftsApi {
  /**
   * 保存草稿
   */
  static async save(data: DraftSaveRequest, authFetch?: (url: string, options?: RequestInit) => Promise<Response>): Promise<DraftResponse> {
    const client = authFetch ? createAuthApiClient(authFetch) : apiClient;
    return client.post<DraftResponse>('/api/drafts', data);
  }

  /**
   * 取得員工的草稿列表
   */
  static async getByEmployee(
    empno: string,
    docDate: string,
    type?: 'TEMP' | 'AI',
    authFetch?: (url: string, options?: RequestInit) => Promise<Response>
  ): Promise<Draft[]> {
    const client = authFetch ? createAuthApiClient(authFetch) : apiClient;
    return client.get<Draft[]>(`/api/drafts/${empno}`, {
      doc_date: docDate,
      draft_type: type
    });
  }

  /**
   * 更新草稿（根據 daily_no、planno 和 sopno）
   */
  static async update(
    dailyNo: string,
    planno: string,
    sopno: string,
    data: DraftUpdateRequest,
    authFetch?: (url: string, options?: RequestInit) => Promise<Response>
  ): Promise<{ message: string; daily_no: string; planno: string; sopno: string }> {
    const client = authFetch ? createAuthApiClient(authFetch) : apiClient;
    return client.put(`/api/drafts/by-daily-planno-sopno/${dailyNo}/${planno}/${sopno}`, data);
  }

  /**
   * 刪除草稿
   */
  static async delete(
    draftId: string,
    authFetch?: (url: string, options?: RequestInit) => Promise<Response>
  ): Promise<{ message: string }> {
    const client = authFetch ? createAuthApiClient(authFetch) : apiClient;
    return client.delete(`/api/drafts/${draftId}`);
  }

  /**
   * 保存 AI 草稿
   */
  static async saveAIDraft(
    data: AIDraftSaveRequest,
    authFetch?: (url: string, options?: RequestInit) => Promise<Response>
  ): Promise<AIDraftResponse> {
    const client = authFetch ? createAuthApiClient(authFetch) : apiClient;
    return client.post<AIDraftResponse>('/api/drafts/ai', data);
  }

  /**
   * 取得 AI 草稿列表
   */
  static async getAIDrafts(
    empno: string,
    authFetch?: (url: string, options?: RequestInit) => Promise<Response>
  ): Promise<Draft[]> {
    const client = authFetch ? createAuthApiClient(authFetch) : apiClient;
    return client.get<Draft[]>(`/api/drafts/ai/${empno}`);
  }
}
