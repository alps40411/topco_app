# backend/delete_user.py
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy import select, delete

# --- 讓此獨立腳本可以載入 app 內的模組 ---
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.models import User, Employee

async def delete_user(email: str):
    """
    根據提供的 Email，從資料庫中刪除使用者帳號。
    """
    db_url = settings.DATABASE_URL
    if not db_url:
        print("錯誤：找不到 DATABASE_URL 設定。請檢查您的 .env 檔案。")
        return

    engine = create_async_engine(db_url, echo=False)
    AsyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

    async with AsyncSessionLocal() as db:
        # --- 1. 尋找使用者 ---
        print(f"正在尋找 Email 為 {email} 的使用者...")
        stmt = select(User).where(User.email == email).options(selectinload(User.employee))
        result = await db.execute(stmt)
        user_to_delete = result.scalar_one_or_none()

        if not user_to_delete:
            print(f"錯誤：找不到 Email 為 {email} 的使用者。")
            return

        print(f"成功找到使用者: {user_to_delete.name} (ID: {user_to_delete.id})")

        # --- 2. 解除與員工的關聯 (如果存在) ---
        if user_to_delete.employee:
            print(f"正在解除與員工 {user_to_delete.employee.name} ({user_to_delete.employee.empno}) 的關聯...")
            user_to_delete.employee.user_id = None
            await db.flush()

        # --- 3. 刪除使用者 ---
        print(f"正在刪除使用者 {email}...")
        await db.delete(user_to_delete)
        await db.commit()
        
        print(f"\n使用者 {email} 已成功刪除！")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python delete_user.py <要刪除的 Email>")
        print("範例: python delete_user.py supervisor@example.com")
        sys.exit(1)

    email_arg = sys.argv[1]
    asyncio.run(delete_user(email_arg))