// frontend/src/services/types/report.ts
/**
 * 日報相關型別定義
 */

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
  deptno: string;
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

export interface Comment {
  id: string;
  report_id: string;
  user_id: string;
  username: string;
  content: string;
  created_at: string;
}

export interface Approval {
  id: string;
  report_id: string;
  approver_id: string;
  approver_name: string;
  status: 'pending' | 'approved' | 'rejected';
  comment?: string;
  created_at: string;
}
