# backend/reset_db.py

import asyncio
import sys
import os

# 讓此獨立腳本可以載入 app 內的模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import engine
# 根據您的指示，直接從 models 匯入 Base 來建立資料表
from app.models.base import Base
from sqlalchemy import text

async def reset_database():
    """
    重置資料庫：刪除所有資料表並根據當前 models 重新建立。
    """
    print("[INFO] 開始重置資料庫...")
    
    try:
        async with engine.begin() as conn:
            print("[INFO] 正在刪除所有現有資料表 (透過重建 public schema)...")
            
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            await conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
            await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
            print("[SUCCESS] 已清空 public schema。")

            print("[INFO] 正在根據當前 models 重新建立所有資料表...")
            await conn.run_sync(Base.metadata.create_all)
            print("[SUCCESS] 所有資料表已根據 models 重新建立。")
            
        print("[SUCCESS] 資料庫重置完成！")
        return True
        
    except Exception as e:
        print(f"[ERROR] 資料庫重置失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-y', '--yes']:
        confirm = 'y'
    else:
        print("警告：此操作將刪除所有資料，並根據當前程式碼中的 models 重新建立資料表結構。")
        print(f"目標資料庫: {settings.DATABASE_URL}")
        confirm = input("您確定要繼續嗎？(y/N): ").strip().lower()
    
    if confirm == 'y':
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        success = asyncio.run(reset_database())
        if success:
            print("\n[INFO] 資料庫已成功重置。\n")
        else:
            sys.exit(1)
    else:
        print("[INFO] 操作已取消")