// frontend/src/services/apiClient.ts
/**
 * 統一的 API 客戶端
 * 提供統一的錯誤處理、認證、請求攔截等功能
 */

import { buildApiUrl } from '../config/api';

export interface ApiResponse<T = any> {
  data?: T;
  success?: boolean;
  message?: string;
  detail?: string;
}

export interface ApiError {
  message: string;
  status?: number;
  detail?: string;
}

export class ApiClient {
  private authFetch?: (url: string, options?: RequestInit) => Promise<Response>;

  constructor(authFetch?: (url: string, options?: RequestInit) => Promise<Response>) {
    this.authFetch = authFetch;
  }

  /**
   * 設置認證 fetch 函數
   */
  setAuthFetch(authFetch: (url: string, options?: RequestInit) => Promise<Response>) {
    this.authFetch = authFetch;
  }

  /**
   * 處理 API 響應
   */
  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      const error: ApiError = {
        message: errorData?.detail || errorData?.message || `HTTP ${response.status}: ${response.statusText}`,
        status: response.status,
        detail: errorData?.detail
      };
      throw error;
    }

    const data = await response.json();
    return data as T;
  }

  /**
   * GET 請求
   */
  async get<T = any>(endpoint: string, params?: Record<string, any>): Promise<T> {
    // 如果使用 authFetch，它會自己處理 buildApiUrl
    const baseUrl = this.authFetch ? endpoint : buildApiUrl(endpoint);
    const url = new URL(baseUrl, window.location.origin);

    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          url.searchParams.append(key, String(params[key]));
        }
      });
    }

    const fetchFn = this.authFetch || fetch.bind(window);
    const response = await fetchFn(url.toString());
    return this.handleResponse<T>(response);
  }

  /**
   * POST 請求
   */
  async post<T = any>(endpoint: string, data?: any): Promise<T> {
    // 如果使用 authFetch，它會自己處理 buildApiUrl
    // 否則我們需要手動調用 buildApiUrl
    const url = this.authFetch ? endpoint : buildApiUrl(endpoint);
    const fetchFn = this.authFetch || fetch.bind(window);

    const response = await fetchFn(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: data ? JSON.stringify(data) : undefined
    });

    return this.handleResponse<T>(response);
  }

  /**
   * PUT 請求
   */
  async put<T = any>(endpoint: string, data?: any): Promise<T> {
    const url = this.authFetch ? endpoint : buildApiUrl(endpoint);
    const fetchFn = this.authFetch || fetch.bind(window);

    const response = await fetchFn(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: data ? JSON.stringify(data) : undefined
    });

    return this.handleResponse<T>(response);
  }

  /**
   * DELETE 請求
   */
  async delete<T = any>(endpoint: string): Promise<T> {
    const url = this.authFetch ? endpoint : buildApiUrl(endpoint);
    const fetchFn = this.authFetch || fetch.bind(window);

    const response = await fetchFn(url, {
      method: 'DELETE'
    });

    return this.handleResponse<T>(response);
  }

  /**
   * 上傳檔案
   */
  async uploadFile<T = any>(endpoint: string, file: File, params?: Record<string, any>): Promise<T> {
    const baseUrl = this.authFetch ? endpoint : buildApiUrl(endpoint);
    const url = new URL(baseUrl, window.location.origin);

    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          url.searchParams.append(key, String(params[key]));
        }
      });
    }

    const formData = new FormData();
    formData.append('file', file);

    const fetchFn = this.authFetch || fetch.bind(window);
    const response = await fetchFn(url.toString(), {
      method: 'POST',
      body: formData
    });

    return this.handleResponse<T>(response);
  }
}

// 預設的 API 客戶端實例（不含認證）
export const apiClient = new ApiClient();

// 創建帶認證的 API 客戶端
export function createAuthApiClient(authFetch: (url: string, options?: RequestInit) => Promise<Response>) {
  return new ApiClient(authFetch);
}
