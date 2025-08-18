#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

# 讓此獨立腳本可以載入 app 內的模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionFactory
from app.core.security import get_password_hash
from app.models import Project, User, Employee, Department

async def seed_data():
    """
    僅為數位發展部填充專案和測試帳號。
    """
    print("[INFO] 開始填充數位發展部的初始資料...")
    
    async with AsyncSessionFactory() as session:
        try:
            # === 準備工作：清空舊的測試資料 ===
            print("\n[INFO] 清空舊的專案和測試用戶資料...")
            # 為避免誤刪，只刪除腳本創建的測試帳號
            await session.execute(delete(User).where(User.email.like('%@topco.com')))
            # 刪除所有專案以便重建
            await session.execute(delete(Project))
            await session.commit()
            print("[SUCCESS] 舊資料清理完畢。")

            # === 步驟 1：找到數位發展部 ===
            print("\n[INFO] 尋找數位發展部...")
            digital_dev_dept_result = await session.execute(
                select(Department).where(Department.dept_name.like('%數位發展%'))
            )
            digital_dev_dept = digital_dev_dept_result.scalar_one_or_none()
            
            if not digital_dev_dept:
                print("[ERROR] 找不到'數位發展部'，請先運行 `sync_company_a_data.py` 同步公司資料。" )
                return
            
            print(f"[SUCCESS] 找到數位發展部: {digital_dev_dept.dept_name} (ID: {digital_dev_dept.id})")

            # === 步驟 2：為數位發展部創建專案 ===
            print("\n[INFO] 創建數位發展部專案...")
            # 將通用專案也歸類至部門底下，方便管理
            digital_projects = [
                "AI日誌報表統規劃", "技術與Survey", "專案計畫", "分析工作",
                "日常業務處理", "會議與協調", "教育訓練", "其他工作項目"
            ]
            
            for project_name in digital_projects:
                project = Project(
                    name=project_name,
                    is_active=True,
                    department_id=digital_dev_dept.id # 全部歸屬數位發展部
                )
                session.add(project)
            
            await session.commit()
            print(f"[SUCCESS] 成功創建 {len(digital_projects)} 個數位發展部專案。")

            # === 步驟 3：收集需要創建帳號的員工及主管 ===
            print("\n[INFO] 收集數位發展部員工及其各級主管...")
            
            digital_employees_result = await session.execute(
                select(Employee)
                .options(selectinload(Employee.supervisors)) # 預先載入主管
                .where(Employee.department_id == digital_dev_dept.id)
            )
            digital_employees = digital_employees_result.scalars().unique().all()
            
            personnel_to_check = set(digital_employees)
            supervisors_to_check = set()

            for emp in digital_employees:
                for supervisor in emp.supervisors:
                    supervisors_to_check.add(supervisor)
            
            personnel_to_check.update(supervisors_to_check)
            
            print(f"[INFO] 總共需要檢查/創建 {len(personnel_to_check)} 名人員 (含員工及主管) 的帳號。")

            # === 步驟 4：為所有相關人員創建 User 帳號 ===
            print("\n[INFO] 開始創建 User 帳號...")
            created_accounts_count = 0
            for person in personnel_to_check:
                if person.user_id:
                    continue

                email = f"{person.empno}@topco.com"
                
                existing_user_res = await session.execute(select(User).where(User.email == email))
                if existing_user_res.scalar_one_or_none():
                    continue

                is_supervisor_flag = bool(
                    (person.admin_rank and person.admin_rank.isdigit() and int(person.admin_rank) >= 7)
                    or (person in supervisors_to_check)
                )

                user = User(
                    email=email,
                    name=person.name or f"員工{person.empno}",
                    hashed_password=get_password_hash(person.empno),
                    is_active=True,
                    is_supervisor=is_supervisor_flag
                )
                session.add(user)
                created_accounts_count += 1
                print(f"[INFO] 準備為 {person.name} ({person.empno}) 創建帳號: {email}")

            if created_accounts_count > 0:
                await session.commit()
            print(f"[SUCCESS] 成功創建 {created_accounts_count} 個新帳號。")

            # === 步驟 5：將 User 帳號關聯回 Employee ===
            print("\n[INFO] 將 User 帳號關聯至員工資料...")
            linked_accounts_count = 0
            for person in personnel_to_check:
                if not person.user_id:
                    email = f"{person.empno}@topco.com"
                    user_res = await session.execute(select(User).where(User.email == email))
                    user = user_res.scalar_one_or_none()
                    if user:
                        person.user_id = user.id
                        linked_accounts_count += 1
            
            if linked_accounts_count > 0:
                await session.commit()
            print(f"[SUCCESS] 成功關聯 {linked_accounts_count} 個帳號。")

            # === 步驟 6：最終驗證 ===
            print("\n[INFO] 最終驗證...")
            users_res = await session.execute(select(User).where(User.email.like('%@topco.com')))
            users = users_res.scalars().all()
            print(f"[SUCCESS] 驗證完畢。資料庫中現在有 {len(users)} 個測試帳號。")
            print("\n[SUCCESS] 數位發展部初始資料設置完成！")

        except Exception as e:
            print(f"[ERROR] 資料填充失敗: {str(e)}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_data())
