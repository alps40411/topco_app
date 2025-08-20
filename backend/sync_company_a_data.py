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
    Employee, Department, Supervisor, Project, ProjectMember,
    DailyReport, WorkRecord, FileAttachment,
    User, ReviewComment, ReportApproval
)

# 來源資料庫 (公司PostgreSQL) 的連線資訊
SOURCE_DB_CONFIG = {
    'user': settings.SOURCE_DB_USER,
    'password': settings.SOURCE_DB_PASSWORD,
    'host': '10.129.7.28',
    'port': 5444,
    'dbname': 'myrpt'
}

# 目標資料庫 (本地PostgreSQL) 的連線資訊
TARGET_DB_URL = settings.DATABASE_URL

def to_str(value):
    """安全地將任何值轉換為字串，處理 None 的情況"""
    if value is None:
        return None
    return str(value).strip() if str(value).strip() else None

async def sync_company_a_data():
    """
    基於四個核心查詢同步公司別A的完整資料
    
    查詢1：員工主檔
    查詢2：員工主管層級關係  
    查詢3：專案主檔
    查詢4：員工專案參與關係
    """
    
    print("[INFO] 開始同步公司別A的完整員工資料...")
    
    # 建立來源資料庫連線
    source_db_url = f"postgresql+asyncpg://{SOURCE_DB_CONFIG['user']}:{SOURCE_DB_CONFIG['password']}@{SOURCE_DB_CONFIG['host']}:{SOURCE_DB_CONFIG['port']}/{SOURCE_DB_CONFIG['dbname']}"
    source_engine = create_async_engine(source_db_url, echo=False)
    SourceSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=source_engine, class_=AsyncSession)

    # 建立目標資料庫連線
    target_engine = create_async_engine(TARGET_DB_URL, echo=False)
    TargetSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine, class_=AsyncSession)

    # === 查詢1：員工主檔 (Employees Master) ===
    print("[INFO] 執行查詢1：員工主檔...")
    employees_data = []
    try:
        async with SourceSessionLocal() as source_db:
            result = await source_db.execute(text("""
                SELECT a.cocode, a.empno, a.empnamec, a.deptno, a.adm_rank, a.sop_role, 
                       a.dutyscript, a.firstnamec, a.lastnamec, b.g_deptno, a.tam_pass, 
                       b.deptabbv, a.workcls
                FROM jps.dcd003$master a, jps.dcd002$master b
                WHERE a.cocode='A' AND a.cocode=b.cocode AND a.deptno=b.deptno
            """))
            employees_data = result.mappings().all()
            print(f"[SUCCESS] 查詢1完成，讀取 {len(employees_data)} 筆員工記錄")
    except Exception as e:
        print(f"[ERROR] 查詢1失敗: {e}")
        return False

    # === 查詢2：員工主管層級關係 (Employee-Supervisor Relationship) ===
    print("[INFO] 執行查詢2：員工主管層級關係...")
    supervisor_data = []
    try:
        async with SourceSessionLocal() as source_db:
            result = await source_db.execute(text("""
                SELECT supervisor, empno
                FROM jps.groupfoodchn
                WHERE cocode = 'A'
            """))
            supervisor_data = result.mappings().all()
            print(f"[SUCCESS] 查詢2完成，讀取 {len(supervisor_data)} 筆主管關係記錄")
    except Exception as e:
        print(f"[ERROR] 查詢2失敗: {e}")
        return False

    # === 查詢3：專案主檔 (Projects Master) ===
    print("[INFO] 執行查詢3：專案主檔...")
    projects_data = []
    try:
        async with SourceSessionLocal() as source_db:
            result = await source_db.execute(text("""
                SELECT DISTINCT planno, plan_subj_c, pm_empno
                FROM jps.tjp_master
                WHERE cocode = 'A' AND pm_empno IS NOT NULL
            """))
            projects_data = result.mappings().all()
            print(f"[SUCCESS] 查詢3完成，讀取 {len(projects_data)} 筆專案記錄")
    except Exception as e:
        print(f"[ERROR] 查詢3失敗: {e}")
        return False

    # === 查詢4：員工專案參與關係 (Employee-Project Partnership) ===
    print("[INFO] 執行查詢4：員工專案參與關係...")
    project_members_data = []
    try:
        async with SourceSessionLocal() as source_db:
            result = await source_db.execute(text("""
                SELECT planno, part_empno
                FROM jps.tjp_partner
                WHERE cocode_g = 'A'
            """))
            project_members_data = result.mappings().all()
            print(f"[SUCCESS] 查詢4完成，讀取 {len(project_members_data)} 筆專案成員記錄")
    except Exception as e:
        print(f"[ERROR] 查詢4失敗: {e}")
        return False

    # === 開始同步到目標資料庫 ===
    async with TargetSessionLocal() as target_db:
        print("\n[INFO] 清空現有資料...")
        
        # 先清空所有相關的資料（避免外鍵約束問題）
        await target_db.execute(delete(ReviewComment))
        await target_db.execute(delete(FileAttachment))
        await target_db.execute(delete(WorkRecord))
        await target_db.execute(delete(DailyReport))
        await target_db.execute(delete(ReportApproval))
        
        # 清空新的資料表
        await target_db.execute(delete(ProjectMember))
        await target_db.execute(delete(Supervisor))
        
        # 清空專案（先清空專案，避免外鍵約束）
        await target_db.execute(delete(Project))
        
        # 清空員工對用戶的引用
        await target_db.execute(text("UPDATE employees SET user_id = NULL WHERE user_id IS NOT NULL"))
        await target_db.execute(delete(User))
        await target_db.execute(delete(Employee))
        
        # 清空部門
        await target_db.execute(delete(Department))
        await target_db.commit()
        
        # === 第1步：建立部門資料表 ===
        print("\n[INFO] 建立部門資料...")
        unique_departments = {}
        
        for row in employees_data:
            deptno = to_str(row.get('deptno'))
            deptabbv = to_str(row.get('deptabbv'))
            g_deptno = to_str(row.get('g_deptno'))
            
            if deptno and deptabbv:
                unique_departments[deptno] = {
                    'deptno': deptno,
                    'deptabbv': deptabbv,
                    'g_deptno': g_deptno
                }
        
        for dept_data in unique_departments.values():
            dept = Department(**dept_data)
            target_db.add(dept)
        
        await target_db.commit()
        print(f"[SUCCESS] 建立了 {len(unique_departments)} 個部門")

        # === 第2步：建立部門映射 ===
        print("[INFO] 建立部門映射...")
        department_map = {}
        dept_result = await target_db.execute(select(Department))
        departments = dept_result.scalars().all()
        for dept in departments:
            department_map[dept.deptno] = dept.id
        print(f"[SUCCESS] 建立了 {len(department_map)} 個部門映射")

        # === 第3步：建立員工資料表 ===
        print("\n[INFO] 建立員工資料...")
        for row in employees_data:
            deptno = to_str(row.get('deptno'))
            department_id = department_map.get(deptno) if deptno else None
            
            employee_data = {
                'cocode': to_str(row.get('cocode', 'A')),
                'empno': to_str(row.get('empno')),
                'empnamec': to_str(row.get('empnamec')),
                'deptno': deptno,
                'adm_rank': to_str(row.get('adm_rank')),
                'sop_role': to_str(row.get('sop_role')),
                'dutyscript': to_str(row.get('dutyscript')),
                'firstnamec': to_str(row.get('firstnamec')),
                'lastnamec': to_str(row.get('lastnamec')),
                'g_deptno': to_str(row.get('g_deptno')),
                'tam_pass': to_str(row.get('tam_pass')),
                'deptabbv': to_str(row.get('deptabbv')),
                'workcls': to_str(row.get('workcls')),
                'department_id': department_id
            }
            
            employee = Employee(**employee_data)
            target_db.add(employee)
        
        await target_db.commit()
        print(f"[SUCCESS] 建立了 {len(employees_data)} 名員工")

        # === 第4步：建立員工編號集合 ===
        print("\n[INFO] 建立員工編號集合...")
        employee_empnos = set()
        emp_result = await target_db.execute(select(Employee.empno))
        for emp_row in emp_result:
            employee_empnos.add(emp_row[0])
        print(f"[SUCCESS] 員工編號集合包含 {len(employee_empnos)} 個員工")

        # === 第5步：建立主管關係表 ===
        print("\n[INFO] 建立主管關係...")
        supervisor_count = 0
        skipped_count = 0
        for row in supervisor_data:
            supervisor_empno = to_str(row.get('supervisor'))
            empno = to_str(row.get('empno'))
            
            if supervisor_empno and empno:
                # 檢查主管和員工都存在於員工表中
                if supervisor_empno in employee_empnos and empno in employee_empnos:
                    supervisor_rel = Supervisor(
                        supervisor=supervisor_empno,
                        empno=empno
                    )
                    target_db.add(supervisor_rel)
                    supervisor_count += 1
                else:
                    skipped_count += 1
        
        await target_db.commit()
        print(f"[SUCCESS] 建立了 {supervisor_count} 個主管關係，跳過了 {skipped_count} 個無效關係")

        # === 第6步：建立專案表 ===
        print("\n[INFO] 建立專案資料...")
        project_count = 0
        project_skipped = 0
        for row in projects_data:
            planno = to_str(row.get('planno'))
            plan_subj_c = to_str(row.get('plan_subj_c'))
            pm_empno = to_str(row.get('pm_empno'))
            
            if planno and plan_subj_c and pm_empno:
                # 檢查專案經理是否存在於員工表中
                if pm_empno in employee_empnos:
                    project = Project(
                        planno=planno,
                        plan_subj_c=plan_subj_c,
                        pm_empno=pm_empno,
                        is_active=True
                    )
                    target_db.add(project)
                    project_count += 1
                else:
                    project_skipped += 1
        
        await target_db.commit()
        print(f"[SUCCESS] 建立了 {project_count} 個專案，跳過了 {project_skipped} 個無效專案")

        # === 第7步：建立專案編號集合 ===
        print("\n[INFO] 建立專案編號集合...")
        project_plannos = set()
        project_result = await target_db.execute(select(Project.planno))
        for project_row in project_result:
            project_plannos.add(project_row[0])
        print(f"[SUCCESS] 專案編號集合包含 {len(project_plannos)} 個專案")

        # === 第8步：建立專案成員表 ===
        print("\n[INFO] 建立專案成員關係...")
        member_count = 0
        member_skipped = 0
        for row in project_members_data:
            planno = to_str(row.get('planno'))
            part_empno = to_str(row.get('part_empno'))
            
            if planno and part_empno:
                # 檢查專案編號和員工編號是否都存在
                if planno in project_plannos and part_empno in employee_empnos:
                    project_member = ProjectMember(
                        planno=planno,
                        part_empno=part_empno
                    )
                    target_db.add(project_member)
                    member_count += 1
                else:
                    member_skipped += 1
        
        await target_db.commit()
        print(f"[SUCCESS] 建立了 {member_count} 個專案成員關係，跳過了 {member_skipped} 個無效關係")

    print(f"\n[SUCCESS] 公司別A資料同步完成！")
    print(f"總結：")
    print(f"  - 部門：{len(unique_departments)} 個")
    print(f"  - 員工：{len(employees_data)} 名")
    print(f"  - 主管關係：{supervisor_count} 個 (跳過 {skipped_count} 個)")
    print(f"  - 專案：{project_count} 個 (跳過 {project_skipped} 個)")
    print(f"  - 專案成員：{member_count} 個 (跳過 {member_skipped} 個)")
    return True

if __name__ == "__main__":
    # 確保在 Windows 上 asyncio 可以正常運作
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    success = asyncio.run(sync_company_a_data())
    if not success:
        sys.exit(1)