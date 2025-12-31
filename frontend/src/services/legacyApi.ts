// frontend/src/services/legacyApi.ts
import { apiConfig, buildApiUrl } from "../config/api";

// 日報列表項目類型
export interface DailyReportListItem {
  daily_no: string;
  cocode: string;
  empno: string;
  empnamec: string;
  emergency?: string;
  classify?: string;
  att_file1?: string;
  att_file2?: string;
  att_file3?: string;
  cust_ename1?: string;
  cust_ename2?: string;
  cust_ename3?: string;
  cust_comp_abbv1?: string;
  cust_comp_abbv2?: string;
  cust_comp_abbv3?: string;
  sop_desc_c?: string;
  reply_status?: string;
  memo_status?: string;
  doc_date: string;
  proj_status?: string;
  openpath?: string;
  openwebpage?: string;
  sort_cocode: string;
  g_deptno: string;
  deptnamec: string;
  reply_count: number;
  replier_count: number;
  my_ask?: string;
  other_ask?: string;
  isForwarded: string;
  lastdatetime?: string;
  practice_cocode?: string;
  coabbv?: string;
}

// 日報內容詳細類型
export interface DailyReportContent {
  cuno1?: string;
  daily_sub_nos: string;
  sopno?: string;
  sop_code?: string;
  prod_cate?: string;
  itemdesc1?: string;
  exetime?: number;
  estimate?: number;
  attitude?: string;
  memo_collect?: string;
  cuno_subj?: string;
  cuno_msg?: string;
  cuno_collect?: string;
  comp_inf?: string;
  comp_desc?: string;
  comp_collect?: string;
  ques_subj?: string;
  ques_desc?: string;
  solut_subj?: string;
  solut_desc?: string;
  solut_status?: string;
  att_file3?: string;
  xuser?: string;
  xdate?: string;
  xtime?: string;
  empname1?: string;
  empname2?: string;
  empname3?: string;
  empname4?: string;
  empname5?: string;
  prod_no?: string;
  create_msg?: string;
  comp_serno?: string;
  cuno_comp_serno?: string;
  cocode: string;
  empno: string;
  status: string;
  planno?: string;
  memo?: string;
  cuno_infcont?: string;
  comp_infcont?: string;
  ques_infcont?: string;
  solut_infcont?: string;
  finish_rate?: number;
  pps_cocode?: string;
  pps_empno?: string;
  pps_deptno?: string;
  pps_empnamec?: string;
  ship_log?: string;
  cuno_msg1?: string;
  ques_desc1?: string;
  solut_desc1?: string;
  memo1?: string;
  cuno_msg2?: string;
  ques_desc2?: string;
  solut_desc2?: string;
  memo2?: string;
  reply?: string;
  pps_servecocode?: string;
  projno?: string;
  proj_cocode?: string;
}

// 工作計畫類型
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

// 公司資料類型
export interface Company {
  cocode: string;
  coabbv: string;
}

// 日報查詢參數類型
export interface ReportQueryParams {
  empno: string;
  doc_date: string;
  cocode?: string;
  deptno?: string;
}

// 暫存和提交相關類型
export interface DraftSaveRequest {
  daily_no: string;
  empno: string;
  cocode: string;
  doc_date: string; // YYYYMMDD
  draft_type?: string; // TEMP(暫存), AI(AI草稿)
  draft_content: Record<string, any>; // JSON 格式的暫存內容
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

export class LegacyApi {
  /**
   * 取得日報列表 BY 工號（主管）
   */
  static async getDailyReports(
    params: ReportQueryParams
  ): Promise<DailyReportListItem[]> {
    const { empno, doc_date, cocode, deptno } = params;

    // 構建查詢參數
    const queryParams = new URLSearchParams({
      empno,
      doc_date,
    });

    if (cocode) queryParams.append("cocode", cocode);
    if (deptno) queryParams.append("deptno", deptno);

    const url = buildApiUrl(
      `${apiConfig.endpoints.legacy.reports}?${queryParams.toString()}`
    );

    try {
      const response = await fetch(url);
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("取得日報列表失敗:", error);
      throw error;
    }
  }

  /**
   * 取得日報內容詳細
   */
  static async getDailyReportContent(
    daily_no: string
  ): Promise<DailyReportContent[]> {
    const url = buildApiUrl(
      `${apiConfig.endpoints.legacy.reportContent}/${daily_no}/content`
    );

    try {
      const response = await fetch(url);
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("取得日報內容失敗:", error);
      throw error;
    }
  }

  /**
   * 取得工作計畫
   */
  static async getWorkPlans(empno: string): Promise<WorkPlan[]> {
    const url = buildApiUrl(
      `${apiConfig.endpoints.legacy.workPlans}?empno=${empno}`
    );

    try {
      const response = await fetch(url);
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("取得工作計畫失敗:", error);
      throw error;
    }
  }

  /**
   * 取得服務公司列表
   */
  static async getCompanies(): Promise<Company[]> {
    const url = buildApiUrl(apiConfig.endpoints.legacy.companies);

    try {
      const response = await fetch(url);
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("取得公司列表失敗:", error);
      throw error;
    }
  }

  /**
   * 已廢棄: 取得新的日報編號
   * 原因: save_draft API 會自動處理 daily_no 的生成
   * 使用方式: 呼叫 saveDraft 時傳入 daily_no: null 即可
   */
  // static async getNextDailyNo() - 已移除

  /**
   * 格式化日期為 YYYYMMDD 格式
   */
  static formatDateForApi(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}${month}${day}`;
  }

  /**
   * 將 YYYYMMDD 格式轉換為 Date 物件
   */
  static parseDateFromApi(dateStr: string): Date {
    if (dateStr.length !== 8) {
      throw new Error("日期格式錯誤，應為 YYYYMMDD");
    }

    const year = parseInt(dateStr.substring(0, 4));
    const month = parseInt(dateStr.substring(4, 6)) - 1; // 月份從0開始
    const day = parseInt(dateStr.substring(6, 8));

    return new Date(year, month, day);
  }

  // === 暫存和提交相關方法 ===

  /**
   * 保存日報暫存
   */
  static async saveDraft(
    draftData: DraftSaveRequest
  ): Promise<{ draft_id: string; daily_no: string; message: string }> {
    const url = buildApiUrl(apiConfig.endpoints.legacy.drafts);

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(draftData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("保存暫存失敗:", error);
      throw error;
    }
  }

  /**
   * 保存AI草稿
   */
  static async saveAIDraft(
    aiDraftData: AIDraftSaveRequest
  ): Promise<{ ai_draft_id: string; message: string }> {
    const url = buildApiUrl(apiConfig.endpoints.legacy.aiDrafts);

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(aiDraftData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("保存AI草稿失敗:", error);
      throw error;
    }
  }

  /**
   * 正式提交日報
   */
  static async submitReport(
    submitData: ReportSubmitRequest
  ): Promise<{ daily_no: string; status: string; message: string }> {
    const url = buildApiUrl(apiConfig.endpoints.legacy.submit);

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(submitData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("提交日報失敗:", error);
      throw error;
    }
  }

  /**
   * 取得員工的暫存資料
   */
  static async getDrafts(empno: string, draftType?: string): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (draftType) {
      queryParams.append("draft_type", draftType);
    }

    const url = buildApiUrl(
      `${apiConfig.endpoints.legacy.drafts}/${empno}${
        queryParams.toString() ? "?" + queryParams.toString() : ""
      }`
    );

    try {
      const response = await fetch(url);
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("取得暫存資料失敗:", error);
      throw error;
    }
  }

  /**
   * 取得員工的AI草稿
   */
  static async getAIDrafts(empno: string): Promise<any[]> {
    const url = buildApiUrl(`${apiConfig.endpoints.legacy.aiDrafts}/${empno}`);

    try {
      const response = await fetch(url);
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("取得AI草稿失敗:", error);
      throw error;
    }
  }

  /**
   * 刪除暫存資料
   */
  static async deleteDraft(draftId: string): Promise<{ message: string }> {
    const url = buildApiUrl(`${apiConfig.endpoints.legacy.drafts}/${draftId}`);

    try {
      const response = await fetch(url, {
        method: "DELETE",
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("刪除暫存資料失敗:", error);
      throw error;
    }
  }

  // === 工作計畫階層API ===

  /**
   * 取得所有工作相關資料（統一API）
   */
  static async getAllWorkData(
    empno: string,
    authFetch?: (url: string, options?: RequestInit) => Promise<Response>
  ): Promise<{
    work_plans: any[];
    basic_execution_works: any[];
    project_execution_works: { [key: string]: any[] };
    service_companies: Array<{
      id: string;
      cocode: string;
      coabbv: string;
    }>;
    service_targets: Array<{
      cocode: string;
      coabbv: string;
      deptno: string;
      deptabbv: string;
      empno: string;
      empnamec: string;
    }>;
  }> {
    // 使用新的 API 端點（需要身份驗證）
    // 注意：如果使用 authFetch，不要先呼叫 buildApiUrl，因為 authFetch 會自己處理
    const endpoint = apiConfig.endpoints.workData.all || '/api/work-data';
    const url = authFetch ? endpoint : buildApiUrl(endpoint);
    console.log('[LegacyApi] getAllWorkData called:', { empno, endpoint, url, hasAuthFetch: !!authFetch });

    try {
      // 如果提供了 authFetch，使用它（推薦）
      const fetchFn = authFetch || fetch.bind(window);
      console.log('[LegacyApi] Fetching work data from:', url);
      const response = await fetchFn(url);

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      const result = await response.json();

      // 新 API 返回格式：{ success: true, data: {...} }
      const data = result.data || result;

      // 檢測並轉換新的正規化格式
      if (data.execution_works && typeof data.execution_works === 'object' &&
          !Array.isArray(data.execution_works)) {
        // 新格式：execution_works 是字典
        console.log('[LegacyApi] 檢測到新的正規化格式，進行轉換...');

        return this.convertNormalizedFormat(data);
      }

      // 舊格式：execution_works 是陣列或不存在
      if (data.projects && (Array.isArray(data.execution_works) || data.basic_execution_works)) {
        console.log('[LegacyApi] 使用舊格式');
        return {
          work_plans: data.projects || [],
          basic_execution_works: data.basic_execution_works || data.execution_works || [],
          project_execution_works: data.project_execution_works || {},
          service_companies: data.service_companies || [],
          service_targets: data.service_targets || []
        };
      }

      // 直接返回
      return data;
    } catch (error) {
      console.error("取得工作資料失敗:", error);
      throw error;
    }
  }

  /**
   * 將新的正規化格式轉換為前端期望的舊格式
   *
   * 新格式結構：
   * {
   *   execution_works: { [sopno]: ExecutionWork },
   *   basic_execution_sopnos: string[],
   *   project_execution_mapping: { [planno]: string[] }
   * }
   *
   * 舊格式結構：
   * {
   *   basic_execution_works: ExecutionWork[],
   *   project_execution_works: { [planno]: ExecutionWork[] }
   * }
   */
  private static convertNormalizedFormat(data: any): {
    work_plans: any[];
    basic_execution_works: any[];
    project_execution_works: { [key: string]: any[] };
    service_companies: any[];
    service_targets: any[];
  } {
    const executionWorksDict = data.execution_works || {};
    const basicSopnos = data.basic_execution_sopnos || [];
    const projectMapping = data.project_execution_mapping || {};

    // 1. 轉換基本執行工作（使用 sopno 參照）
    const basic_execution_works = basicSopnos
      .map((sopno: string) => {
        const work = executionWorksDict[sopno];
        if (!work) {
          console.warn(`[LegacyApi] 警告：基本執行工作 sopno=${sopno} 在 execution_works 中不存在`);
          return null;
        }
        return work;
      })
      .filter((work: any) => work !== null); // 過濾掉不存在的

    // 2. 轉換專案執行工作映射（使用 sopno 參照）
    const project_execution_works: { [key: string]: any[] } = {};

    for (const [planno, sopnos] of Object.entries(projectMapping)) {
      if (!Array.isArray(sopnos)) {
        console.warn(`[LegacyApi] 警告：專案 ${planno} 的 sopnos 不是陣列:`, sopnos);
        continue;
      }

      project_execution_works[planno] = sopnos
        .map((sopno: string) => {
          const work = executionWorksDict[sopno];
          if (!work) {
            console.warn(`[LegacyApi] 警告：專案 ${planno} 的執行工作 sopno=${sopno} 在 execution_works 中不存在`);
            return null;
          }
          return work;
        })
        .filter((work: any) => work !== null); // 過濾掉不存在的
    }

    // 3. 記錄轉換統計
    const totalExecutionWorks = Object.keys(executionWorksDict).length;
    const basicCount = basic_execution_works.length;
    const projectCount = Object.keys(project_execution_works).length;

    console.log(`[LegacyApi] 格式轉換完成:
      - 執行工作字典: ${totalExecutionWorks} 個
      - 基本執行工作: ${basicCount} 個 (sopnos: ${basicSopnos.length})
      - 專案執行工作: ${projectCount} 個專案
    `);

    // 檢查是否有遺失的 sopno
    const missingSopnos = basicSopnos.filter((sopno: string) => !executionWorksDict[sopno]);
    if (missingSopnos.length > 0) {
      console.error(`[LegacyApi] 錯誤：有 ${missingSopnos.length} 個基本執行工作的 sopno 在字典中找不到:`, missingSopnos);
    }

    return {
      work_plans: data.projects || [],
      basic_execution_works,
      project_execution_works,
      service_companies: data.service_companies || [],
      service_targets: data.service_targets || []
    };
  }

  /**
   * 取得執行工作列表 (基於工作計畫或基本執行工作)
   */
  static async getExecutionWorks(
    planno: string,
    empno: string
  ): Promise<any[]> {
    const queryParams = new URLSearchParams({
      empno,
    });

    // 只有當 planno 不為空時才加入查詢參數
    if (planno && planno.trim()) {
      queryParams.append("planno", planno);
    }

    const url = buildApiUrl(
      `${apiConfig.endpoints.legacy.executionWorks}?${queryParams.toString()}`
    );

    try {
      const response = await fetch(url);
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("取得執行工作失敗:", error);
      throw error;
    }
  }

  /**
   * 取得工作項目列表 (基於執行工作)
   */
  static async getWorkItems(sopno: string): Promise<any[]> {
    const queryParams = new URLSearchParams({
      sopno,
    });

    const url = buildApiUrl(
      `${apiConfig.endpoints.legacy.workItems}?${queryParams.toString()}`
    );

    try {
      const response = await fetch(url);
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("取得工作項目失敗:", error);
      throw error;
    }
  }

  /**
   * 取得服務公司列表
   */
  static async getServiceCompanies(): Promise<any[]> {
    const url = buildApiUrl(apiConfig.endpoints.legacy.serviceCompanies);

    try {
      const response = await fetch(url);
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("取得服務公司失敗:", error);
      throw error;
    }
  }

  /**
   * 取得服務對象列表 (基於服務公司)
   */
  static async getServiceTargets(companyCocode?: string): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (companyCocode) {
      queryParams.append("company_cocode", companyCocode);
    }

    const url = buildApiUrl(
      `${apiConfig.endpoints.legacy.serviceTargets}${
        queryParams.toString() ? "?" + queryParams.toString() : ""
      }`
    );

    try {
      const response = await fetch(url);
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("取得服務對象失敗:", error);
      throw error;
    }
  }
}
