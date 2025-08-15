# backend/create_user.py
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy import select

# --- 讓此獨立腳本可以載入 app 內的模組 ---
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.security import get_password_hash
from app.models import Employee, User

async def create_user(empno: str, email: str, password: str):
    """
    為指定的員工建立一個可以登入的使用者帳號。
    """
    db_url = settings.DATABASE_URL
    if not db_url:
        print("錯誤：找不到 DATABASE_URL 設定。請檢查您的 .env 檔案。 সন")
        return

    engine = create_async_engine(db_url, echo=False)
    AsyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

    async with AsyncSessionLocal() as db:
        # --- 1. 檢查員工是否存在 ---
        print(f"正在尋找員工編號為 {empno} 的員工...")
        stmt = select(Employee).where(Employee.empno == empno).options(selectinload(Employee.subordinates))
        result = await db.execute(stmt)
        employee = result.scalar_one_or_none()

        if not employee:
            print(f"錯誤：找不到員工編號為 {empno} 的員工。")
            return

        print(f"成功找到員工: {employee.name}")

        # --- 2. 檢查是否已關聯帳號 ---
        if employee.user_id:
            print(f"錯誤：該員工 {employee.name} ({empno}) 已經關聯了使用者帳號。")
            return

        # --- 3. 檢查 Email 是否已被使用 ---
        user_stmt = select(User).where(User.email == email)
        user_result = await db.execute(user_stmt)
        if user_result.scalar_one_or_none():
            print(f"錯誤：Email '{email}' 已經被其他使用者註冊。")
            return

        # --- 4. 建立新使用者 ---
        is_supervisor = bool(employee.subordinates)
        hashed_password = get_password_hash(password)

        new_user = User(
            email=email,
            name=employee.name,
            hashed_password=hashed_password,
            is_active=True,
            is_supervisor=is_supervisor
        )
        
        print(f"正在為 {employee.name} 建立使用者帳號...")
        print(f"  - Email (帳號): {email}")
        print(f"  - 姓名: {employee.name}")
        print(f"  - 是否為主管: {'是' if is_supervisor else '否'}")

        db.add(new_user)
        await db.flush() # 先 flush 以取得 new_user.id

        # --- 5. 關聯員工與使用者 ---
        employee.user = new_user
        
        await db.commit()
        print("\n使用者帳號成功建立並與員工資料關聯！")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("用法: python create_user.py <員工編號> <Email(登入帳號)> <密碼>")
        print("範例: python create_user.py 00034 supervisor@example.com your_password")
        sys.exit(1)

    empno_arg, email_arg, password_arg = sys.argv[1:4]
    asyncio.run(create_user(empno_arg, email_arg, password_arg))
