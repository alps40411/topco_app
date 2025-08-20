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

async def check_employee_32():
    """檢查員工 ID 32"""
    
    print("=== 檢查員工 ID 32 ===\n")
    
    target_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    TargetSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine, class_=AsyncSession)
    
    try:
        async with TargetSessionLocal() as target_db:
            # 檢查員工表中所有記錄
            print("1. 檢查員工表中所有記錄:")
            result = await target_db.execute(text("""
                SELECT id, empno, name, company_code
                FROM employees 
                ORDER BY id
            """))
            rows = result.mappings().all()
            
            for row in rows:
                print(f"   ID: {row['id']}, 工號: {row['empno']}, 姓名: {row['name']}, 公司別: {row['company_code']}")
            
            print(f"\n總共有 {len(rows)} 筆員工記錄\n")
            
            # 特別檢查 ID 32
            print("2. 檢查是否存在 ID 32:")
            result = await target_db.execute(text("""
                SELECT id, empno, name, company_code
                FROM employees 
                WHERE id = 32
            """))
            row = result.mappings().first()
            
            if row:
                print(f"   找到 ID 32: 工號 {row['empno']}, 姓名 {row['name']}, 公司別 {row['company_code']}")
            else:
                print("   沒有找到 ID 32 的員工記錄")
            
            # 檢查工作記錄表
            print("\n3. 檢查工作記錄表中的員工ID:")
            result = await target_db.execute(text("""
                SELECT DISTINCT employee_id
                FROM work_records 
                ORDER BY employee_id
            """))
            rows = result.mappings().all()
            
            employee_ids = [row['employee_id'] for row in rows]
            print(f"   工作記錄表中的員工ID: {employee_ids}")
            
            # 檢查哪些員工ID不存在於員工表中
            print("\n4. 檢查孤立的工作記錄:")
            result = await target_db.execute(text("""
                SELECT wr.id, wr.employee_id, wr.content, wr.created_at
                FROM work_records wr
                LEFT JOIN employees e ON wr.employee_id = e.id
                WHERE e.id IS NULL
                ORDER BY wr.employee_id
            """))
            rows = result.mappings().all()
            
            if rows:
                print("   發現孤立的工作記錄:")
                for row in rows:
                    print(f"     記錄ID: {row['id']}, 員工ID: {row['employee_id']}, 內容: {row['content'][:50]}...")
            else:
                print("   沒有發現孤立的工作記錄")
                
    except Exception as e:
        print(f"   查詢失敗: {e}")
    
    print("\n=== 檢查完成 ===")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_employee_32())