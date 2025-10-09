// frontend/src/services/datesApi.ts
/**
 * 日期管理 API
 * 職責：日期範圍和編號管理
 */

import { apiClient, createAuthApiClient } from './apiClient';
import type { DateRange, NextDailyNoResponse } from './types';

export class DatesApi {
  /**
   * 取得日期範圍
   */
  static async getRange(
    authFetch?: (url: string, options?: RequestInit) => Promise<Response>
  ): Promise<DateRange> {
    const client = authFetch ? createAuthApiClient(authFetch) : apiClient;
    return client.get<DateRange>('/api/dates/range');
  }

  /**
   * 取得下一個日報編號
   */
  static async getNextDailyNo(
    authFetch?: (url: string, options?: RequestInit) => Promise<Response>
  ): Promise<NextDailyNoResponse> {
    const client = authFetch ? createAuthApiClient(authFetch) : apiClient;
    return client.get<NextDailyNoResponse>('/api/dates/next-daily-no');
  }

  /**
   * 格式化日期為 YYYYMMDD 格式
   */
  static formatDateForApi(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}${month}${day}`;
  }

  /**
   * 將 YYYYMMDD 格式轉換為 Date 物件
   */
  static parseDateFromApi(dateStr: string): Date {
    if (dateStr.length !== 8) {
      throw new Error('日期格式錯誤，應為 YYYYMMDD');
    }

    const year = parseInt(dateStr.substring(0, 4));
    const month = parseInt(dateStr.substring(4, 6)) - 1; // 月份從0開始
    const day = parseInt(dateStr.substring(6, 8));

    return new Date(year, month, day);
  }
}
