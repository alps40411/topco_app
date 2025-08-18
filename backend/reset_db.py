# backend/reset_db.py

import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine

# 讓此獨立腳本可以載入 app 內的模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import AsyncSessionFactory, engine
from app.models import Base
from sqlalchemy import text

async def reset_database():
    """
    重置資料庫：刪除所有資料表並重新建立
    """
    print("[INFO] 開始重置資料庫...")
    
    try:
        async with engine.begin() as conn:
            print("[INFO] 正在刪除所有現有資料表...")
            
            # 使用CASCADE強制刪除所有依賴關係
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            await conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
            await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
            print("[SUCCESS] 已清空並重建schema")
            
            print("[INFO] 正在重新建立所有資料表...")
            await conn.run_sync(Base.metadata.create_all)
            print("[SUCCESS] 所有資料表已重新建立")
            
        print("[SUCCESS] 資料庫重置完成！")
        return True
        
    except Exception as e:
        print(f"[ERROR] 資料庫重置失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-y', '--yes']:
        # 自動確認模式
        confirm = 'y'
    else:
        # 交互式確認
        print("警告：此操作將刪除所有資料！")
        print(f"目標資料庫: {settings.DATABASE_URL}")
        confirm = input("您確定要繼續嗎？(y/N): ").strip().lower()
    
    if confirm == 'y':
        # 確保在 Windows 上 asyncio 可以正常運作
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        success = asyncio.run(reset_database())
        if success:
            print("\n[INFO] 資料庫已成功重置，您現在可以執行 seed_db.py 來填充初始資料")
        else:
            sys.exit(1)
    else:
        print("[INFO] 操作已取消")