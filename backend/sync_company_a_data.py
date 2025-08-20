#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text, insert, delete
from datetime import datetime, date
import sys
import os

# 讓此獨立腳本可以載入 app 內的模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.models import (
    Employee, Department, 
    EmployeeDepartmentHistory, 
    EmployeeSupervisorHistory,
    EmployeePositionHistory,
    DailyReport, WorkRecord, FileAttachment,
    User, Project, ReviewComment
)

# 來源資料庫 (公司PostgreSQL) 的連線資訊
SOURCE_DB_CONFIG = {
    'user': settings.SOURCE_DB_USER,
    'password': settings.SOURCE_DB_PASSWORD,
    'host': '10.129.7.28',
    'port': 5444,
    'dbname': 'myrpt'
}
SOURCE_TABLE = 'jps.groupfoodchn'

# 目標資料庫 (本地PostgreSQL) 的連線資訊
TARGET_DB_URL = settings.DATABASE_URL

def to_str(value):
    """安全地將任何值轉換為字串，處理 None 的情況"""
    if value is None:
        return None
    return str(value).strip() if str(value).strip() else None

def parse_date(date_str):
    """解析日期字串"""
    if not date_str or (isinstance(date_str, str) and date_str.lower() in ['null', '', '0']):
        return None
    if isinstance(date_str, datetime):
        return date_str.date()
    try:
        return datetime.strptime(str(date_str), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None

async def sync_company_a_data():
    """同步公司別A的完整資料，包括跨公司的主管關係"""
    
    print("[INFO] 開始同步公司別A的完整員工資料...")
    
    # 建立來源資料庫連線
    source_db_url = f"postgresql+asyncpg://{SOURCE_DB_CONFIG['user']}:{SOURCE_DB_CONFIG['password']}@{SOURCE_DB_CONFIG['host']}:{SOURCE_DB_CONFIG['port']}/{SOURCE_DB_CONFIG['dbname']}"
    source_engine = create_async_engine(source_db_url, echo=False)
    SourceSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=source_engine, class_=AsyncSession)

    # 建立目標資料庫連線
    target_engine = create_async_engine(TARGET_DB_URL, echo=False)
    TargetSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine, class_=AsyncSession)

    # === 第一步：讀取公司別A的資料 ===
    print("[INFO] 讀取公司別A的員工資料...")
    source_data = []
    try:
        async with SourceSessionLocal() as source_db:
            result = await source_db.execute(text(f"""
                SELECT DISTINCT 
                    supervisor, suname, sudept, surank, suquitdate, sugrp_empno,
                    empno, empnamec, deptno, dclass, xlevel, adm_rank, quitdate, 
                    deptnamec, deptabbv, g_deptno, grp_empno, cocode
                FROM {SOURCE_TABLE}
                WHERE empno IS NOT NULL 
                AND empno != ''
                AND cocode = 'A'
                ORDER BY empno
            """))
            source_data = result.mappings().all()
            print(f"[SUCCESS] 讀取 {len(source_data)} 筆公司別A員工記錄")
    except Exception as e:
        print(f"[ERROR] 讀取來源資料庫失敗: {e}")
        return False

    # === 第一步之二：讀取跨公司主管資料 ===
    print("[INFO] 讀取跨公司主管資料...")
    supervisor_empnos = set()
    for row in source_data:
        supervisor_empno = to_str(row.get('supervisor'))
        if supervisor_empno:
            supervisor_empnos.add(supervisor_empno)
    
    cross_company_supervisors = []
    if supervisor_empnos:
        try:
            async with SourceSessionLocal() as source_db:
                supervisor_list = "', '".join(supervisor_empnos)
                result = await source_db.execute(text(f"""
                    SELECT DISTINCT 
                        empno, empnamec, deptno, dclass, xlevel, adm_rank, quitdate, 
                        deptnamec, deptabbv, g_deptno, grp_empno, cocode
                    FROM {SOURCE_TABLE}
                    WHERE empno IN ('{supervisor_list}')
                    AND empno IS NOT NULL 
                    AND empno != ''
                    ORDER BY empno
                """))
                cross_company_supervisors = result.mappings().all()
                print(f"[SUCCESS] 讀取 {len(cross_company_supervisors)} 筆跨公司主管記錄")
        except Exception as e:
            print(f"[ERROR] 讀取跨公司主管資料失敗: {e}")
            return False

    # === 第二步：同步部門資料（包括跨公司主管的部門） ===
    print("\n[INFO] 同步部門資料...")
    unique_departments = {}
    
    # 處理公司A員工的部門
    for row in source_data:
        dept_no = to_str(row.get('deptno'))
        dept_name = to_str(row.get('deptnamec'))
        
        if dept_no and dept_name:
            if dept_no not in unique_departments:
                unique_departments[dept_no] = {
                    'dept_no': dept_no,
                    'dept_name': dept_name,
                    'dept_abbr': to_str(row.get('deptabbv')),
                    'group_dept_no': to_str(row.get('g_deptno')),
                    'company_code': to_str(row.get('cocode', 'A'))
                }
    
    # 處理跨公司主管的部門
    for row in cross_company_supervisors:
        dept_no = to_str(row.get('deptno'))
        dept_name = to_str(row.get('deptnamec'))
        
        if dept_no and dept_name:
            if dept_no not in unique_departments:
                unique_departments[dept_no] = {
                    'dept_no': dept_no,
                    'dept_name': dept_name,
                    'dept_abbr': to_str(row.get('deptabbv')),
                    'group_dept_no': to_str(row.get('g_deptno')),
                    'company_code': to_str(row.get('cocode'))
                }

    async with TargetSessionLocal() as target_db:
        # 先清空所有相關的資料（避免外鍵約束問題）
        print("[INFO] 清空現有資料...")
        await target_db.execute(delete(ReviewComment))
        await target_db.execute(delete(FileAttachment))
        await target_db.execute(delete(WorkRecord))
        await target_db.execute(delete(DailyReport))
        await target_db.execute(delete(EmployeeDepartmentHistory))
        await target_db.execute(delete(EmployeeSupervisorHistory))
        await target_db.execute(delete(EmployeePositionHistory))
        
        # 先清空員工對用戶的引用和主管關係，再清空用戶和員工
        await target_db.execute(text("UPDATE employees SET user_id = NULL, supervisor_id = NULL"))
        await target_db.execute(text("DELETE FROM employee_supervisors"))
        await target_db.execute(delete(User))
        await target_db.execute(delete(Employee))
        await target_db.commit()
        
        # 再清空現有專案和部門（重新開始）
        await target_db.execute(delete(Project))
        await target_db.execute(delete(Department))
        await target_db.commit()
        
        # 插入新部門
        for dept_data in unique_departments.values():
            dept = Department(**dept_data)
            target_db.add(dept)
        
        await target_db.commit()
        print(f"[SUCCESS] 同步了 {len(unique_departments)} 個部門")

    # === 第三步：建立部門映射 ===
    print("\n[INFO] 建立部門映射...")
    department_map = {}  # dept_name -> department.id
    async with TargetSessionLocal() as target_db:
        dept_result = await target_db.execute(select(Department))
        departments = dept_result.scalars().all()
        for dept in departments:
            department_map[dept.dept_name] = dept.id
            # 也建立 dept_no 到 id 的映射
            department_map[dept.dept_no] = dept.id
        print(f"[SUCCESS] 建立了 {len(department_map)} 個部門映射")

    # === 第四步：同步員工資料（包括跨公司主管） ===
    print("\n[INFO] 同步員工資料...")
    unique_employees = {}
    
    # 先處理公司A員工
    for row in source_data:
        empno = to_str(row.get('empno'))
        if empno and empno not in unique_employees:
            # 查找部門ID
            dept_name = to_str(row.get('deptnamec'))
            department_id = None
            if dept_name and dept_name in department_map:
                department_id = department_map[dept_name]
            
            unique_employees[empno] = {
                'empno': empno,
                'name': to_str(row.get('empnamec')) or f'員工{empno}',
                'department_id': department_id,
                'department_no': to_str(row.get('deptno')),
                'department_name': to_str(row.get('deptnamec')),
                'department_abbr': to_str(row.get('deptabbv')),
                'group_dept_no': to_str(row.get('g_deptno')),
                'dclass': to_str(row.get('dclass')),
                'xlevel': to_str(row.get('xlevel')),
                'admin_rank': to_str(row.get('adm_rank')),
                'company_code': to_str(row.get('cocode', 'A')),
                'group_emp_no': to_str(row.get('grp_empno')),
                'quit_date': parse_date(row.get('quitdate'))
            }
    
    # 再處理跨公司主管
    for row in cross_company_supervisors:
        empno = to_str(row.get('empno'))
        if empno and empno not in unique_employees:
            # 查找部門ID
            dept_name = to_str(row.get('deptnamec'))
            department_id = None
            if dept_name and dept_name in department_map:
                department_id = department_map[dept_name]
            
            unique_employees[empno] = {
                'empno': empno,
                'name': to_str(row.get('empnamec')) or f'主管{empno}',
                'department_id': department_id,
                'department_no': to_str(row.get('deptno')),
                'department_name': to_str(row.get('deptnamec')),
                'department_abbr': to_str(row.get('deptabbv')),
                'group_dept_no': to_str(row.get('g_deptno')),
                'dclass': to_str(row.get('dclass')),
                'xlevel': to_str(row.get('xlevel')),
                'admin_rank': to_str(row.get('adm_rank')),
                'company_code': to_str(row.get('cocode')),
                'group_emp_no': to_str(row.get('grp_empno')),
                'quit_date': parse_date(row.get('quitdate'))
            }

    async with TargetSessionLocal() as target_db:
        # 插入新員工
        for emp_data in unique_employees.values():
            employee = Employee(**emp_data)
            target_db.add(employee)
        
        await target_db.commit()
        company_a_count = sum(1 for emp in unique_employees.values() if emp.get('company_code') == 'A')
        cross_company_count = len(unique_employees) - company_a_count
        print(f"[SUCCESS] 同步了 {len(unique_employees)} 名員工 (公司A: {company_a_count}, 跨公司主管: {cross_company_count})")

    # === 第五步：建立員工映射並處理主管關係 ===
    print("\n[INFO] 處理主管關係...")
    
    async with TargetSessionLocal() as target_db:
        # 建立員工映射
        emp_result = await target_db.execute(select(Employee))
        employees = emp_result.scalars().all()
        employee_map = {emp.empno: emp for emp in employees}
        
        # 處理主管關係
        supervisor_relationships = []
        for row in source_data:
            empno = to_str(row.get('empno'))
            supervisor_empno = to_str(row.get('supervisor'))
            
            if empno and supervisor_empno and empno in employee_map and supervisor_empno in employee_map:
                employee = employee_map[empno]
                supervisor = employee_map[supervisor_empno]
                
                # 設置單一主管關係（向後兼容）
                if not employee.supervisor_id:
                    employee.supervisor_id = supervisor.id
                
                # 收集多對多關係
                relationship_key = (employee.id, supervisor.id)
                if relationship_key not in supervisor_relationships:
                    supervisor_relationships.append(relationship_key)
        
        # 插入多對多主管關係
        from app.models.employee import employee_supervisors
        for emp_id, sup_id in supervisor_relationships:
            await target_db.execute(
                insert(employee_supervisors).values(
                    employee_id=emp_id,
                    supervisor_id=sup_id
                )
            )
        
        await target_db.commit()
        print(f"[SUCCESS] 建立了 {len(supervisor_relationships)} 個主管關係")

    print(f"[SUCCESS] 公司別A資料同步完成！")
    return True

if __name__ == "__main__":
    # 確保在 Windows 上 asyncio 可以正常運作
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    success = asyncio.run(sync_company_a_data())
    if not success:
        sys.exit(1)