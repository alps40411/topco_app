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

async def check_database_integrity():
    """檢查資料庫完整性"""
    
    print("=== 檢查資料庫完整性 ===\n")
    
    target_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    TargetSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine, class_=AsyncSession)
    
    try:
        async with TargetSessionLocal() as target_db:
            # 1. 檢查員工表範圍
            print("1. 檢查員工表ID範圍:")
            result = await target_db.execute(text("""
                SELECT MIN(id) as min_id, MAX(id) as max_id, COUNT(*) as total_count
                FROM employees
            """))
            row = result.mappings().first()
            print(f"   員工ID範圍: {row['min_id']} - {row['max_id']}, 總數: {row['total_count']}")
            
            # 2. 檢查工作記錄表的員工ID
            print("\n2. 檢查工作記錄表員工ID:")
            result = await target_db.execute(text("""
                SELECT MIN(employee_id) as min_emp_id, MAX(employee_id) as max_emp_id, COUNT(*) as total_records,
                       COUNT(DISTINCT employee_id) as unique_employees
                FROM work_records
                WHERE employee_id IS NOT NULL
            """))
            row = result.mappings().first()
            if row['total_records'] > 0:
                print(f"   工作記錄員工ID範圍: {row['min_emp_id']} - {row['max_emp_id']}")
                print(f"   總記錄數: {row['total_records']}, 不重複員工數: {row['unique_employees']}")
            else:
                print("   工作記錄表中沒有數據")
            
            # 3. 檢查孤立的工作記錄
            print("\n3. 檢查孤立的工作記錄:")
            result = await target_db.execute(text("""
                SELECT wr.employee_id, COUNT(*) as record_count
                FROM work_records wr
                LEFT JOIN employees e ON wr.employee_id = e.id
                WHERE e.id IS NULL
                GROUP BY wr.employee_id
                ORDER BY wr.employee_id
            """))
            rows = result.mappings().all()
            
            if rows:
                print("   發現孤立的工作記錄:")
                for row in rows:
                    print(f"     員工ID {row['employee_id']}: {row['record_count']} 筆記錄")
            else:
                print("   沒有發現孤立的工作記錄")
            
            # 4. 檢查項目表的員工ID
            print("\n4. 檢查項目表員工ID:")
            result = await target_db.execute(text("""
                SELECT COUNT(*) as project_count
                FROM projects
            """))
            row = result.mappings().first()
            print(f"   項目總數: {row['project_count']}")
            
            # 5. 檢查用戶表與員工表的關聯
            print("\n5. 檢查用戶與員工關聯:")
            result = await target_db.execute(text("""
                SELECT COUNT(*) as user_count,
                       COUNT(employee_id) as users_with_employee
                FROM users
            """))
            row = result.mappings().first()
            print(f"   用戶總數: {row['user_count']}, 有員工關聯的用戶: {row['users_with_employee']}")
            
            # 6. 檢查是否有重複的員工工號
            print("\n6. 檢查重複的員工工號:")
            result = await target_db.execute(text("""
                SELECT empno, COUNT(*) as count
                FROM employees
                GROUP BY empno
                HAVING COUNT(*) > 1
                ORDER BY count DESC
            """))
            rows = result.mappings().all()
            
            if rows:
                print("   發現重複的工號:")
                for row in rows:
                    print(f"     工號 {row['empno']}: {row['count']} 筆記錄")
            else:
                print("   沒有發現重複的工號")
                
    except Exception as e:
        print(f"   查詢失敗: {e}")
    
    print("\n=== 檢查完成 ===")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_database_integrity())