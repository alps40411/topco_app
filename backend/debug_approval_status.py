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

async def debug_approval_status():
    """調查審核狀態錯誤"""
    
    print("=== 調查審核狀態錯誤 ===\n")
    
    target_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    TargetSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine, class_=AsyncSession)
    
    try:
        async with TargetSessionLocal() as target_db:
            # 1. 檢查員工01446和05489的基本信息
            print("1. 檢查員工基本信息:")
            result = await target_db.execute(text("""
                SELECT id, empno, name, user_id
                FROM employees 
                WHERE empno IN ('01446', '05489')
                ORDER BY empno
            """))
            rows = result.mappings().all()
            
            employee_map = {}
            for row in rows:
                employee_map[row['empno']] = row
                print(f"   員工: {row['empno']} - {row['name']} (ID: {row['id']}, User ID: {row['user_id']})")
            
            # 2. 檢查ReviewComment表中的審核記錄
            print("\n2. 檢查ReviewComment表中的審核記錄:")
            result = await target_db.execute(text("""
                SELECT rc.id, rc.content, rc.rating, rc.created_at, 
                       rc.user_id, rc.report_id,
                       u.email, u.name as user_name,
                       e.empno as user_empno,
                       dr.employee_id as report_employee_id,
                       rep_emp.empno as report_employee_empno
                FROM review_comments rc
                JOIN users u ON rc.user_id = u.id
                LEFT JOIN employees e ON u.id = e.user_id
                JOIN daily_reports dr ON rc.report_id = dr.id
                LEFT JOIN employees rep_emp ON dr.employee_id = rep_emp.id
                WHERE e.empno IN ('01446', '05489') OR rep_emp.empno IN ('01446', '05489')
                ORDER BY rc.created_at DESC
            """))
            rows = result.mappings().all()
            
            for row in rows:
                print(f"   評論ID: {row['id']}")
                print(f"     評論者: {row['user_empno']} - {row['user_name']} (User ID: {row['user_id']})")
                print(f"     被評論員工: {row['report_employee_empno']}")
                print(f"     評分: {row['rating']}")
                print(f"     內容: {row['content']}")
                print(f"     時間: {row['created_at']}")
                print()
            
            # 3. 檢查ReportApproval表
            print("3. 檢查ReportApproval表:")
            result = await target_db.execute(text("""
                SELECT ra.id, ra.report_id, ra.supervisor_id, ra.status, 
                       ra.rating, ra.feedback, ra.approved_at,
                       sup.empno as supervisor_empno, sup.name as supervisor_name,
                       dr.employee_id as report_employee_id,
                       emp.empno as report_employee_empno
                FROM report_approvals ra
                JOIN employees sup ON ra.supervisor_id = sup.id
                JOIN daily_reports dr ON ra.report_id = dr.id
                JOIN employees emp ON dr.employee_id = emp.id
                WHERE sup.empno IN ('01446', '05489') OR emp.empno IN ('01446', '05489')
                ORDER BY ra.id
            """))
            rows = result.mappings().all()
            
            if rows:
                for row in rows:
                    print(f"   審核記錄ID: {row['id']}")
                    print(f"     主管: {row['supervisor_empno']} - {row['supervisor_name']} (ID: {row['supervisor_id']})")
                    print(f"     被審核員工: {row['report_employee_empno']} (ID: {row['report_employee_id']})")
                    print(f"     狀態: {row['status']}")
                    print(f"     評分: {row['rating']}")
                    print(f"     意見: {row['feedback']}")
                    print(f"     審核時間: {row['approved_at']}")
                    print()
            else:
                print("   沒有找到ReportApproval記錄")
            
            # 4. 檢查主管關係
            print("4. 檢查主管關係:")
            result = await target_db.execute(text("""
                SELECT es.employee_id, es.supervisor_id,
                       emp.empno as employee_empno, emp.name as employee_name,
                       sup.empno as supervisor_empno, sup.name as supervisor_name
                FROM employee_supervisors es
                JOIN employees emp ON es.employee_id = emp.id
                JOIN employees sup ON es.supervisor_id = sup.id
                WHERE emp.empno IN ('01446', '05489') OR sup.empno IN ('01446', '05489')
                ORDER BY emp.empno, sup.empno
            """))
            rows = result.mappings().all()
            
            for row in rows:
                print(f"   員工: {row['employee_empno']} - {row['employee_name']}")
                print(f"   主管: {row['supervisor_empno']} - {row['supervisor_name']}")
                print()
                
    except Exception as e:
        print(f"   查詢失敗: {e}")
    
    print("=== 調查完成 ===")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(debug_approval_status())