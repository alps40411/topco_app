# backend/app/services/legacy_report_submit_service.py

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..schemas.work_record import ConsolidatedReport
from ..models.user import User

logger = logging.getLogger(__name__)

class LegacyReportSubmitService:
    """Legacy 日報提交服務 - 處理將新系統的日報資料插入到 tdr_master, tdr_detail1, tdr_detail2"""
    
    @staticmethod
    def submit_daily_report_to_legacy(
        db: Session, 
        employee,  # Employee model
        consolidated_reports: List[Dict[str, Any]],
        daily_no: Optional[str] = None
    ) -> str:
        """
        將彙整的日報資料提交到 legacy 資料庫
        
        Args:
            db: Legacy 資料庫 session
            employee: 員工資料
            consolidated_reports: 彙整的日報資料
            daily_no: 日報編號 (如果未提供則自動生成)
            
        Returns:
            str: 日報編號
        """
        try:
            # 確保交易狀態正常
            try:
                db.rollback()
            except:
                pass
                
            # 取得目前日期時間
            now = datetime.now()
            current_date = now.strftime('%Y%m%d')
            current_time = now.strftime('%H:%M:%S')
            
            # 生成日報編號 (如果未提供)
            if not daily_no:
                daily_no = LegacyReportSubmitService._generate_daily_no(db, employee.cocode, current_date)
            
            # 計算總字數和執行時間
            total_word_count = 0
            total_execution_time = 0
            
            for report in consolidated_reports:
                content = report.get('content', '')
                total_word_count += len(content)
                total_execution_time += report.get('total_execution_time_minutes', 0)
            
            # 使用原始的 COCODE（不需要轉換）
            legacy_cocode = getattr(employee, 'cocode', 'A')
            
            # 取得主管資料 (暫時設為空值，需要根據實際組織架構調整)
            leader_empno = None
            
            # 取得部門 G_DEPTNO (通常與 DEPTNO 相同或為上級部門)
            g_deptno = getattr(employee, 'department_no', '000')  # 預設值
            
            # 1. 插入 tdr_master
            master_sql = text("""
                INSERT INTO tdr_master (
                    DAILY_NO, COCODE, EMPNO, DEPTNO, DOC_DATE, EMERGENCY, 
                    CLASSIFY, SCORE, XUSER, XDATE, XTIME, STATUS, LEADER, G_DEPTNO, EMPNAMEC, 
                    DEPTNAMEC, UPLOAD_SITE, EMPNAMEC_N, WFINBOX_STATUS, SOP_DESC_C, CUST_ENAME1, 
                    CUST_COMP_ABBV1, WORD_COUNT, ATT_FILE1, ATT_FILE2, openpath, openwebpage
                ) VALUES (
                    :daily_no, :cocode, :empno, :deptno, :doc_date, :emergency,
                    :classify, :score, :xuser, :xdate, :xtime, :status, :leader, :g_deptno, :empnamec,
                    :deptnamec, :upload_site, :empnamec_n, :wfinbox_status, :sop_desc_c, :cust_ename1,
                    :cust_comp_abbv1, :word_count, :att_file1, :att_file2, :openpath, :openwebpage
                )
            """)
            
            # 取得第一個報告的執行工作名稱作為 SOP_DESC_C (限制50字元)
            first_sop_desc_c = ''
            if consolidated_reports:
                raw_sop_desc = consolidated_reports[0].get('execution_work_name', '')
                # 移除換行符號並限制長度
                first_sop_desc_c = raw_sop_desc.replace('\r\n', ' ').replace('\n', ' ').strip()
                if len(first_sop_desc_c) > 50:
                    first_sop_desc_c = first_sop_desc_c[:47] + '...'
            
            master_params = {
                'daily_no': daily_no,
                'cocode': legacy_cocode,
                'empno': getattr(employee, 'empno', ''),
                'deptno': getattr(employee, 'department_no', '000'),
                'doc_date': current_date,
                'emergency': None,  # null or 'Y'
                'classify': None,   # null or 'Y'
                'score': 0,         # 固定0
                'xuser': getattr(employee, 'empno', ''),
                'xdate': current_date,
                'xtime': current_time,
                'status': 'N',      # N:繳交, T:暫存
                'leader': leader_empno,
                'g_deptno': g_deptno,
                'empnamec': getattr(employee, 'name', ''),
                'deptnamec': getattr(employee, 'department_name', ''),
                'upload_site': 'D',
                'empnamec_n': getattr(employee, 'name', ''),
                'wfinbox_status': 'N',
                'sop_desc_c': first_sop_desc_c,
                'cust_ename1': None,
                'cust_comp_abbv1': None,
                'word_count': total_word_count,
                'att_file1': 'ATT_FILE1',  # 固定值或從報告中取得
                'att_file2': 'ATT_FILE2',  # 固定值或從報告中取得
                'openpath': '/MyReport/',
                'openwebpage': 'viewed.aspx'
            }
            
            db.execute(master_sql, master_params)
            
            # 2. 為每個 consolidated_report 插入 tdr_detail1 和 tdr_detail2
            daily_sub_nos = 1
            
            for report in consolidated_reports:
                # 插入 tdr_detail1
                detail1_sql = text("""
                    INSERT INTO tdr_detail1 (
                        DAILY_NO, DAILY_SUB_NOS, XUSER, XDATE, XTIME, CUNO1, COMP_SERNO1
                    ) VALUES (
                        :daily_no, :daily_sub_nos, :xuser, :xdate, :xtime, :cuno1, :comp_serno1
                    )
                """)
                
                detail1_params = {
                    'daily_no': daily_no,
                    'daily_sub_nos': daily_sub_nos,
                    'xuser': getattr(employee, 'empno', ''),
                    'xdate': current_date,
                    'xtime': current_time,
                    'cuno1': None,
                    'comp_serno1': None
                }
                
                db.execute(detail1_sql, detail1_params)
                
                # 插入 tdr_detail2
                detail2_sql = text("""
                    INSERT INTO tdr_detail2 (
                        DAILY_NO, DAILY_SUB_NOS, DAILY_JOB_NOS, COCODE, EMPNO, SOP_CODE, STATUS, 
                        XUSER, XDATE, XTIME, ITEMDESC1, PROD_CATE, EXETIME, ESTIMATE, ATTITUDE, 
                        PROD_NO, SOLUT_SUBJ, SOLUT_STATUS, EMPNAME1, EMPNAME2, EMPNAME3, EMPNAME4, EMPNAME5, 
                        PPS_SERVECOCODE, PPS_EMPNO, PPS_COCODE, PPS_DEPTNO, MEMO_COLLECT, MEMO, 
                        PPS_EMPNAMEC, PLANNO, SOPNO
                    ) VALUES (
                        :daily_no, :daily_sub_nos, :daily_job_nos, :cocode, :empno, :sop_code, :status,
                        :xuser, :xdate, :xtime, :itemdesc1, :prod_cate, :exetime, :estimate, :attitude,
                        :prod_no, :solut_subj, :solut_status, :empname1, :empname2, :empname3, :empname4, :empname5,
                        :pps_servecocode, :pps_empno, :pps_cocode, :pps_deptno, :memo_collect, :memo,
                        :pps_empnamec, :planno, :sopno
                    )
                """)
                
                # 從 project 資料中取得相關資訊
                project = report.get('project', {})
                planno = project.get('planno', '')
                sopno = ''  # 需要從其他地方取得執行工作編號
                
                # 取得服務對象資訊 (如果有的話)
                service_cocode = None
                service_empno = None
                service_deptno = None
                service_empnamec = None
                
                if 'service_company_name' in report or 'service_target_name' in report:
                    # 這裡需要根據實際的資料結構來取得服務對象資訊
                    service_cocode = legacy_cocode  # 或其他邏輯
                    service_empno = None  # 需要從報告中取得
                    service_deptno = None  # 需要從報告中取得
                    service_empnamec = report.get('service_target_name', '')
                
                detail2_params = {
                    'daily_no': daily_no,
                    'daily_sub_nos': daily_sub_nos,
                    'daily_job_nos': 1,  # 固定1
                    'cocode': legacy_cocode,
                    'empno': getattr(employee, 'empno', ''),
                    'sop_code': report.get('work_item_name', ''),  # 工作項目(中文)
                    'status': 'N',  # 固定N
                    'xuser': getattr(employee, 'name', ''),  # 撰寫人姓名
                    'xdate': current_date,
                    'xtime': current_time,
                    'itemdesc1': '',  # 規格細項(文字) - 需要確認從哪裡取得
                    'prod_cate': 'PROD_CATE',  # 固定值或需要從其他地方取得
                    'exetime': report.get('total_execution_time_minutes', 0),  # 工時
                    'estimate': None,
                    'attitude': None,
                    'prod_no': None,
                    'solut_subj': None,
                    'solut_status': None,
                    'empname1': '0',  # 固定值
                    'empname2': None,
                    'empname3': None,
                    'empname4': None,
                    'empname5': None,
                    'pps_servecocode': service_cocode,  # 服務公司別
                    'pps_empno': service_empno,  # 服務對象工號
                    'pps_cocode': service_cocode,  # 服務對象公司別
                    'pps_deptno': service_deptno,  # 服務對象部門
                    'memo_collect': '1',  # 固定1
                    'memo': report.get('content', ''),  # 日報內文
                    'pps_empnamec': service_empnamec,  # 服務對象姓名
                    'planno': planno,  # 工作計畫編號
                    'sopno': sopno  # 執行工作編號
                }
                
                db.execute(detail2_sql, detail2_params)
                
                daily_sub_nos += 1
            
            # 提交交易
            db.commit()
            logger.info(f"Successfully submitted daily report {daily_no} to legacy database")
            
            return daily_no
            
        except Exception as e:
            logger.error(f"Error submitting daily report to legacy database: {str(e)}")
            db.rollback()
            raise
    
    @staticmethod
    def _generate_daily_no(db: Session, cocode: str, doc_date: str) -> int:
        """生成日報編號 - 返回數字格式"""
        try:
            # 查詢當天的最大日報編號
            sql = text("""
                SELECT MAX(daily_no) as max_daily_no
                FROM tdr_master 
                WHERE cocode = :cocode 
                AND doc_date = :doc_date
            """)
            
            result = db.execute(sql, {"cocode": cocode, "doc_date": doc_date}).fetchone()
            max_daily_no = result[0] if result and result[0] is not None else 0
            next_daily_no = max_daily_no + 1
            
            # 如果當天沒有記錄，從基數開始 (例如: 20250903001)
            if max_daily_no == 0:
                # 格式: YYYYMMDDNNN (NNN從001開始)
                base_no = int(f"{doc_date}001")
                return base_no
            else:
                return next_daily_no
            
        except Exception as e:
            logger.error(f"Error generating daily_no: {str(e)}")
            # 如果出錯，使用時間戳作為備用方案
            import time
            fallback_no = int(f"{doc_date}{int(time.time()) % 1000:03d}")
            return fallback_no
    
    @staticmethod
    def _get_supervisor_empno(db: Session, empno: str, cocode: str) -> Optional[str]:
        """取得員工的直屬主管工號"""
        try:
            # 這裡需要根據實際的組織架構表來查詢
            # 暫時返回 None，需要根據實際的資料表結構來實作
            return None
        except Exception as e:
            logger.error(f"Error getting supervisor empno: {str(e)}")
            return None