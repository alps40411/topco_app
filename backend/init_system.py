# backend/init_system.py

import asyncio
import sys
import os
import subprocess

# 讓此獨立腳本可以載入 app 內的模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

async def main():
    """
    數位發展部專用 - 系統初始化腳本
    1. 重置資料庫 (根據 Models 重建)
    2. (可選) 同步公司員工資料
    3. 填充數位發展部專案與測試帳號
    """
    print("=" * 60)
    print("       TOPCO 日報系統初始化 (數位發展部專用)")
    print("=" * 60)
    print(f"目標資料庫: {settings.DATABASE_URL}")
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] in ['-y', '--yes']:
        confirm = 'y'
    else:
        print("[WARNING] 此操作將執行以下步驟：")
        print("   1. 刪除所有現有資料表，並根據 models 重新建立結構")
        print("   2. (可選) 同步公司別A員工資料")
        print("   3. 填充數位發展部專用的專案與測試資料")
        print()
        confirm = input("您確定要繼續嗎？(y/N): ").strip().lower()
    
    if confirm != 'y':
        print("[INFO] 操作已取消")
        return
    
    backend_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        # 步驟 1: 重置資料庫並根據 Model 建立
        print("\n" + "=" * 50)
        print("步驟 1/3: 重置資料庫 (刪除並依 models 重建)")
        print("=" * 50)
        
        from reset_db import reset_database
        success = await reset_database()
        if not success:
            print("[ERROR] 資料庫重置失敗，停止執行")
            return
        
        # 步驟 2: 同步公司別A員工資料
        print("\n" + "=" * 50)
        print("步驟 2/3: 同步公司員工資料")
        print("=" * 50)
        
        sync_script_path = os.path.join(backend_dir, 'sync_company_a_data.py')
        if not os.path.exists(sync_script_path):
            print(f"[WARNING] 同步腳本 {sync_script_path} 不存在，跳過此步驟。")
        else:
            if len(sys.argv) > 1 and sys.argv[1] in ['-y', '--yes']:
                sync_full_data = 'y'
            else:
                sync_full_data = input("是否要從公司資料庫同步公司別A員工資料？(y/N): ").strip().lower()
            
            if sync_full_data == 'y':
                print("[INFO] 開始同步公司別A員工資料...")
                sync_result = subprocess.run([sys.executable, sync_script_path], cwd=backend_dir, capture_output=True, text=True)
                if sync_result.returncode == 0:
                    print(sync_result.stdout)
                    print("[SUCCESS] 公司別A員工資料同步完成")
                else:
                    print("[ERROR] 員工資料同步失敗:")
                    print(sync_result.stderr)
                    return
            else:
                print("[INFO] 跳過員工資料同步")

        # 步驟 3: 填充數位發展部資料
        print("\n" + "=" * 50)
        print("步驟 3/3: 填充數位發展部專案與測試帳號")
        print("=" * 50)
        
        from seed_db import seed_data
        await seed_data()

        print("\n" + "=" * 60)
        print("[SUCCESS] 系統初始化完成！")
        print("現在您可以啟動後端伺服器。")
        print("=" * 60)

    except Exception as e:
        print(f"[ERROR] 初始化過程中發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())