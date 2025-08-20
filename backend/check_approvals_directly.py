#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text

# 讓此獨立腳本可以載入 app 內的模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

async def check_approvals_directly():
    """直接查詢ReportApproval表"""
    
    print("=== 直接查詢ReportApproval表 ===\n")
    
    target_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    TargetSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine, class_=AsyncSession)
    
    try:
        async with TargetSessionLocal() as target_db:
            # 直接查詢ReportApproval表
            result = await target_db.execute(text("""
                SELECT ra.id, ra.report_id, ra.supervisor_id, ra.status, 
                       ra.rating, ra.feedback, ra.approved_at
                FROM report_approvals ra
                ORDER BY ra.id
            """))
            rows = result.mappings().all()
            
            if rows:
                print(f"找到 {len(rows)} 個ReportApproval記錄:")
                for row in rows:
                    print(f"   ID: {row['id']}")
                    print(f"   Report ID: {row['report_id']}")
                    print(f"   Supervisor ID: {row['supervisor_id']}")
                    print(f"   狀態: {row['status']}")
                    print(f"   評分: {row['rating']}")
                    print(f"   意見: {row['feedback']}")
                    print(f"   審核時間: {row['approved_at']}")
                    print()
            else:
                print("沒有找到任何ReportApproval記錄")
                
    except Exception as e:
        print(f"   查詢失敗: {e}")
    
    print("=== 查詢完成 ===")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_approvals_directly())