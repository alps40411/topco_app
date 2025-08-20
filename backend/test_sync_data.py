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

# 目標資料庫 (本地PostgreSQL) 的連線資訊
TARGET_DB_URL = settings.DATABASE_URL

async def create_test_data():
    """創建測試資料以驗證新的資料庫結構"""
    
    print("[INFO] 開始創建測試資料...")
    
    # 建立目標資料庫連線
    target_engine = create_async_engine(TARGET_DB_URL, echo=False)
    TargetSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine, class_=AsyncSession)

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
        
        # 清空員工對用戶的引用
        await target_db.execute(text("UPDATE employees SET user_id = NULL"))
        await target_db.execute(delete(User))
        await target_db.execute(delete(Employee))
        
        # 清空專案和部門
        await target_db.execute(delete(Project))
        await target_db.execute(delete(Department))
        await target_db.commit()
        
        # === 第1步：建立測試部門資料 ===
        print("\n[INFO] 建立測試部門資料...")
        test_departments = [
            {'deptno': '100', 'deptabbv': '數位發展部', 'g_deptno': '100'},
            {'deptno': '200', 'deptabbv': '資訊部', 'g_deptno': '200'},
            {'deptno': '300', 'deptabbv': '業務部', 'g_deptno': '300'}
        ]
        
        for dept_data in test_departments:
            dept = Department(**dept_data)
            target_db.add(dept)
        
        await target_db.commit()
        print(f"[SUCCESS] 建立了 {len(test_departments)} 個部門")

        # === 第2步：建立部門映射 ===
        print("[INFO] 建立部門映射...")
        department_map = {}
        dept_result = await target_db.execute(select(Department))
        departments = dept_result.scalars().all()
        for dept in departments:
            department_map[dept.deptno] = dept.id
        print(f"[SUCCESS] 建立了 {len(department_map)} 個部門映射")

        # === 第3步：建立測試員工資料 ===
        print("\n[INFO] 建立測試員工資料...")
        test_employees = [
            {
                'cocode': 'A',
                'empno': 'E001',
                'empnamec': '張三',
                'deptno': '100',
                'adm_rank': '8',
                'sop_role': 'PM',
                'dutyscript': '專案經理',
                'firstnamec': '三',
                'lastnamec': '張',
                'g_deptno': '100',
                'deptabbv': '數位發展部',
                'workcls': 'A',
                'department_id': department_map.get('100')
            },
            {
                'cocode': 'A',
                'empno': 'E002',
                'empnamec': '李四',
                'deptno': '100',
                'adm_rank': '5',
                'sop_role': 'DEV',
                'dutyscript': '軟體工程師',
                'firstnamec': '四',
                'lastnamec': '李',
                'g_deptno': '100',
                'deptabbv': '數位發展部',
                'workcls': 'A',
                'department_id': department_map.get('100')
            },
            {
                'cocode': 'A',
                'empno': 'E003',
                'empnamec': '王五',
                'deptno': '200',
                'adm_rank': '7',
                'sop_role': 'LEADER',
                'dutyscript': '資訊部主管',
                'firstnamec': '五',
                'lastnamec': '王',
                'g_deptno': '200',
                'deptabbv': '資訊部',
                'workcls': 'A',
                'department_id': department_map.get('200')
            }
        ]
        
        for emp_data in test_employees:
            employee = Employee(**emp_data)
            target_db.add(employee)
        
        await target_db.commit()
        print(f"[SUCCESS] 建立了 {len(test_employees)} 名員工")

        # === 第4步：建立測試主管關係 ===
        print("\n[INFO] 建立測試主管關係...")
        test_supervisors = [
            {'supervisor': 'E001', 'empno': 'E002'},  # E001是E002的主管
            {'supervisor': 'E003', 'empno': 'E001'},  # E003是E001的主管
        ]
        
        for sup_data in test_supervisors:
            supervisor_rel = Supervisor(**sup_data)
            target_db.add(supervisor_rel)
        
        await target_db.commit()
        print(f"[SUCCESS] 建立了 {len(test_supervisors)} 個主管關係")

        # === 第5步：建立測試專案 ===
        print("\n[INFO] 建立測試專案資料...")
        test_projects = [
            {
                'planno': 'PROJ001',
                'plan_subj_c': 'AI日誌報表統規劃',
                'pm_empno': 'E001',
                'is_active': True,
                'department_id': department_map.get('100')
            },
            {
                'planno': 'PROJ002',
                'plan_subj_c': '技術與Survey',
                'pm_empno': 'E001',
                'is_active': True,
                'department_id': department_map.get('100')
            },
            {
                'planno': 'PROJ003',
                'plan_subj_c': '系統維護',
                'pm_empno': 'E003',
                'is_active': True,
                'department_id': department_map.get('200')
            }
        ]
        
        for proj_data in test_projects:
            project = Project(**proj_data)
            target_db.add(project)
        
        await target_db.commit()
        print(f"[SUCCESS] 建立了 {len(test_projects)} 個專案")

        # === 第6步：建立測試專案成員關係 ===
        print("\n[INFO] 建立測試專案成員關係...")
        test_project_members = [
            {'planno': 'PROJ001', 'part_empno': 'E001'},
            {'planno': 'PROJ001', 'part_empno': 'E002'},
            {'planno': 'PROJ002', 'part_empno': 'E001'},
            {'planno': 'PROJ002', 'part_empno': 'E002'},
            {'planno': 'PROJ003', 'part_empno': 'E003'},
        ]
        
        for member_data in test_project_members:
            project_member = ProjectMember(**member_data)
            target_db.add(project_member)
        
        await target_db.commit()
        print(f"[SUCCESS] 建立了 {len(test_project_members)} 個專案成員關係")

    print(f"\n[SUCCESS] 測試資料創建完成！")
    print(f"總結：")
    print(f"  - 部門：{len(test_departments)} 個")
    print(f"  - 員工：{len(test_employees)} 名")
    print(f"  - 主管關係：{len(test_supervisors)} 個")
    print(f"  - 專案：{len(test_projects)} 個")
    print(f"  - 專案成員：{len(test_project_members)} 個")
    return True

if __name__ == "__main__":
    # 確保在 Windows 上 asyncio 可以正常運作
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    success = asyncio.run(create_test_data())
    if not success:
        sys.exit(1)