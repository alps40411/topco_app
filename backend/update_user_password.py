#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text

# 讓此獨立腳本可以載入 app 內的模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.security import get_password_hash

async def update_user_password():
    """更新用戶密碼為 'password'"""
    
    print("=== 更新用戶密碼 ===\n")
    
    target_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    TargetSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine, class_=AsyncSession)
    
    try:
        async with TargetSessionLocal() as target_db:
            # 更新用戶ID 32的密碼
            new_password_hash = get_password_hash("05489")
            
            result = await target_db.execute(text("""
                UPDATE users 
                SET hashed_password = :password_hash
                WHERE id = 32
            """), {"password_hash": new_password_hash})
            
            await target_db.commit()
            
            print(f"已更新用戶ID 32的密碼為 '05489'")
            print(f"受影響的行數: {result.rowcount}")
                
    except Exception as e:
        print(f"   更新失敗: {e}")
    
    print("\n=== 更新完成 ===")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(update_user_password())