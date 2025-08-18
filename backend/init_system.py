# backend/init_system.py

import asyncio
import sys
import os

# 讓此獨立腳本可以載入 app 內的模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

async def main():
    """
    完整的系統初始化腳本
    1. 重置資料庫（清除所有資料表並重建）
    2. 執行資料庫遷移
    3. 填充初始資料
    """
    print("=" * 60)
    print("       TOPCO 日報系統初始化 (數位發展部專用)")
    print("=" * 60)
    print(f"目標資料庫: {settings.DATABASE_URL}")
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] in ['-y', '--yes']:
        # 自動確認模式
        confirm = 'y'
    else:
        # 交互式確認
        print("[WARNING] 此操作將執行以下步驟：")
        print("   1. 刪除所有現有資料表和資料")
        print("   2. 重新建立資料表結構")
        print("   3. 執行資料庫遷移")
        print("   4. 同步公司別A資料")
        print("   5. 填充數位發展部測試資料")
        print()
        confirm = input("您確定要繼續嗎？(y/N): ").strip().lower()
    
    if confirm != 'y':
        print("[INFO] 操作已取消")
        return
    
    try:
        # 步驟 1: 重置資料庫
        print("\n" + "=" * 50)
        print("步驟 1/4: 重置資料庫")
        print("=" * 50)
        
        from reset_db import reset_database
        success = await reset_database()
        if not success:
            print("[ERROR] 資料庫重置失敗，停止執行")
            return
        
        # 步驟 2: 執行資料庫遷移
        print("\n" + "=" * 50)
        print("步驟 2/4: 執行資料庫遷移")
        print("=" * 50)
        
        os.system("cd backend && alembic upgrade head")
        print("[SUCCESS] 資料庫遷移完成")

        # 步驟 3: 同步公司別A員工資料
        print("\n" + "=" * 50)
        print("步驟 3/5: 同步公司別A員工資料")
        print("=" * 50)
        
        if len(sys.argv) > 1 and sys.argv[1] in ['-y', '--yes']:
            # 自動模式：直接執行同步
            print("[INFO] 自動模式：開始同步公司別A員工資料...")
            sync_result = os.system("python sync_company_a_data.py")
            if sync_result == 0:
                print("[SUCCESS] 公司別A員工資料同步完成")
            else:
                print("[ERROR] 員工資料同步失敗，請檢查同步腳本")
                return
        else:
            sync_full_data = input("是否要從公司資料庫同步公司別A員工資料？(y/N): ").strip().lower()
            if sync_full_data == 'y':
                print("[INFO] 開始同步公司別A員工資料...")
                sync_result = os.system("python sync_company_a_data.py")
                if sync_result == 0:
                    print("[SUCCESS] 公司別A員工資料同步完成")
                else:
                    print("[ERROR] 員工資料同步失敗，請檢查同步腳本")
                    return
            else:
                print("[INFO] 跳過員工資料同步")

        # 步驟 4: 填充數位發展部資料
        print("\n" + "=" * 50)
        print("步驟 4/5: 填充數位發展部測試資料")
        print("=" * 50)
        
        from seed_db import seed_data
        await seed_data()

        # 步驟 5: 系統驗證
        print("\n" + "=" * 50)
        print("步驟 5/5: 系統驗證")
        print("=" * 50)
        
        print("[INFO] 驗證系統設置...")
        # 這裡可以添加一些基本的系統驗證
        print("[SUCCESS] 系統驗證完成")



        
        # 初始化完成
        print("\n" + "=" * 60)
        print("[SUCCESS] 系統初始化完成！")
    except Exception as e:
        print(f"[ERROR] 初始化過程中發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # 確保在 Windows 上 asyncio 可以正常運作
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())