# backend/seed_db.py

import asyncio
from app.core.database import AsyncSessionFactory, engine
from app.models import Base, Project, User, Employee # 引入需要的模型
from app.services import user_service    # 引入 user_service
from app.schemas.user import UserCreate  # 引入 UserCreate schema

async def seed_data():
    print("開始填充初始資料...")
    async with engine.begin() as conn:
        # 先刪除所有舊資料表
        await conn.run_sync(Base.metadata.drop_all)
        # 重新建立所有資料表
        await conn.run_sync(Base.metadata.create_all)
        print("資料庫已重設並重新建立。")

    async with AsyncSessionFactory() as session:
        # --- 建立一個一般員工使用者 ---
        user_email = "employee@example.com"
        user = await user_service.get_user_by_email(session, email=user_email)
        if not user:
            user_in = UserCreate(
                email=user_email, 
                password="StrongPassword123",
                name="測試員工",
                department="技術部",
                is_supervisor=False
            )
            await user_service.create_user(session, obj_in=user_in)
            print(f"- 已建立預設員工: {user_email}")

        # --- 建立一個主管使用者 ---
        supervisor_email = "supervisor@example.com"
        supervisor = await user_service.get_user_by_email(session, email=supervisor_email)
        if not supervisor:
            supervisor_in = UserCreate(
                email=supervisor_email,
                password="StrongPassword123",
                name="測試主管",
                department="管理部",
                is_supervisor=True
            )
            await user_service.create_user(session, obj_in=supervisor_in)
            print(f"- 已建立預設主管: {supervisor_email}")


        # --- 建立預設的工作計畫 ---
        projects_to_create = [
            "AI日誌報表統規劃", "技術與Survey", "專案計畫", "分析工作",
            "目標設定", "資料研究", "週計畫制定", "檢視與修正"
        ]
        
        for project_name in projects_to_create:
            result = await session.execute(
                Project.__table__.select().where(Project.name == project_name)
            )
            if result.first() is None:
                session.add(Project(name=project_name, is_active=True))
        
        print(f"- 已建立 {len(projects_to_create)} 個預設工作計畫。")

        await session.commit()
    print("初始資料填充完畢！")

if __name__ == "__main__":
    # 確保在 Windows 上 asyncio 可以正常運作
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_data())