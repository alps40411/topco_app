# backend/app/schemas/legacy_schemas.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date

class DailyReportListItem(BaseModel):
    """日報列表項目"""
    daily_no: str
    cocode: str
    empno: str
    empnamec: str
    emergency: Optional[str]
    classify: Optional[str]
    att_file1: Optional[str]
    att_file2: Optional[str]
    att_file3: Optional[str]
    cust_ename1: Optional[str]
    cust_ename2: Optional[str]
    cust_ename3: Optional[str]
    cust_comp_abbv1: Optional[str]
    cust_comp_abbv2: Optional[str]
    cust_comp_abbv3: Optional[str]
    sop_desc_c: Optional[str]
    reply_status: Optional[str]
    memo_status: Optional[str]
    doc_date: str
    proj_status: Optional[str]
    openpath: Optional[str]
    openwebpage: Optional[str]
    sort_cocode: str
    g_deptno: str
    deptnamec: str
    reply_count: int
    replier_count: int
    my_ask: Optional[str]
    other_ask: Optional[str]
    isForwarded: str
    lastdatetime: Optional[str]
    practice_cocode: Optional[str]
    coabbv: Optional[str]

class DailyReportContent(BaseModel):
    """日報內容詳細"""
    cuno1: Optional[str]
    daily_sub_nos: str
    sopno: Optional[str]
    sop_code: Optional[str]
    prod_cate: Optional[str]
    itemdesc1: Optional[str]
    exetime: Optional[int]
    estimate: Optional[int]
    attitude: Optional[str]
    memo_collect: Optional[str]
    cuno_subj: Optional[str]
    cuno_msg: Optional[str]
    cuno_collect: Optional[str]
    comp_inf: Optional[str]
    comp_desc: Optional[str]
    comp_collect: Optional[str]
    ques_subj: Optional[str]
    ques_desc: Optional[str]
    solut_subj: Optional[str]
    solut_desc: Optional[str]
    solut_status: Optional[str]
    att_file3: Optional[str]
    xuser: Optional[str]
    xdate: Optional[str]
    xtime: Optional[str]
    empname1: Optional[str]
    empname2: Optional[str]
    empname3: Optional[str]
    empname4: Optional[str]
    empname5: Optional[str]
    prod_no: Optional[str]
    create_msg: Optional[str]
    comp_serno: Optional[str]
    cuno_comp_serno: Optional[str]
    cocode: str
    empno: str
    status: str
    planno: Optional[str]
    memo: Optional[str]
    cuno_infcont: Optional[str]
    comp_infcont: Optional[str]
    ques_infcont: Optional[str]
    solut_infcont: Optional[str]
    finish_rate: Optional[int]
    pps_cocode: Optional[str]
    pps_empno: Optional[str]
    pps_deptno: Optional[str]
    pps_empnamec: Optional[str]
    ship_log: Optional[str]
    cuno_msg1: Optional[str]
    ques_desc1: Optional[str]
    solut_desc1: Optional[str]
    memo1: Optional[str]
    cuno_msg2: Optional[str]
    ques_desc2: Optional[str]
    solut_desc2: Optional[str]
    memo2: Optional[str]
    reply: Optional[str]
    pps_servecocode: Optional[str]
    projno: Optional[str]
    proj_cocode: Optional[str]

class WorkPlan(BaseModel):
    """工作計畫"""
    empno: str
    planno: str
    plan_subj_c: Optional[str]
    no: Optional[str]
    sopno: str
    sop_desc_c: Optional[str]
    seq: Optional[int]
    name: Optional[str]

# 暫存相關 Schema
class WorkRecordDraftContent(BaseModel):
    """工作記錄暫存內容"""
    # 工作計畫相關
    planno: Optional[str] = None
    plan_subj_c: Optional[str] = None
    
    # 執行工作相關
    sopno: Optional[str] = None
    sop_desc_c: Optional[str] = None
    
    # 工作項目相關 - 改為陣列支援多選
    work_item_seq: Optional[List[str]] = None
    work_item_name: Optional[str] = None
    
    # 服務相關
    service_cocode: Optional[str] = None  # 服務公司代碼
    service_empno: Optional[str] = None   # 服務對象工號
    service_empnamec: Optional[str] = None # 服務對象姓名
    service_deptno: Optional[str] = None   # 服務對象部門
    
    # 工作內容
    content: str
    execution_time_minutes: int = 0
    
    # 附件
    files: List[Dict[str, Any]] = []

class DraftSaveRequest(BaseModel):
    """暫存保存請求"""
    daily_no: str
    empno: str
    cocode: str
    doc_date: str  # YYYYMMDD
    draft_type: str = "TEMP"  # TEMP(暫存), AI(AI草稿)
    draft_content: WorkRecordDraftContent  # 結構化的暫存內容


class AttachmentSaveRequest(BaseModel):
    """附件保存請求"""
    draft_id: str
    file_name: str
    file_path: str
    file_size: int
    file_type: str
    is_selected_for_ai: bool = False

class ReportSubmitRequest(BaseModel):
    """正式日報提交請求"""
    daily_no: str
    empno: str
    cocode: str
    deptno: str
    doc_date: str  # YYYYMMDD
    emergency: Optional[str]
    classify: Optional[str]
    score: int = 0
    leader: str
    g_deptno: str
    empnamec: str
    deptnamec: str
    sop_desc_c: str
    word_count: int
    att_file1: Optional[str]
    att_file2: Optional[str]
    work_items: List[Dict[str, Any]]  # 工作項目列表

class DraftResponse(BaseModel):
    """暫存回應"""
    draft_id: str
    daily_no: str
    message: str


class SubmitResponse(BaseModel):
    """提交回應"""
    daily_no: str
    status: str
    message: str