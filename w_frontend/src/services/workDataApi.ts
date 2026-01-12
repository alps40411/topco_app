// frontend/src/services/workDataApi.ts
/**
 * 工作資料 API
 * 職責：整合所有工作相關資料查詢
 */

import { apiClient, createAuthApiClient } from './apiClient';
import type {
  WorkDataResponse,
  WorkPlan,
  ExecutionWork,
  ServiceCompany,
  ServiceTarget
} from './types';

export class WorkDataApi {
  /**
   * 取得所有工作資料（推薦）
   */
  static async getAll(
    authFetch?: (url: string, options?: RequestInit) => Promise<Response>
  ): Promise<{
    projects: WorkPlan[];
    executionWorks: ExecutionWork[];
    serviceCompanies: ServiceCompany[];
    serviceTargets: ServiceTarget[];
  }> {
    const client = authFetch ? createAuthApiClient(authFetch) : apiClient;
    const response = await client.get<WorkDataResponse>('/api/work-data');

    // 新 API 格式轉換
    const data = response.data || response;

    return {
      projects: data.projects || data.work_plans || [],
      executionWorks: data.execution_works || data.basic_execution_works || [],
      serviceCompanies: data.service_companies || [],
      serviceTargets: data.service_targets || []
    };
  }

  /**
   * 取得專案/工作計畫列表
   */
  static async getProjects(
    authFetch?: (url: string, options?: RequestInit) => Promise<Response>
  ): Promise<WorkPlan[]> {
    const client = authFetch ? createAuthApiClient(authFetch) : apiClient;
    const response = await client.get<WorkDataResponse>('/api/work-data', {
      include: 'projects'
    });
    return response.data?.projects || [];
  }

  /**
   * 取得執行工作列表
   */
  static async getExecutionWorks(
    authFetch?: (url: string, options?: RequestInit) => Promise<Response>
  ): Promise<ExecutionWork[]> {
    const client = authFetch ? createAuthApiClient(authFetch) : apiClient;
    const response = await client.get<WorkDataResponse>('/api/work-data', {
      include: 'execution_works'
    });
    return response.data?.execution_works || [];
  }

  /**
   * 取得服務公司列表
   */
  static async getServiceCompanies(
    authFetch?: (url: string, options?: RequestInit) => Promise<Response>
  ): Promise<ServiceCompany[]> {
    const client = authFetch ? createAuthApiClient(authFetch) : apiClient;
    const response = await client.get<WorkDataResponse>('/api/work-data', {
      include: 'service_companies'
    });
    return response.data?.service_companies || [];
  }

  /**
   * 取得服務對象列表
   */
  static async getServiceTargets(
    authFetch?: (url: string, options?: RequestInit) => Promise<Response>
  ): Promise<ServiceTarget[]> {
    const client = authFetch ? createAuthApiClient(authFetch) : apiClient;
    const response = await client.get<WorkDataResponse>('/api/work-data', {
      include: 'service_targets'
    });
    return response.data?.service_targets || [];
  }
}
