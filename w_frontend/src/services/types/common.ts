// frontend/src/services/types/common.ts
/**
 * 共用型別定義
 */

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  detail?: string;
}

export interface PaginationParams {
  page?: number;
  pageSize?: number;
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  total: number;
  page: number;
  pageSize: number;
}
