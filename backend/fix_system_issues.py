#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
from sqlalchemy import select, delete, text, update
from sqlalchemy.orm import selectinload

# 讓此獨立腳本可以載入 app 內的模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionFactory
from app.models import Project, User, Employee, Department, Supervisor, ProjectMember

async def fix_system_issues():
    """
    修正系統的主要問題：
    1. 修正員工05489等人的is_supervisor權限（改為基於實際下屬判斷）
    2. 清空測試專案，只保留從原始資料庫搬遷的專案
    3. 修正員工的專案關聯
    """
    print("[INFO] 開始修正系統問題...")
    
    async with AsyncSessionFactory() as session:
        try:
            # === 問題1: 修正is_supervisor權限邏輯 ===
            print("\n[INFO] 修正is_supervisor權限...")
            
            # 獲取所有用戶
            users_result = await session.execute(
                select(User).options(selectinload(User.employee))
            )
            users = users_result.scalars().all()
            
            updated_count = 0
            for user in users:
                if not user.employee:
                    continue
                
                # 檢查該員工是否真的有下屬
                supervisor_relations = await session.execute(
                    select(Supervisor).where(Supervisor.supervisor == user.employee.empno)
                )
                has_subordinates = bool(supervisor_relations.scalars().first())
                
                # 更新is_supervisor狀態
                if user.is_supervisor != has_subordinates:
                    user.is_supervisor = has_subordinates
                    updated_count += 1
                    print(f"  更新 {user.employee.empnamec} ({user.employee.empno}): is_supervisor = {has_subordinates}")
            
            await session.commit()
            print(f"[SUCCESS] 更新了 {updated_count} 個用戶的主管權限")
            
            # === 問題2: 清空測試專案，保留原始專案 ===
            print("\n[INFO] 檢查專案資料...")
            
            # 檢查是否有PROJ_開頭的測試專案
            test_projects_result = await session.execute(
                select(Project).where(Project.planno.like('PROJ_%'))
            )
            test_projects = test_projects_result.scalars().all()
            
            if test_projects:
                print(f"[INFO] 找到 {len(test_projects)} 個測試專案，將清除...")
                
                # 先清除測試專案的成員關係
                for project in test_projects:
                    await session.execute(
                        delete(ProjectMember).where(ProjectMember.planno == project.planno)
                    )
                
                # 清除測試專案
                await session.execute(
                    delete(Project).where(Project.planno.like('PROJ_%'))
                )
                
                await session.commit()
                print(f"[SUCCESS] 清除了 {len(test_projects)} 個測試專案")
            else:
                print("[INFO] 沒有找到測試專案")
            
            # === 問題3: 檢查專案統計 ===
            print("\n[INFO] 檢查專案統計...")
            
            # 統計現有專案
            project_count_result = await session.execute(
                select(Project.id).where(Project.is_active == True)
            )
            active_projects = project_count_result.scalars().all()
            
            # 統計專案成員關係
            member_count_result = await session.execute(
                select(ProjectMember.id)
            )
            member_relations = member_count_result.scalars().all()
            
            print(f"[INFO] 當前狀態:")
            print(f"  - 活躍專案數量: {len(active_projects)}")
            print(f"  - 專案成員關係: {len(member_relations)}")
            
            # === 問題4: 檢查員工05489的狀態 ===
            print("\n[INFO] 檢查員工05489的最終狀態...")
            
            emp_result = await session.execute(
                select(Employee)
                .options(selectinload(Employee.user))
                .where(Employee.empno == '05489')
            )
            emp = emp_result.scalar_one_or_none()
            
            if emp and emp.user:
                # 檢查下屬數量
                subordinates_result = await session.execute(
                    select(Supervisor).where(Supervisor.supervisor == '05489')
                )
                subordinates = subordinates_result.scalars().all()
                
                # 檢查專案成員關係
                project_relations_result = await session.execute(
                    select(ProjectMember).where(ProjectMember.part_empno == '05489')
                )
                project_relations = project_relations_result.scalars().all()
                
                print(f"[INFO] 員工05489 ({emp.empnamec}) 的狀態:")
                print(f"  - is_supervisor: {emp.user.is_supervisor}")
                print(f"  - 下屬數量: {len(subordinates)}")
                print(f"  - 專案關聯數量: {len(project_relations)}")
                
                if len(subordinates) == 0 and emp.user.is_supervisor:
                    print("  [WARNING] 該員工被標記為主管但沒有下屬！")
                elif len(subordinates) > 0 and not emp.user.is_supervisor:
                    print("  [WARNING] 該員工有下屬但未被標記為主管！")
                else:
                    print("  [SUCCESS] 權限設置正確")
                    
            print(f"\n[SUCCESS] 系統問題修正完成！")

        except Exception as e:
            print(f"[ERROR] 修正失敗: {str(e)}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(fix_system_issues())