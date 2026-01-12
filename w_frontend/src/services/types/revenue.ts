// frontend/src/services/types/revenue.ts

export interface RevenueData {
  cocode?: string;
  coabbv?: string;
  year: number;
  week_no: number;
  DATA_DATE?: string;
  month?: string;
  cateno1?: string;
  catedesc1?: string;  // 產品類別
  last_updatetime?: string;
  ym_bg_rev_amt?: number;  // 年月預算營收金額
  ym_rev_amt?: number;  // 年月營收金額（月累計營收）
  y_rev_amt?: number;  // 年度營收金額（年度出貨）
  rev_amt?: number;  // 營收金額
  m_rev_amt?: number;  // 月營收金額
}

export interface RevenueResponse {
  ResponseCmd: string;
  ResponseData: RevenueData[];
  ResponseNo: string;
  ResponseNa: string;
}
