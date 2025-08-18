#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# 讓此獨立腳本可以載入 app 內的模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionFactory
from app.core.security import get_password_hash
from app.models import Project, User, Employee, Department
from app.models.employee import employee_supervisors

async def seed_data():
    print("[INFO] 開始填充數位發展部的初始資料...")
    
    async with AsyncSessionFactory() as session:
        try:
            # === 第一步：檢查現有資料 ===
            print("[INFO] 檢查現有資料狀態...")
            
            # 統計現有資料
            emp_count = await session.execute(select(Employee).where(Employee.company_code == 'A'))
            employee_count = len(emp_count.scalars().all())
            
            dept_count = await session.execute(select(Department))
            department_count = len(dept_count.scalars().all())
            
            print(f"[INFO] 現有公司別A員工: {employee_count} 名")
            print(f"[INFO] 現有部門: {department_count} 個")
            
            if employee_count == 0:
                print("[WARNING] 沒有找到公司別A的員工資料，請先運行同步腳本")
                return
            
            # === 第二步：找到數位發展部並創建專案 ===
            print("\n[INFO] 尋找數位發展部...")
            
            # 找到數位發展部
            digital_dev_dept_result = await session.execute(
                select(Department).where(
                    Department.dept_name.like('%數位發展%')
                )
            )
            digital_dev_dept = digital_dev_dept_result.scalar_one_or_none()
            
            if not digital_dev_dept:
                print("[ERROR] 找不到數位發展部，請確認資料庫中存在數位發展部")
                return
            
            print(f"[SUCCESS] 找到數位發展部: {digital_dev_dept.dept_name} (ID: {digital_dev_dept.id})")
            
            # 為數位發展部創建專屬專案
            digital_projects = [
                "AI日誌報表統規劃",
                "技術與Survey", 
                "專案計畫",
                "分析工作"
            ]
            
            dept_projects_created = 0
            for project_name in digital_projects:
                result = await session.execute(
                    select(Project).where(Project.name == project_name)
                )
                if not result.scalar_one_or_none():
                    project = Project(
                        name=project_name,
                        is_active=True,
                        department_id=digital_dev_dept.id
                    )
                    session.add(project)
                    dept_projects_created += 1
                    print(f"[SUCCESS] 創建數位發展部專案: {project_name}")
            
            # === 第三步：創建通用專案 ===
            print("\n[INFO] 創建通用專案...")
            
            general_projects = [
                "日常業務處理",
                "會議與協調", 
                "教育訓練",
                "其他工作項目"
            ]
            
            general_projects_created = 0
            for project_name in general_projects:
                result = await session.execute(
                    select(Project).where(Project.name == project_name)
                )
                if not result.scalar_one_or_none():
                    project = Project(
                        name=project_name,
                        is_active=True,
                        department_id=None  # 通用專案
                    )
                    session.add(project)
                    general_projects_created += 1
            
            await session.commit()
            print(f"[SUCCESS] 創建了 {dept_projects_created} 個數位發展部專案")
            print(f"[SUCCESS] 創建了 {general_projects_created} 個通用專案")
            
            # === 第四步：為數位發展部員工及其上級創建測試帳號 ===
            print("\n[INFO] 為數位發展部員工創建測試帳號...")
            
            # 獲取數位發展部的員工
            digital_employees_result = await session.execute(
                select(Employee).where(Employee.department_id == digital_dev_dept.id)
            )
            digital_employees = digital_employees_result.scalars().all()
            
            print(f"[INFO] 找到數位發展部員工: {len(digital_employees)} 名")
            
            created_accounts = 0
            supervisor_empnos = set()  # 記錄需要創建帳號的上級員工編號
            
            # 首先為數位發展部員工創建帳號，並收集其上級
            for employee in digital_employees:
                if employee.user_id is None:  # 還沒有帳號
                    email = f"{employee.empno}@topco.com"
                    
                    # 檢查Email是否已存在
                    existing_user = await session.execute(
                        select(User).where(User.email == email)
                    )
                    if not existing_user.scalar_one_or_none():
                        # 判斷是否為主管
                        is_supervisor = (
                            employee.admin_rank and 
                            employee.admin_rank.isdigit() and 
                            int(employee.admin_rank) >= 7
                        )
                        
                        user = User(
                            email=email,
                            name=employee.name or f"員工{employee.empno}",
                            hashed_password=get_password_hash(employee.empno),
                            is_active=True,
                            is_supervisor=is_supervisor
                        )
                        session.add(user)
                        await session.flush()
                        
                        # 關聯員工與用戶
                        employee.user = user
                        created_accounts += 1
                        print(f"[SUCCESS] 創建數位發展部員工帳號: {email} -> {employee.name}")
                
                # 收集該員工的上級(從多對多關係表)
                supervisors_result = await session.execute(
                    select(Employee).join(
                        employee_supervisors,
                        Employee.id == employee_supervisors.c.supervisor_id
                    ).where(
                        employee_supervisors.c.employee_id == employee.id
                    )
                )
                supervisors = supervisors_result.scalars().all()
                for supervisor in supervisors:
                    supervisor_empnos.add(supervisor.empno)
            
            # 為收集到的上級創建帳號
            print(f"\n[INFO] 為數位發展部員工的上級創建帳號... (共 {len(supervisor_empnos)} 名上級)")
            
            for supervisor_empno in supervisor_empnos:
                # 查找上級員工
                supervisor_result = await session.execute(
                    select(Employee).where(Employee.empno == supervisor_empno)
                )
                supervisor = supervisor_result.scalar_one_or_none()
                
                if supervisor and supervisor.user_id is None:
                    email = f"{supervisor.empno}@topco.com"
                    
                    # 檢查Email是否已存在
                    existing_user = await session.execute(
                        select(User).where(User.email == email)
                    )
                    if not existing_user.scalar_one_or_none():
                        user = User(
                            email=email,
                            name=supervisor.name or f"主管{supervisor.empno}",
                            hashed_password=get_password_hash(supervisor.empno),
                            is_active=True,
                            is_supervisor=True  # 上級通常都是主管
                        )
                        session.add(user)
                        await session.flush()
                        
                        # 關聯員工與用戶
                        supervisor.user = user
                        created_accounts += 1
                        print(f"[SUCCESS] 創建上級帳號: {email} -> {supervisor.name} ({supervisor.department_name})")
            
            await session.commit()
            print(f"\n[SUCCESS] 總共創建了 {created_accounts} 個測試帳號")
            
            # === 第五步：驗證設置 ===
            print("\n[INFO] 驗證設置結果...")
            
            # 檢查專案數量
            projects_result = await session.execute(select(Project))
            projects = projects_result.scalars().all()
            dept_projects = [p for p in projects if p.department_id == digital_dev_dept.id]
            general_projects = [p for p in projects if p.department_id is None]
            
            print(f"[INFO] 專案統計:")
            print(f"  - 數位發展部專案: {len(dept_projects)} 個")
            print(f"  - 通用專案: {len(general_projects)} 個")
            print(f"  - 總計: {len(projects)} 個專案")
            
            # 檢查測試帳號
            users_result = await session.execute(
                select(User.email, User.name, User.is_supervisor).where(
                    User.email.like('%@topco.com')
                )
            )
            accounts = users_result.all()
            
            print(f"\n[SUCCESS] 可用測試帳號 ({len(accounts)} 個):")
            # 先顯示數位發展部員工
            digital_users = []
            supervisor_users = []
            
            for email, name, is_supervisor in accounts:
                empno = email.split('@')[0]
                
                # 檢查是否為數位發展部員工
                emp_check = await session.execute(
                    select(Employee).where(
                        Employee.empno == empno,
                        Employee.department_id == digital_dev_dept.id
                    )
                )
                if emp_check.scalar_one_or_none():
                    digital_users.append((email, name, is_supervisor, empno))
                else:
                    supervisor_users.append((email, name, is_supervisor, empno))
            
            print("  數位發展部員工:")
            for email, name, is_supervisor, empno in digital_users:
                role = "主管" if is_supervisor else "員工"
                print(f"    - {role}: {email} / 密碼: {empno} ({name})")
            
            if supervisor_users:
                print("  上級主管:")
                for email, name, is_supervisor, empno in supervisor_users:
                    print(f"    - 主管: {email} / 密碼: {empno} ({name})")
            
            # 系統統計
            print(f"\n[SUCCESS] 系統統計:")
            print(f"  - 數位發展部員工數: {len(digital_employees)}")
            print(f"  - 測試帳號數: {len(accounts)}")
            print(f"  - 數位發展部專案數: {len(dept_projects)}")
            print(f"  - 通用專案數: {len(general_projects)}")
            
            print("\n[SUCCESS] 數位發展部初始資料設置完成！")
            
        except Exception as e:
            print(f"[ERROR] 資料填充失敗: {str(e)}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise

if __name__ == "__main__":
    # 確保在 Windows 上 asyncio 可以正常運作
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_data())