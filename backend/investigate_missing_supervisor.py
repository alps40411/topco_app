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

async def investigate_missing_supervisor():
    """調查缺失的主管 00003"""
    
    print("=== 調查缺失的主管 00003 ===\n")
    
    # === 1. 檢查原始資料庫中的 00003 員工資料 ===
    print("1. 檢查原始資料庫中的員工 00003:")
    source_db_url = f"postgresql+asyncpg://{SOURCE_DB_CONFIG['user']}:{SOURCE_DB_CONFIG['password']}@{SOURCE_DB_CONFIG['host']}:{SOURCE_DB_CONFIG['port']}/{SOURCE_DB_CONFIG['dbname']}"
    source_engine = create_async_engine(source_db_url, echo=False)
    SourceSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=source_engine, class_=AsyncSession)
    
    try:
        async with SourceSessionLocal() as source_db:
            result = await source_db.execute(text("""
                SELECT DISTINCT empno, empnamec, deptno, deptnamec, dclass, xlevel, adm_rank, quitdate, cocode
                FROM jps.groupfoodchn 
                WHERE empno = '00003'
                ORDER BY empno
            """))
            rows = result.mappings().all()
            
            if rows:
                for row in rows:
                    print(f"   工號: {row['empno']}")
                    print(f"   姓名: {row['empnamec']}")
                    print(f"   部門編號: {row['deptno']}")
                    print(f"   部門名稱: {row['deptnamec']}")
                    print(f"   職級: {row['dclass']}")
                    print(f"   層級: {row['xlevel']}")
                    print(f"   管理職級: {row['adm_rank']}")
                    print(f"   離職日期: {row['quitdate']}")
                    print(f"   公司別: {row['cocode']}")
            else:
                print("   在原始資料庫中找不到員工 00003")
                
    except Exception as e:
        print(f"   查詢原始資料庫失敗: {e}")
    
    print()
    
    # === 2. 檢查新資料庫中是否有 00003 ===
    print("2. 檢查新資料庫中是否有員工 00003:")
    target_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    TargetSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine, class_=AsyncSession)
    
    try:
        async with TargetSessionLocal() as target_db:
            result = await target_db.execute(text("""
                SELECT empno, name, department_no, department_name, dclass, xlevel, admin_rank, quit_date, company_code
                FROM employees 
                WHERE empno = '00003'
            """))
            rows = result.mappings().all()
            
            if rows:
                for row in rows:
                    print(f"   工號: {row['empno']}")
                    print(f"   姓名: {row['name']}")
                    print(f"   部門編號: {row['department_no']}")
                    print(f"   部門名稱: {row['department_name']}")
                    print(f"   職級: {row['dclass']}")
                    print(f"   層級: {row['xlevel']}")
                    print(f"   管理職級: {row['admin_rank']}")
                    print(f"   離職日期: {row['quit_date']}")
                    print(f"   公司別: {row['company_code']}")
            else:
                print("   在新資料庫中找不到員工 00003")
                
    except Exception as e:
        print(f"   查詢新資料庫失敗: {e}")
    
    print()
    
    # === 3. 檢查原始資料庫中所有 05489 的主管關係記錄 ===
    print("3. 檢查原始資料庫中員工 05489 的所有主管關係:")
    try:
        async with SourceSessionLocal() as source_db:
            result = await source_db.execute(text("""
                SELECT empno, empnamec, supervisor, suname, sudept, surank, deptno, deptnamec, cocode
                FROM jps.groupfoodchn 
                WHERE empno = '05489'
                ORDER BY supervisor
            """))
            rows = result.mappings().all()
            
            for i, row in enumerate(rows, 1):
                print(f"   記錄 {i}:")
                print(f"     員工: {row['empno']} - {row['empnamec']}")
                print(f"     主管: {row['supervisor']} - {row['suname']}")
                print(f"     主管部門: {row['sudept']}")
                print(f"     主管職級: {row['surank']}")
                print(f"     員工部門: {row['deptno']} - {row['deptnamec']}")
                print(f"     公司別: {row['cocode']}")
                print()
                
    except Exception as e:
        print(f"   查詢失敗: {e}")
    
    print("=== 調查完成 ===")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(investigate_missing_supervisor())