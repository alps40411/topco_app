// frontend/src/services/recordsApi.ts
/**
 * 記錄管理 API
 * 職責：日報填寫過程的所有操作
 */

import { apiClient, createAuthApiClient } from './apiClient';
import type {
  SubmitResponse,
  UploadFileResponse,
  DeleteFileResponse,
  ConsolidatedRecord
} from './types';

export class RecordsApi {
  /**
   * 取得合併的今日記錄
   */
  static async getConsolidatedToday(
    docDate?: string,
    authFetch?: (url: string, options?: RequestInit) => Promise<Response>
  ): Promise<ConsolidatedRecord[]> {
    const client = authFetch ? createAuthApiClient(authFetch) : apiClient;
    return client.get<ConsolidatedRecord[]>('/api/records/consolidated/today', docDate ? { doc_date: docDate } : undefined);
  }

  /**
   * 上傳檔案
   */
  static async uploadFile(
    file: File,
    docDate: string,
    authFetch?: (url: string, options?: RequestInit) => Promise<Response>
  ): Promise<UploadFileResponse> {
    const client = authFetch ? createAuthApiClient(authFetch) : apiClient;
    return client.uploadFile<UploadFileResponse>('/api/records/upload', file, { doc_date: docDate });
  }

  // ✅ REMOVED: deleteFile - CommonAPI 檔案不實體刪除

  /**
   * 提交日報
   */
  static async submit(
    docDate: string,
    authFetch?: (url: string, options?: RequestInit) => Promise<Response>
  ): Promise<SubmitResponse> {
    const client = authFetch ? createAuthApiClient(authFetch) : apiClient;
    return client.post<SubmitResponse>(`/api/records/submit?doc_date=${docDate}`);
  }
}
