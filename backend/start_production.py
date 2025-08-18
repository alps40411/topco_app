# backend/start_production.py
import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv

if __name__ == "__main__":
    # 設置環境變數指向生產環境配置
    env_file = Path(__file__).parent / ".env.production"
    if env_file.exists():
        print(f"使用生產環境配置: {env_file}")
        # 手動載入生產環境配置
        load_dotenv(env_file)
    else:
        print("找不到生產環境配置，使用預設 .env")
        load_dotenv()
    
    # 啟動生產服務器
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # 允許外部訪問
        port=8000,
        workers=1,  # 單工作進程，適合小團隊使用
        log_level="info",
        access_log=True,
        reload=False  # 生產環境不要自動重載
    )