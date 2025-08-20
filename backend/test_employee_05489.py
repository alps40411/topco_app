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
from app.models import Employee

# 來源資料庫配置
SOURCE_DB_CONFIG = {
    'user': settings.SOURCE_DB_USER,
    'password': settings.SOURCE_DB_PASSWORD,
    'host': '10.129.7.28',
    'port': 5444,
    'dbname': 'myrpt'
}

async def test_employee_05489():
    """測試員工05489的主管關係"""
    
    print("=== 測試員工05489主管關係 ===\n")
    
    # === 1. 查詢原始資料庫 ===
    print("1. 查詢原始資料庫 (jps.groupfoodchn):")
    source_db_url = f"postgresql+asyncpg://{SOURCE_DB_CONFIG['user']}:{SOURCE_DB_CONFIG['password']}@{SOURCE_DB_CONFIG['host']}:{SOURCE_DB_CONFIG['port']}/{SOURCE_DB_CONFIG['dbname']}"
    source_engine = create_async_engine(source_db_url, echo=False)
    SourceSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=source_engine, class_=AsyncSession)
    
    original_supervisors = []
    try:
        async with SourceSessionLocal() as source_db:
            result = await source_db.execute(text("""
                SELECT supervisor, suname, sudept, surank, empno, empnamec, deptnamec
                FROM jps.groupfoodchn 
                WHERE empno = '05489' 
                AND supervisor IS NOT NULL 
                AND supervisor != ''
                ORDER BY supervisor
            """))
            rows = result.mappings().all()
            
            for row in rows:
                supervisor_info = {
                    'supervisor_empno': row['supervisor'],
                    'supervisor_name': row['suname'],
                    'supervisor_dept': row['sudept'],
                    'supervisor_rank': row['surank']
                }
                original_supervisors.append(supervisor_info)
                print(f"   主管工號: {row['supervisor']}, 姓名: {row['suname']}, 部門: {row['sudept']}, 職級: {row['surank']}")
                
        print(f"   原始資料庫共找到 {len(original_supervisors)} 位主管\n")
                
    except Exception as e:
        print(f"   查詢原始資料庫失敗: {e}\n")
    
    # === 2. 查詢新資料庫 ===
    print("2. 查詢新資料庫:")
    target_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    TargetSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine, class_=AsyncSession)
    
    new_supervisors = []
    try:
        async with TargetSessionLocal() as target_db:
            # 查詢多對多關係
            result = await target_db.execute(text("""
                SELECT supervisors.empno, supervisors.empnamec, supervisors.department_name, supervisors.admin_rank
                FROM employees e
                JOIN employee_supervisors es ON e.id = es.employee_id
                JOIN employees supervisors ON es.supervisor_id = supervisors.id
                WHERE e.empno = '05489'
                ORDER BY supervisors.empno
            """))
            rows = result.mappings().all()
            
            for row in rows:
                supervisor_info = {
                    'supervisor_empno': row['empno'],
                    'supervisor_name': row['name'],
                    'supervisor_dept': row['department_name'],
                    'supervisor_rank': row['admin_rank']
                }
                new_supervisors.append(supervisor_info)
                print(f"   主管工號: {row['empno']}, 姓名: {row['name']}, 部門: {row['department_name']}, 職級: {row['admin_rank']}")
                
        print(f"   新資料庫共找到 {len(new_supervisors)} 位主管\n")
                
    except Exception as e:
        print(f"   查詢新資料庫失敗: {e}\n")
    
    # === 3. 比較結果 ===
    print("3. 比較結果:")
    original_empnos = {sup['supervisor_empno'] for sup in original_supervisors}
    new_empnos = {sup['supervisor_empno'] for sup in new_supervisors}
    
    missing_in_new = original_empnos - new_empnos
    extra_in_new = new_empnos - original_empnos
    
    if missing_in_new:
        print(f"   [ERROR] Missing supervisors in new database: {missing_in_new}")
        for empno in missing_in_new:
            original_info = next(sup for sup in original_supervisors if sup['supervisor_empno'] == empno)
            print(f"      {empno}: {original_info['supervisor_name']} ({original_info['supervisor_dept']})")
    
    if extra_in_new:
        print(f"   [WARNING] Extra supervisors in new database: {extra_in_new}")
        
    if not missing_in_new and not extra_in_new:
        print("   [SUCCESS] Supervisor relationships match perfectly")
    
    print(f"\n=== 測試完成 ===")
    return original_supervisors, new_supervisors, missing_in_new

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_employee_05489())