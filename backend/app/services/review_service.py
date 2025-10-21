# backend/app/services/review_service.py

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
import json

from ..schemas.review_schemas import ReviewSubmitRequest
from .wfinbox_service import WfinboxService

logger = logging.getLogger(__name__)

class ReviewService:
    """評分和回復服務"""
    
    @staticmethod
    async def submit_review(
        db: Session,
        daily_no: str,
        reviewer_empno: str,
        reviewer_empname: str,
        reviewer_cocode: str,
        score: Optional[int] = None,
        reply_memo: Optional[str] = None,
        to_users: List[str] = [],
        forward_users: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """提交主管審閱（包含評分和回復）"""
        
        try:
            # 取得當前日期時間
            now = datetime.now()
            current_date = now.strftime('%Y%m%d')
            current_time = now.strftime('%H:%M:%S')
            
            # 取得原始日報作者工號和基本資訊（包含 doc_date）
            report_author_sql = text("""
                SELECT empno, empnamec, sop_desc_c, cocode, doc_date
                FROM jps.tdr_master
                WHERE daily_no = :daily_no
            """)
            report_result = db.execute(report_author_sql, {"daily_no": daily_no}).fetchone()

            if not report_result:
                raise ValueError(f"日報 {daily_no} 不存在")

            report_empno, report_empname, sop_desc_c, report_cocode, doc_date = report_result
            
            # 取得planno (從 tdr_detail2 中取得第一筆記錄的planno)
            planno_sql = text("""
                SELECT planno FROM jps.tdr_detail2 
                WHERE daily_no = :daily_no 
                ORDER BY daily_sub_nos LIMIT 1
            """)
            planno_result = db.execute(planno_sql, {"daily_no": daily_no}).fetchone()
            planno = planno_result[0] if planno_result else None
            
            # 1. 取得下一個回應編號
            max_reply_sql = text("""
                SELECT COALESCE(MAX(reply_nos), 0) + 1 
                FROM jps.tdr_reply 
                WHERE daily_no = :daily_no
            """)
            reply_nos = db.execute(max_reply_sql, {"daily_no": daily_no}).scalar()
            
            # 2. 寫入回應 (如果有回應內容)
            if reply_memo:
                reply_sql = text("""
                    INSERT INTO jps.tdr_reply (
                        daily_no, reply_nos, empno, memo, xuser, xdate, xtime, memo1, from_where
                    ) VALUES (
                        :daily_no, :reply_nos, :empno, :memo, :xuser, :xdate, :xtime, '', 0
                    )
                """)

                db.execute(reply_sql, {
                    "daily_no": daily_no,
                    "reply_nos": reply_nos,
                    "empno": reviewer_empno,
                    "memo": reply_memo,
                    "xuser": reviewer_empname,
                    "xdate": current_date,
                    "xtime": current_time
                })

                # 檢查是否為罐頭訊息，如果不是則記錄為特殊訊息
                is_general_sql = text("""
                    SELECT COUNT(*) FROM jps.TDR_REPLY_GENERAL_COMMENT
                    WHERE memo = :memo
                """)
                is_general_count = db.execute(is_general_sql, {"memo": reply_memo}).scalar()

                # 如果不是罐頭訊息，則插入特殊訊息記錄
                if is_general_count == 0:
                    insert_special_sql = text("""
                        INSERT INTO jps.TDR_REPLY_SPECIAL_COMMENT
                        (DAILY_NO, DOC_DATE, EMPNO, UPDATETIME)
                        VALUES (:daily_no, :doc_date, :empno, SYSDATE)
                    """)

                    db.execute(insert_special_sql, {
                        "daily_no": daily_no,
                        "doc_date": doc_date,
                        "empno": report_empno
                    })
            
            # 3. 回應紀錄 - 取得日報內容項目數量
            detail_count_sql = text("""
                SELECT COUNT(*) FROM jps.tdr_detail2 WHERE daily_no = :daily_no
            """)
            detail_count = db.execute(detail_count_sql, {"daily_no": daily_no}).scalar()
            
            # 為每個日報內容項目創建回應記錄
            for i in range(1, detail_count + 1):
                reply_detail_sql = text("""
                    INSERT INTO jps.tdr_reply_detail (
                        daily_no, daily_sub_nos, reply_nos, xuser, xdate, xtime
                    ) VALUES (
                        :daily_no, :daily_sub_nos, :reply_nos, :xuser, :xdate, :xtime
                    )
                """)
                
                db.execute(reply_detail_sql, {
                    "daily_no": daily_no,
                    "daily_sub_nos": i,
                    "reply_nos": reply_nos,
                    "xuser": reviewer_empname,
                    "xdate": current_date,
                    "xtime": current_time
                })
            
            # 4. 跨群轉寄 (如果有轉寄用戶)
            if forward_users:
                for fw_user in forward_users:
                    msg_send_sql = text("""
                        INSERT INTO jps.tdr_msg_send_log (
                            daily_no, reply_nos, from_empno, to_empno, xuser, xdate, xtime
                        ) VALUES (
                            :daily_no, :reply_nos, :from_empno, :to_empno, :xuser, :xdate, :xtime
                        )
                    """)
                    
                    db.execute(msg_send_sql, {
                        "daily_no": daily_no,
                        "reply_nos": reply_nos,
                        "from_empno": reviewer_empno,
                        "to_empno": fw_user,
                        "xuser": reviewer_empname,
                        "xdate": current_date,
                        "xtime": current_time
                    })
            
            # 5. 評分 (如果有評分)
            if score is not None:
                score_sql = text("""
                    INSERT INTO jps.tdr_score (
                        daily_no, reply_nos, cocode, reply_empno, score, bonus, xuser, xdate, xtime
                    ) VALUES (
                        :daily_no, :reply_nos, :cocode, :reply_empno, :score, 0, :xuser, :xdate, :xtime
                    )
                """)
                
                db.execute(score_sql, {
                    "daily_no": daily_no,
                    "reply_nos": reply_nos,
                    "cocode": reviewer_cocode,
                    "reply_empno": reviewer_empno,
                    "score": score,
                    "xuser": reviewer_empname,
                    "xdate": current_date,
                    "xtime": current_time
                })
            
            # 6. 更新已回應狀態
            update_master_sql = text("""
                UPDATE jps.tdr_master 
                SET reply_status = 'Y' 
                WHERE daily_no = :daily_no
            """)
            db.execute(update_master_sql, {"daily_no": daily_no})
            
            # 7. 處理高階長官特殊邏輯
            ReviewService._handle_boss_review(
                db, daily_no, reviewer_empno, reviewer_empname, 
                forward_users is not None and len(forward_users) > 0
            )
            
            # 8. 更新 wfinbox 狀態（透過 CommonAPI）
            try:
                await WfinboxService.update_status_to_read(
                    empno=reviewer_empno,
                    serino=daily_no
                )
            except Exception as e:
                # wfinbox 更新失敗不影響主流程
                logger.warning(f"Wfinbox 更新失敗（不影響主流程）: {str(e)}")

            # 9. 工作流通知 - 建構通知用戶列表
            # 建立要通知的用戶列表（不包含原作者，因為原作者不需要收到自己日報的通知）
            ls_total_user = []

            # 加入回應的用戶(toUser) - 這些是要收到通知的目標用戶
            if to_users:
                for to_user in to_users:
                    if to_user not in ls_total_user:
                        ls_total_user.append(to_user)

            # 加入跨轉寄的用戶(fwUser) - 這些也是要收到通知的用戶
            if forward_users:
                for fw_user in forward_users:
                    if fw_user not in ls_total_user:
                        ls_total_user.append(fw_user)

            # 建立訊息佇列 - 為每個要通知的用戶建立EAI記錄
            ls_mq = []
            for i in range(len(ls_total_user)):  # 從0開始，通知所有目標用戶
                # 取得 EAI 序號
                eai_seq_sql = text("SELECT nextval('jps.seq_eai_source')")
                eai_seq = db.execute(eai_seq_sql).scalar()

                ls_mq.append({
                    "fwUser": ls_total_user[i],
                    "eai": eai_seq
                })

            # 建立工作流通知
            for mq_item in ls_mq:
                try:
                    subject = f"{reviewer_empname}回應日報({sop_desc_c})"
                    href = f"%2fMyReportAI%2f%3fcocode%3d{report_cocode}%26daily_no%3d{daily_no}%26replyid%3d{reply_nos}%26status%3dP"
                    doc_body = f"Source=JpsReportDailyReply^|Action=toWkf^|cocode=toWkf^|xuser={reviewer_empno}^|doc_date={current_date[:4]}/{current_date[4:6]}/{current_date[6:8]}^|doc_time={current_time}^|touser={reviewer_empno}^|href={href}^|Key={daily_no}^|Subject={subject}"

                    eai_sql = text("""
                        INSERT INTO jps.eai_source (
                            eai_seq, source, subject, cocode, xuser, touser, doc_date, doc_time,
                            key, action, doc_bady, status
                        ) VALUES (
                            :eai_seq, 'JpsReportDailyReply', :subject, :cocode, :xuser, :touser,
                            :doc_date, :doc_time, :key, 'toWkf', :doc_bady, 'N'
                        )
                    """)

                    db.execute(eai_sql, {
                        "eai_seq": mq_item["eai"],
                        "subject": subject,
                        "cocode": reviewer_cocode,
                        "xuser": reviewer_empno,
                        "touser": mq_item["fwUser"],
                        "doc_date": f"{current_date[:4]}/{current_date[4:6]}/{current_date[6:8]}",
                        "doc_time": current_time,
                        "key": daily_no,
                        "doc_bady": doc_body
                    })

                except Exception as eai_error:
                    logger.warning(f"EAI 通知插入失敗: touser={mq_item['fwUser']}, error={str(eai_error)}")
                    # 不要因為EAI失敗而中斷整個流程，繼續處理

            db.commit()
            logger.info(f"成功提交審閱 daily_no={daily_no}, reply_nos={reply_nos}")
            
            return {
                "success": True,
                "message": "審閱提交成功",
                "reply_nos": reply_nos,
                "daily_no": daily_no
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"提交審閱失敗: {str(e)}")
            raise
    
    @staticmethod
    def _handle_boss_review(
        db: Session, 
        daily_no: str, 
        reviewer_empno: str, 
        reviewer_empname: str, 
        has_forwarded: bool
    ):
        """處理高階長官審閱邏輯"""
        
        # 高階長官工號
        boss_empnos = ["00002", "02970", "Z0005"]
        
        if reviewer_empno not in boss_empnos:
            return
        
        try:
            # 檢查是否已有回應記錄
            check_sql = text("""
                SELECT case_reply FROM jps.tdr_boss_daily 
                WHERE daily_no = :daily_no
            """)
            existing_reply = db.execute(check_sql, {"daily_no": daily_no}).fetchone()
            
            if not existing_reply or not existing_reply[0]:
                # 第一次審閱
                case_reply = '<a title="自己已審閱" class="myheart"></a>'
            else:
                # 已有人審閱過
                case_reply = '<a title="所有人已審閱" class="hearts"></a>'
            
            update_boss_sql = text("""
                UPDATE jps.tdr_boss_daily 
                SET case_reply = :case_reply
                """ + (", isforwarded = 'true', case_forward = '<a title=\"已轉寄\" class=\"turnout\"></a>'" if has_forwarded else "") + """
                WHERE daily_no = :daily_no
            """)
            
            db.execute(update_boss_sql, {
                "daily_no": daily_no,
                "case_reply": case_reply
            })
            
        except Exception as e:
            logger.warning(f"處理高階長官審閱邏輯失敗: {str(e)}")
    
    @staticmethod
    def get_review_status(db: Session, daily_no: str, reviewer_empno: str) -> Dict[str, Any]:
        """取得審閱狀態"""
        
        try:
            # 檢查是否已評分
            score_check_sql = text("""
                SELECT COUNT(*) FROM jps.tdr_score 
                WHERE daily_no = :daily_no AND reply_empno = :reply_empno
            """)
            has_scored = db.execute(score_check_sql, {
                "daily_no": daily_no, 
                "reply_empno": reviewer_empno
            }).scalar() > 0
            
            # 檢查是否已回應
            reply_check_sql = text("""
                SELECT COUNT(*) FROM jps.tdr_reply 
                WHERE daily_no = :daily_no AND empno = :empno
            """)
            has_replied = db.execute(reply_check_sql, {
                "daily_no": daily_no, 
                "empno": reviewer_empno
            }).scalar() > 0
            
            # 取得所有回應記錄
            replies_sql = text("""
                SELECT r.daily_no, r.reply_nos, r.empno, r.xuser, r.memo, r.xdate, r.xtime, s.score
                FROM jps.tdr_reply r
                LEFT JOIN jps.tdr_score s ON r.daily_no = s.daily_no AND r.reply_nos = s.reply_nos
                WHERE r.daily_no = :daily_no
                ORDER BY r.reply_nos DESC
            """)
            
            reply_results = db.execute(replies_sql, {"daily_no": daily_no}).fetchall()
            
            reply_records = []
            for row in reply_results:
                reply_records.append({
                    "daily_no": row[0],
                    "reply_nos": row[1],
                    "empno": row[2],
                    "empname": row[3],
                    "memo": row[4],
                    "reply_date": row[5],
                    "reply_time": row[6],
                    "score": row[7]
                })
            
            return {
                "daily_no": daily_no,
                "has_replied": has_replied,
                "has_scored": has_scored,
                "reply_records": reply_records
            }

        except Exception as e:
            logger.error(f"取得審閱狀態失敗: {str(e)}")
            raise

    @staticmethod
    async def acknowledge_report(
        db: Session,
        daily_no: str,
        user_empno: str,
        user_empname: str,
        user_cocode: str
    ) -> Dict[str, Any]:
        """確認已讀日報並更新信箱狀態"""

        try:
            # 驗證日報是否存在
            report_check_sql = text("""
                SELECT empno, empnamec, cocode
                FROM jps.tdr_master
                WHERE daily_no = :daily_no
            """)
            report_result = db.execute(report_check_sql, {"daily_no": daily_no}).fetchone()

            if not report_result:
                raise ValueError(f"日報 {daily_no} 不存在")

            # 更新 wfinbox 狀態（透過 CommonAPI）
            try:
                await WfinboxService.update_status_to_read(
                    empno=user_empno,
                    serino=daily_no
                )
            except Exception as e:
                logger.warning(f"Wfinbox 更新失敗（不影響主流程）: {str(e)}")

            db.commit()
            logger.info(f"成功確認日報 daily_no={daily_no}, user_empno={user_empno}")

            return {
                "success": True,
                "message": "已確認閱讀",
                "daily_no": daily_no
            }

        except Exception as e:
            db.rollback()
            logger.error(f"確認日報失敗: {str(e)}")
            raise