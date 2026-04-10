// frontend/src/services/weeklyReportApi.ts

import { apiConfig, buildApiUrl } from "../config/api";

// 工作項目列表（與後端 JOB_ITEMS 對齊，1-based index）
const JOB_ITEMS_LIST = [
  "營收報告",     // 1
  "工作重點",     // 2
  "應收帳款追蹤", // 3
  "原廠說明",     // 4
  "市場動態",     // 5
  "競爭者資訊",   // 6
  "專案",         // 7
  "部門人事",     // 8
  "其他",         // 9
];

// ID → 名稱
const JOB_ITEM_MAP: { [key: number]: string } = Object.fromEntries(
  JOB_ITEMS_LIST.map((name, i) => [i + 1, name])
);

// 名稱 → ID
const JOB_ITEM_REVERSE_MAP: { [key: string]: number } = Object.fromEntries(
  JOB_ITEMS_LIST.map((name, i) => [name, i + 1])
);

// API 回傳的原始資料型別
export interface WeeklyReportListData {
  COCODE: string;
  SORT_COCODE: string;
  G_DEPTNO: string;
  COABBV: string;
  COABBV2: string;
  DEPTABBV: string;
  WEEKLY_NO: string;
  EMPNO: string;
  EMPNAMEC: string;
  SDATE: string;
  EDATE: string;
  CLASSIFY: string;
  ATT_FILE1: string;
  ATT_FILE2: string;
  ATT_FILE3: string;
  EMERGENCY: string;
  REPLY_STATUS: string;
  OPENPATH: string;
  OPENWEBPAGE: string;
  STATUS: string;
  WEEK_NO: string;
  YY: string;
  REPLY_COUNT: string;
  REPLIER_COUNT: string;
  ISFORWARDED: string;
  DOC_DATE: string;
  LASTDATETIME: string;
  PRACTICE_COCODE: string;
  MY_ASK: string;
  OTHER_ASK: string;
  sop_action: string;
}

// API 回傳的整體結構
export interface WeeklyReportListResponse {
  ResponseCmd: string;
  ResponseData: WeeklyReportListData[];
  ResponseNo: string;
  ResponseNa: string;
}

export interface WeeklyReportForm {
  week: number;
  year: number;
  work_item_id?: number;
  subject: string;
  content: string;
  files: Array<{
    name: string;
    url: string;
    file_path?: string;
    type: string;
    size: number;
  }>;
}

export class WeeklyReportApi {
  /**
   * 獲取工作項目列表
   */
  static async getWorkItems(authFetch: Function) {
    try {
      const response = await authFetch(
        buildApiUrl(apiConfig.endpoints.weekly.jobItems)
      );
      if (!response.ok) throw new Error("Failed to load job items");

      const data = await response.json();
      // 將字符串陣列轉換為 { id, name } 格式，使用 1-based index
      return data.job_items.map((item: string, index: number) => ({
        id: JOB_ITEM_REVERSE_MAP[item] || (index + 1),
        name: item,
      }));
    } catch (error) {
      console.error("獲取工作項目失敗:", error);
      // 返回默認列表
      return Object.entries(JOB_ITEM_MAP).map(([id, name]) => ({
        id: parseInt(id),
        name,
      }));
    }
  }

  /**
   * 獲取週報列表
   */
  static async getWeeklyReports(
    year: number,
    week: number,
    authFetch: Function
  ) {
    try {
      const url = buildApiUrl(apiConfig.endpoints.weekly.reportList);

      // 構建請求參數
      const payload = {
        empno: "", // 由後端從 token 中取得
        year: String(year),
        weeklyNo: String(week),
      };

      const response = await authFetch(url, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error("Failed to load weekly reports");

      const data: WeeklyReportListResponse = await response.json();

      // 轉換後端格式為前端格式
      const transformedData = this.transformWeeklyReportList(data);

      return transformedData;
    } catch (error) {
      console.error("獲取週報列表失敗:", error);
      throw error;
    }
  }

  /**
   * 轉換週報列表資料格式（後端 → 前端）
   */
  private static transformWeeklyReportList(response: WeeklyReportListResponse) {
    const reports = (response.ResponseData || []).map((item) => {
      // 解析附件
      const attachments = [];
      if (item.ATT_FILE1) attachments.push({ file_path: item.ATT_FILE1 });
      if (item.ATT_FILE2) attachments.push({ file_path: item.ATT_FILE2 });
      if (item.ATT_FILE3) attachments.push({ file_path: item.ATT_FILE3 });

      return {
        id: parseInt(item.WEEKLY_NO) || 0,
        week: parseInt(item.WEEK_NO) || 0,
        year: parseInt(item.YY) || 0,
        employee: {
          id: 0, // 後端未提供
          empno: item.EMPNO,
          name: item.EMPNAMEC,
          department_no: item.G_DEPTNO,
          department_name: item.DEPTABBV,
          company_code: item.COCODE,
          company_name: item.COABBV, // 公司名稱
        },
        work_item: {
          id: JOB_ITEM_REVERSE_MAP[item.CLASSIFY] || 0,
          name: item.CLASSIFY,
        },
        subject: item.CLASSIFY, // 使用 CLASSIFY 作為主題
        content: "", // 後端未提供完整內容
        status: item.STATUS === "1" ? "reviewed" : "pending",
        attachments: attachments,
        last_update: item.LASTDATETIME,
        reply_count: parseInt(item.REPLY_COUNT) || 0,
        replier_count: parseInt(item.REPLIER_COUNT) || 0,
        my_ask: item.MY_ASK === "1" || item.MY_ASK === "true",
        other_ask: item.OTHER_ASK === "1" || item.OTHER_ASK === "true",
        is_forwarded: item.ISFORWARDED === "1" || item.ISFORWARDED === "true",
        can_view_detail: true, // ✅ 週報系統：所有週報都可查看
        start_date: item.SDATE, // 週報開始日期
        end_date: item.EDATE, // 週報結束日期
      };
    });

    // 簡單分組：暫時都放在 subordinate_reports
    // TODO: 根據實際業務邏輯區分 subordinate 和 forwarded
    return {
      subordinate_reports: reports,
      forwarded_reports: [],
    };
  }

  /**
   * 獲取本週筆記列表
   */
  static async getWeeklyNotes(
    year: number,
    week: number,
    empno: string,
    authFetch: Function
  ) {
    try {
      const url = `${buildApiUrl(
        apiConfig.endpoints.weekly.drafts
      )}?year=${year}&week=${week}`;
      const response = await authFetch(url);

      if (!response.ok) throw new Error("Failed to load drafts");

      const data = await response.json();

      // 轉換後端格式為前端格式
      const notes = (data.drafts || []).map((draft: any) => ({
        id: draft.seq, // 使用 seq 作為 id
        work_item_id: JOB_ITEM_REVERSE_MAP[draft.job_item] || 1,
        work_item_name: draft.job_item,
        subject: draft.subject || "",
        content: draft.content || "",
        files: (draft.files || []).map((file: any) => ({
          id: file.id || 0,
          name: file.filename || file.name || "",
          type: file.file_type || file.type || "",
          size: file.file_size || file.size || 0,
          url: file.url || "",
          file_path: file.file_path || "",
          is_selected_for_ai: file.is_selected_for_ai || false,
        })),
        ai_content: draft.ai_content || undefined,
        ai_service: draft.ai_service || undefined,
        weekly_no: draft.weekly_no,
        seq: draft.seq,
      }));

      return {
        weekly_no: data.weekly_no,
        notes,
      };
    } catch (error) {
      console.error("獲取週報筆記失敗:", error);
      throw error;
    }
  }

  /**
   * 保存週報草稿
   */
  static async saveDraft(
    data: WeeklyReportForm,
    authFetch: Function,
    weeklyNo?: string,
    seq?: number
  ) {
    try {
      // 轉換前端格式為後端格式
      const payload = {
        weekly_no: weeklyNo,
        seq: seq,
        year: data.year,
        week: data.week,
        subject: data.subject,
        job_item: JOB_ITEM_MAP[data.work_item_id || 1],
        content: data.content,
        files: data.files.map((f) => ({
          id: f.id,
          filename: f.name,
          name: f.name,
          file_path: f.file_path || "",
          file_size: f.size,
          size: f.size,
          file_type: f.type,
          type: f.type,
          url: f.url || "",
          is_selected_for_ai: f.is_selected_for_ai || false,
        })),
      };

      const response = await authFetch(
        buildApiUrl(apiConfig.endpoints.weekly.drafts),
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      );

      if (!response.ok) throw new Error("保存失敗");

      return response.json();
    } catch (error) {
      console.error("保存草稿失敗:", error);
      throw error;
    }
  }

  /**
   * 刪除週報筆記
   */
  static async deleteNote(weeklyNo: string, seq: number, authFetch: Function) {
    try {
      const url = buildApiUrl(
        apiConfig.endpoints.weekly.deleteDraft(weeklyNo, seq)
      );
      const response = await authFetch(url, { method: "DELETE" });

      if (!response.ok) throw new Error("刪除失敗");

      return response.json();
    } catch (error) {
      console.error("刪除筆記失敗:", error);
      throw error;
    }
  }

  /**
   * 更新週報筆記
   */
  static async updateNote(
    weeklyNo: string,
    seq: number,
    data: WeeklyReportForm,
    authFetch: Function
  ) {
    return this.saveDraft(data, authFetch, weeklyNo, seq);
  }

  /**
   * 提交週報
   */
  static async submitReport(data: WeeklyReportForm, authFetch: Function) {
    // TODO: 實作提交邏輯
    console.log("提交週報:", data);
    return Promise.resolve({
      message: "週報已提交",
      status: "submitted",
    });
  }

  /**
   * 上傳檔案
   */
  static async uploadFile(
    file: File,
    weeklyNo: string,
    seq: number,
    authFetch: Function
  ) {
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("weekly_no", weeklyNo);
      formData.append("seq", String(seq));

      const response = await authFetch(
        buildApiUrl(apiConfig.endpoints.weekly.upload),
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) throw new Error("檔案上傳失敗");

      return response.json();
    } catch (error) {
      console.error("上傳檔案失敗:", error);
      throw error;
    }
  }

  /**
   * 刪除檔案
   */
  static async deleteFile(
    weeklyNo: string,
    seq: number,
    filename: string,
    authFetch: Function
  ) {
    try {
      const url = buildApiUrl(
        apiConfig.endpoints.weekly.deleteFile(weeklyNo, seq, filename)
      );
      const response = await authFetch(url, { method: "DELETE" });

      if (!response.ok) throw new Error("檔案刪除失敗");

      return response.json();
    } catch (error) {
      console.error("刪除檔案失敗:", error);
      throw error;
    }
  }

  /**
   * AI 潤飾單筆筆記（潤飾結果存入資料庫）
   */
  static async enhanceOne(
    weeklyNo: string,
    seq: number,
    aiService: string,
    authFetch: Function
  ) {
    try {
      const url = `${buildApiUrl(
        apiConfig.endpoints.weekly.drafts
      )}/enhance-one/${weeklyNo}/${seq}?ai_service=${aiService}`;
      const response = await authFetch(url, {
        method: "POST",
      });

      if (!response.ok) throw new Error("AI 潤飾失敗");

      return response.json();
    } catch (error) {
      console.error("AI 潤飾失敗:", error);
      throw error;
    }
  }

  /**
   * 一次取得週報初始化資料：當前應交週次 + 該週草稿列表
   *
   * @param year/week 指定週次（首頁用）
   * @param offset 從今天偏移週數（-1=上週）；只在沒給 year/week 時生效
   * @param includeDrafts 是否查詢 DB 拿草稿（首頁不需要時設 false 加快速度）
   */
  static async getInit(
    authFetch: Function,
    options: {
      year?: number;
      week?: number;
      offset?: number;
      includeDrafts?: boolean;
    } = {}
  ) {
    try {
      let url = buildApiUrl(apiConfig.endpoints.weekly.init);
      const params: string[] = [];
      if (options.year) params.push(`year=${options.year}`);
      if (options.week) params.push(`week=${options.week}`);
      if (options.offset) params.push(`offset=${options.offset}`);
      if (options.includeDrafts === false) params.push(`include_drafts=false`);
      if (params.length) url += `?${params.join("&")}`;

      const response = await authFetch(url);
      if (!response.ok) throw new Error("取得週報初始資料失敗");

      const data = await response.json();

      // 轉換 drafts 為前端格式
      const notes = (data.drafts || []).map((draft: any) => ({
        id: draft.seq,
        work_item_id: JOB_ITEM_REVERSE_MAP[draft.job_item] || 1,
        work_item_name: draft.job_item,
        subject: draft.subject || "",
        content: draft.content || "",
        files: (draft.files || []).map((file: any) => ({
          id: file.id || 0,
          name: file.filename || file.name || "",
          type: file.file_type || file.type || "",
          size: file.file_size || file.size || 0,
          url: file.url || "",
          file_path: file.file_path || "",
          is_selected_for_ai: file.is_selected_for_ai || false,
        })),
        ai_content: draft.ai_content || undefined,
        ai_service: draft.ai_service || undefined,
        weekly_no: draft.weekly_no,
        seq: draft.seq,
      }));

      return {
        year: data.year as number,
        weekly_no: data.weekly_no as number,
        can_send: data.can_send as boolean,
        startdate: data.startdate as string,  // YYYYMMDD
        enddate: data.enddate as string,      // YYYYMMDD
        weekly_no_id: data.weekly_no_id as string,  // 週報編號（DB 用）
        notes,
      };
    } catch (error) {
      console.error("取得週報初始資料失敗:", error);
      throw error;
    }
  }

  /**
   * 取得當前週往前 count 週的列表（給 WeekSelector）
   * 結果按時間升冪排序（最舊在前，當前在最後）
   */
  static async getWeekList(authFetch: Function, count: number = 20) {
    try {
      const url = `${buildApiUrl(apiConfig.endpoints.weekly.weekList)}?count=${count}`;
      const response = await authFetch(url);
      if (!response.ok) throw new Error("取得週次列表失敗");
      return response.json() as Promise<{
        weeks: Array<{
          year: number;
          weekly_no: number;
          startdate: string; // YYYYMMDD
          enddate: string;   // YYYYMMDD
        }>;
      }>;
    } catch (error) {
      console.error("取得週次列表失敗:", error);
      throw error;
    }
  }

  /**
   * 根據年份和週次取得日期區間（後端 cache，幾乎不會打 CommonAPI）
   * 回傳 YYYYMMDD 格式
   */
  static async getWeekPeriod(
    year: number,
    weeklyNo: number,
    authFetch: Function
  ) {
    try {
      const url = `${buildApiUrl(apiConfig.endpoints.weekly.weekPeriod)}?year=${year}&weeklyNo=${weeklyNo}`;
      const response = await authFetch(url);
      if (!response.ok) throw new Error("取得日期區間失敗");
      return response.json() as Promise<{
        year: number;
        weekly_no: number;
        startdate: string;  // YYYYMMDD
        enddate: string;    // YYYYMMDD
      }>;
    } catch (error) {
      console.error("取得日期區間失敗:", error);
      throw error;
    }
  }

  /**
   * 獲取逾期應收帳款
   * @param empno 可選，指定員工工號。若不傳則使用當前登入用戶的工號
   */
  static async getOverdueAR(
    year: number,
    weekNo: number,
    authFetch: Function,
    empno?: string
  ) {
    try {
      const url = buildApiUrl("/api/weekly/overdue-ar");
      const payload: { year: number; week_no: number; empno?: string } = {
        year,
        week_no: weekNo,
      };
      if (empno) {
        payload.empno = empno;
      }

      const response = await authFetch(url, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error("Failed to get overdue AR");

      return response.json();
    } catch (error) {
      console.error("獲取逾期應收帳款失敗:", error);
      throw error;
    }
  }

  /**
   * 獲取營收達成率
   * @param empno 可選，指定員工工號。若不傳則使用當前登入用戶的工號
   */
  static async getRevenue(
    year: number,
    weekNo: number,
    authFetch: Function,
    empno?: string
  ) {
    try {
      const url = buildApiUrl("/api/weekly/revenue");
      const payload: { year: number; week_no: number; empno?: string } = {
        year,
        week_no: weekNo,
      };
      if (empno) {
        payload.empno = empno;
      }

      const response = await authFetch(url, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error("Failed to get revenue");

      return response.json();
    } catch (error) {
      console.error("獲取營收達成率失敗:", error);
      throw error;
    }
  }

  /**
   * 提交週報
   */
  static async submitWeeklyReport(
    weeklyNo: string,
    year: number,
    weekNo: number,
    authFetch: Function
  ) {
    try {
      const url = buildApiUrl("/api/weekly/submit-weekly-report");
      const payload = {
        weekly_no: weeklyNo,
        year,
        week_no: weekNo,
      };

      const response = await authFetch(url, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error("Failed to submit weekly report");

      return response.json();
    } catch (error) {
      console.error("提交週報失敗:", error);
      throw error;
    }
  }

  /**
   * 獲取週報詳情（包含主檔、明細、回覆）
   */
  static async getWeeklyReportDetail(
    weeklyNo: string,
    authFetch: Function
  ) {
    try {
      const url = buildApiUrl(`/api/weekly/report-detail/${weeklyNo}`);
      const response = await authFetch(url);

      if (!response.ok) throw new Error("Failed to get weekly report detail");

      return response.json();
    } catch (error) {
      console.error("獲取週報詳情失敗:", error);
      throw error;
    }
  }

  /**
   * 回覆週報
   */
  static async replyWeeklyReport(
    weeklyNo: string,
    replyMemo: string,
    score: number | null,
    toUsers: string[],
    forwardUsers: string[],
    authFetch: Function
  ) {
    try {
      const url = buildApiUrl(apiConfig.endpoints.weekly.reply);
      const payload = {
        weekly_no: weeklyNo,
        reply_memo: replyMemo,
        score: score,
        to_users: toUsers,
        forward_users: forwardUsers,
      };

      const response = await authFetch(url, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error("Failed to reply weekly report");

      return response.json();
    } catch (error) {
      console.error("回覆週報失敗:", error);
      throw error;
    }
  }
}
