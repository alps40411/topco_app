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
from app.models import Employee, Department

async def comprehensive_test():
    """全面測試部門關係和員工主管關係"""
    
    print("=== 全面測試資料庫數據完整性 ===\n")
    
    target_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    TargetSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine, class_=AsyncSession)
    
    async with TargetSessionLocal() as target_db:
        # === 1. 測試部門統計 ===
        print("1. 部門統計:")
        dept_result = await target_db.execute(select(Department))
        departments = dept_result.scalars().all()
        
        company_stats = {}
        for dept in departments:
            company = dept.company_code or 'Unknown'
            if company not in company_stats:
                company_stats[company] = 0
            company_stats[company] += 1
        
        print(f"   總部門數: {len(departments)}")
        for company, count in sorted(company_stats.items()):
            print(f"   公司別 {company}: {count} 個部門")
        
        print()
        
        # === 2. 測試員工統計 ===
        print("2. 員工統計:")
        emp_result = await target_db.execute(select(Employee))
        employees = emp_result.scalars().all()
        
        company_emp_stats = {}
        for emp in employees:
            company = emp.company_code or 'Unknown'
            if company not in company_emp_stats:
                company_emp_stats[company] = 0
            company_emp_stats[company] += 1
        
        print(f"   總員工數: {len(employees)}")
        for company, count in sorted(company_emp_stats.items()):
            print(f"   公司別 {company}: {count} 名員工")
        
        print()
        
        # === 3. 測試員工05489的詳細資料 ===
        print("3. 員工 05489 詳細測試:")
        emp_05489_result = await target_db.execute(
            select(Employee).where(Employee.empno == '05489')
        )
        emp_05489 = emp_05489_result.scalar_one_or_none()
        
        if emp_05489:
            print(f"   工號: {emp_05489.empno}")
            print(f"   姓名: {emp_05489.name}")
            print(f"   部門: {emp_05489.department_name}")
            print(f"   公司別: {emp_05489.company_code}")
            
            # 測試多對多主管關係
            supervisors_result = await target_db.execute(text("""
                SELECT supervisors.empno, supervisors.name, supervisors.department_name, supervisors.company_code
                FROM employees e
                JOIN employee_supervisors es ON e.id = es.employee_id
                JOIN employees supervisors ON es.supervisor_id = supervisors.id
                WHERE e.empno = '05489'
                ORDER BY supervisors.empno
            """))
            supervisors = supervisors_result.mappings().all()
            
            print(f"   主管數量: {len(supervisors)}")
            for i, supervisor in enumerate(supervisors, 1):
                print(f"     主管 {i}: {supervisor['empno']} - {supervisor['name']} ({supervisor['department_name']}, 公司別: {supervisor['company_code']})")
        else:
            print("   [ERROR] 找不到員工 05489")
        
        print()
        
        # === 4. 測試跨公司主管關係 ===
        print("4. 跨公司主管關係測試:")
        cross_company_result = await target_db.execute(text("""
            SELECT 
                e.empno as employee_empno, 
                e.name as employee_name,
                e.company_code as employee_company,
                s.empno as supervisor_empno,
                s.name as supervisor_name,
                s.company_code as supervisor_company
            FROM employees e
            JOIN employee_supervisors es ON e.id = es.employee_id
            JOIN employees s ON es.supervisor_id = s.id
            WHERE e.company_code != s.company_code
            ORDER BY e.empno, s.empno
        """))
        cross_relations = cross_company_result.mappings().all()
        
        print(f"   跨公司主管關係數量: {len(cross_relations)}")
        for relation in cross_relations:
            print(f"     員工 {relation['employee_empno']} (公司{relation['employee_company']}) -> 主管 {relation['supervisor_empno']} (公司{relation['supervisor_company']})")
        
        print()
        
        # === 5. 測試數位發展部員工 ===
        print("5. 數位發展部員工測試:")
        digital_emp_result = await target_db.execute(text("""
            SELECT empno, name, department_name, company_code
            FROM employees 
            WHERE department_name LIKE '%數位發展%'
            ORDER BY empno
        """))
        digital_employees = digital_emp_result.mappings().all()
        
        print(f"   數位發展部員工數量: {len(digital_employees)}")
        for emp in digital_employees[:10]:  # 只顯示前10個
            print(f"     {emp['empno']} - {emp['name']} (公司別: {emp['company_code']})")
        if len(digital_employees) > 10:
            print(f"     ... 還有 {len(digital_employees) - 10} 名員工")
        
        print()
        
        # === 6. 測試數據一致性 ===
        print("6. 數據一致性檢查:")
        
        # 檢查孤立的員工（沒有部門的）
        orphan_emp_result = await target_db.execute(text("""
            SELECT COUNT(*) as count
            FROM employees 
            WHERE department_id IS NULL
        """))
        orphan_count = orphan_emp_result.scalar()
        print(f"   沒有部門的員工數: {orphan_count}")
        
        # 檢查沒有主管的A公司員工
        no_supervisor_result = await target_db.execute(text("""
            SELECT COUNT(*) as count
            FROM employees e
            LEFT JOIN employee_supervisors es ON e.id = es.employee_id
            WHERE e.company_code = 'A' AND es.employee_id IS NULL
        """))
        no_supervisor_count = no_supervisor_result.scalar()
        print(f"   A公司沒有主管的員工數: {no_supervisor_count}")
        
        # 檢查有帳號的員工數
        has_user_result = await target_db.execute(text("""
            SELECT COUNT(*) as count
            FROM employees 
            WHERE user_id IS NOT NULL
        """))
        has_user_count = has_user_result.scalar()
        print(f"   已建立帳號的員工數: {has_user_count}")
        
    print("\n=== 測試完成 ===")
    return True

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(comprehensive_test())