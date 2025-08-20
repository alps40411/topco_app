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

async def check_user_employee_relationship():
    """檢查用戶與員工的關聯關係"""
    
    print("=== 檢查用戶與員工的關聯關係 ===\n")
    
    target_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    TargetSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine, class_=AsyncSession)
    
    try:
        async with TargetSessionLocal() as target_db:
            # 1. 檢查所有用戶
            print("1. 檢查所有用戶:")
            result = await target_db.execute(text("""
                SELECT id, email, name, is_active, is_supervisor
                FROM users
                ORDER BY id
            """))
            rows = result.mappings().all()
            
            for row in rows:
                print(f"   用戶ID: {row['id']}, 郵箱: {row['email']}, 姓名: {row['name']}, 活躍: {row['is_active']}, 主管: {row['is_supervisor']}")
            
            print(f"\n總共有 {len(rows)} 個用戶\n")
            
            # 2. 檢查用戶ID 32
            print("2. 檢查用戶ID 32:")
            result = await target_db.execute(text("""
                SELECT id, email, name, is_active, is_supervisor
                FROM users
                WHERE id = 32
            """))
            row = result.mappings().first()
            
            if row:
                print(f"   找到用戶ID 32: 郵箱 {row['email']}, 姓名 {row['name']}")
                
                # 檢查是否有對應的員工記錄
                result = await target_db.execute(text("""
                    SELECT id, empno, name, user_id
                    FROM employees
                    WHERE user_id = 32
                """))
                emp_row = result.mappings().first()
                
                if emp_row:
                    print(f"   對應員工: ID {emp_row['id']}, 工號 {emp_row['empno']}, 姓名 {emp_row['name']}")
                else:
                    print("   沒有找到對應的員工記錄")
            else:
                print("   沒有找到用戶ID 32")
            
            # 3. 檢查所有用戶與員工的關聯
            print("\n3. 檢查所有用戶與員工的關聯:")
            result = await target_db.execute(text("""
                SELECT u.id as user_id, u.email, u.name as user_name,
                       e.id as employee_id, e.empno, e.empnamec as employee_name
                FROM users u
                LEFT JOIN employees e ON u.id = e.user_id
                ORDER BY u.id
            """))
            rows = result.mappings().all()
            
            users_with_employees = 0
            for row in rows:
                if row['employee_id']:
                    print(f"   用戶 {row['user_id']} ({row['email']}) -> 員工 {row['employee_id']} ({row['empno']} - {row['employee_name']})")
                    users_with_employees += 1
                else:
                    print(f"   用戶 {row['user_id']} ({row['email']}) -> 沒有對應員工")
            
            print(f"\n   總計: {users_with_employees}/{len(rows)} 個用戶有對應的員工記錄")
            
            # 4. 檢查沒有用戶關聯的員工
            print("\n4. 檢查沒有用戶關聯的員工:")
            result = await target_db.execute(text("""
                SELECT COUNT(*) as count
                FROM employees
                WHERE user_id IS NULL
            """))
            row = result.mappings().first()
            print(f"   沒有用戶關聯的員工數量: {row['count']}")
                
    except Exception as e:
        print(f"   查詢失敗: {e}")
    
    print("\n=== 檢查完成 ===")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_user_employee_relationship())