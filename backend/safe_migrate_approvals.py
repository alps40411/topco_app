#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
import datetime

# 讓此獨立腳本可以載入 app 內的模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.models import ReportApproval, ApprovalStatus

async def safe_migrate_approvals():
    """安全地遷移審核記錄"""
    
    print("=== 安全遷移審核記錄 ===\n")
    
    target_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    TargetSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine, class_=AsyncSession)
    
    try:
        async with TargetSessionLocal() as target_db:
            # 1. 先遷移已有評分的審核記錄
            print("1. 遷移已有評分的審核記錄...")
            result = await target_db.execute(text("""
                SELECT DISTINCT 
                    rc.report_id,
                    e.id as supervisor_id,
                    rc.rating,
                    rc.content as feedback,
                    rc.created_at
                FROM review_comments rc
                JOIN users u ON rc.user_id = u.id
                JOIN employees e ON u.id = e.user_id
                WHERE rc.rating IS NOT NULL AND rc.rating > 0
                ORDER BY rc.created_at
            """))
            old_approvals = result.mappings().all()
            
            print(f"   找到 {len(old_approvals)} 個需要遷移的審核記錄")
            
            migrated_count = 0
            for old_approval in old_approvals:
                # 檢查是否已存在
                existing_query = select(ReportApproval).where(
                    ReportApproval.report_id == old_approval['report_id'],
                    ReportApproval.supervisor_id == old_approval['supervisor_id']
                )
                existing_result = await target_db.execute(existing_query)
                if existing_result.scalar_one_or_none():
                    print(f"   跳過已存在的記錄: Report {old_approval['report_id']}, Supervisor {old_approval['supervisor_id']}")
                    continue
                
                # 處理時區
                approved_at = old_approval['created_at']
                if approved_at and approved_at.tzinfo:
                    approved_at = approved_at.replace(tzinfo=None)
                
                # 只要有評分就是approved
                status = ApprovalStatus.approved if old_approval['rating'] else ApprovalStatus.pending
                
                try:
                    new_approval = ReportApproval(
                        report_id=old_approval['report_id'],
                        supervisor_id=old_approval['supervisor_id'],
                        status=status,
                        rating=old_approval['rating'],
                        feedback=old_approval['feedback'],
                        approved_at=approved_at
                    )
                    target_db.add(new_approval)
                    await target_db.commit()
                    migrated_count += 1
                    print(f"   [OK] 遷移記錄: Report {old_approval['report_id']}, Supervisor {old_approval['supervisor_id']}, 狀態: {status.value}")
                except Exception as e:
                    await target_db.rollback()
                    print(f"   [ERROR] 失敗: Report {old_approval['report_id']}, Supervisor {old_approval['supervisor_id']}, 錯誤: {e}")
            
            print(f"\n   成功遷移 {migrated_count} 個審核記錄")
            
            # 2. 為每個報告創建所有必要的審核記錄
            print("\n2. 為每個報告創建所有必要的審核記錄...")
            
            # 獲取所有報告
            reports_result = await target_db.execute(text("""
                SELECT id, employee_id, date FROM daily_reports ORDER BY id
            """))
            reports = reports_result.mappings().all()
            
            created_count = 0
            for report in reports:
                # 獲取該員工的所有主管
                supervisors_result = await target_db.execute(text("""
                    SELECT supervisor_id FROM employee_supervisors 
                    WHERE employee_id = :employee_id
                """), {"employee_id": report['employee_id']})
                supervisor_ids = [row[0] for row in supervisors_result.fetchall()]
                
                for supervisor_id in supervisor_ids:
                    # 檢查是否已存在審核記錄
                    existing_query = select(ReportApproval).where(
                        ReportApproval.report_id == report['id'],
                        ReportApproval.supervisor_id == supervisor_id
                    )
                    existing_result = await target_db.execute(existing_query)
                    if existing_result.scalar_one_or_none():
                        continue
                    
                    # 創建pending記錄
                    try:
                        pending_approval = ReportApproval(
                            report_id=report['id'],
                            supervisor_id=supervisor_id,
                            status=ApprovalStatus.pending
                        )
                        target_db.add(pending_approval)
                        await target_db.commit()
                        created_count += 1
                        
                        if created_count <= 5:  # 只顯示前5個
                            print(f"   [OK] 創建pending記錄: Report {report['id']}, Supervisor {supervisor_id}")
                    except Exception as e:
                        await target_db.rollback()
                        print(f"   [ERROR] 創建失敗: Report {report['id']}, Supervisor {supervisor_id}, 錯誤: {e}")
            
            if created_count > 5:
                print(f"   ... 還有 {created_count - 5} 個記錄")
            
            print(f"\n   總計創建 {created_count} 個pending審核記錄")
            print(f"\n=== 遷移完成 ===")
            print(f"成功遷移 {migrated_count} 個舊審核記錄")
            print(f"創建 {created_count} 個pending審核記錄")
                
    except Exception as e:
        print(f"   遷移失敗: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== 安全遷移腳本執行完成 ===")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(safe_migrate_approvals())