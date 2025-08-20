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

async def check_user_passwords():
    """檢查用戶密碼信息"""
    
    print("=== 檢查用戶密碼信息 ===\n")
    
    target_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    TargetSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine, class_=AsyncSession)
    
    try:
        async with TargetSessionLocal() as target_db:
            # 檢查幾個關鍵用戶
            result = await target_db.execute(text("""
                SELECT id, email, name, hashed_password, is_active
                FROM users
                WHERE id IN (32, 17, 18)
                ORDER BY id
            """))
            rows = result.mappings().all()
            
            for row in rows:
                print(f"用戶ID: {row['id']}")
                print(f"  郵箱: {row['email']}")
                print(f"  姓名: {row['name']}")
                print(f"  活躍: {row['is_active']}")
                print(f"  密碼哈希: {row['hashed_password'][:50]}...")
                print()
                
    except Exception as e:
        print(f"   查詢失敗: {e}")
    
    print("=== 檢查完成 ===")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_user_passwords())