# backend/reset_db.py

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings
from app.models import Base

async def reset_database():
    print("開始徹底重設資料庫...")
    # 建立一個獨立的引擎來執行操作
    engine = create_async_engine(settings.DATABASE_URL)

    async with engine.begin() as conn:
        print("步驟 1/3: 強制刪除 alembic_version 資料表...")
        # 使用 text() 來執行原生 SQL 指令，確保 alembic_version 表被刪除
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version;"))
        print(" -> alembic_version 已刪除。")

        print("步驟 2/3: 刪除所有應用程式資料表...")
        await conn.run_sync(Base.metadata.drop_all)
        print(" -> 所有應用程式資料表已成功刪除。")
        
        print("步驟 3/3: 根據最新模型，重新建立所有資料表...")
        await conn.run_sync(Base.metadata.create_all)
        print(" -> 已成功重新建立所有資料表！")
    
    # 關閉引擎連線
    await engine.dispose()
    print("資料庫徹底重設完成。")

if __name__ == "__main__":
    # 確保在 Windows 上 asyncio 可以正常運作
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(reset_database())