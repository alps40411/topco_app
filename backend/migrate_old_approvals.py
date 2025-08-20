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

async def migrate_old_approvals():
    """將舊的ReviewComment審核記錄遷移到新的ReportApproval表"""
    
    print("=== 遷移舊審核記錄到ReportApproval表 ===\n")
    
    target_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    TargetSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine, class_=AsyncSession)
    
    try:
        async with TargetSessionLocal() as target_db:
            # 1. 查找所有有評分的ReviewComment記錄
            print("1. 查找需要遷移的ReviewComment記錄...")
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
            skipped_count = 0
            
            for old_approval in old_approvals:
                # 檢查是否已存在對應的ReportApproval記錄
                existing_query = select(ReportApproval).where(
                    ReportApproval.report_id == old_approval['report_id'],
                    ReportApproval.supervisor_id == old_approval['supervisor_id']
                )
                existing_result = await target_db.execute(existing_query)
                if existing_result.scalar_one_or_none():
                    print(f"   跳過已存在的記錄: Report {old_approval['report_id']}, Supervisor {old_approval['supervisor_id']}")
                    skipped_count += 1
                    continue
                
                # 只要有評分就是approved
                status = ApprovalStatus.approved if old_approval['rating'] else ApprovalStatus.pending

                # 處理時區問題
                approved_at = old_approval['created_at']
                if approved_at and approved_at.tzinfo:
                    approved_at = approved_at.replace(tzinfo=None)
                
                # 創建新的ReportApproval記錄
                new_approval = ReportApproval(
                    report_id=old_approval['report_id'],
                    supervisor_id=old_approval['supervisor_id'],
                    status=status,
                    rating=old_approval['rating'],
                    feedback=old_approval['feedback'],
                    approved_at=approved_at
                )
                
                target_db.add(new_approval)
                migrated_count += 1
                
                print(f"   遷移記錄: Report {old_approval['report_id']}, Supervisor {old_approval['supervisor_id']}, 評分: {old_approval['rating']}, 狀態: {status.value}")
            
            # 2. 為所有有審核記錄但缺少ReportApproval的報告創建pending記錄
            print("\n2. 為現有報告創建缺少的pending審核記錄...")
            
            # 獲取所有需要審核記錄的報告和主管組合
            result = await target_db.execute(text("""
                SELECT DISTINCT dr.id as report_id, es.supervisor_id
                FROM daily_reports dr
                JOIN employee_supervisors es ON dr.employee_id = es.employee_id
                LEFT JOIN report_approvals ra ON dr.id = ra.report_id AND es.supervisor_id = ra.supervisor_id
                WHERE ra.id IS NULL
                ORDER BY dr.id, es.supervisor_id
            """))
            missing_approvals = result.mappings().all()
            
            print(f"   找到 {len(missing_approvals)} 個缺少的審核記錄需要創建")
            
            created_count = 0
            for missing in missing_approvals:
                pending_approval = ReportApproval(
                    report_id=missing['report_id'],
                    supervisor_id=missing['supervisor_id'],
                    status=ApprovalStatus.pending
                )
                target_db.add(pending_approval)
                created_count += 1
                
                if created_count <= 10:  # 只顯示前10個
                    print(f"   創建pending記錄: Report {missing['report_id']}, Supervisor {missing['supervisor_id']}")
            
            if created_count > 10:
                print(f"   ... 還有 {created_count - 10} 個記錄")
            
            # 提交所有更改
            await target_db.commit()
            
            print(f"\n=== 遷移完成 ===")
            print(f"成功遷移 {migrated_count} 個舊審核記錄")
            print(f"跳過 {skipped_count} 個已存在記錄") 
            print(f"創建 {created_count} 個pending審核記錄")
            print(f"總計處理 {migrated_count + created_count} 個記錄")
                
    except Exception as e:
        print(f"   遷移失敗: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== 遷移腳本執行完成 ===")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(migrate_old_approvals())