#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
from fastapi.testclient import TestClient

# 讓此獨立腳本可以載入 app 內的模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.database import AsyncSessionFactory
from app.core.deps import get_current_user
from app.core.database import get_db

async def test_complete_auth_flow():
    """測試完整的認證流程"""
    print("[INFO] 測試完整的認證和權限流程...")
    
    client = TestClient(app)
    
    # 測試登入
    print("\n[TEST] 測試員工05489登入...")
    login_data = {
        "username": "05489",
        "password": "05489"
    }
    
    response = client.post("/api/auth/token", data=login_data)
    print(f"[INFO] 登入響應狀態: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        token = data["token"]["access_token"]
        user_info = data["user"]
        
        print(f"[SUCCESS] 登入成功!")
        print(f"[INFO] 用戶: {user_info['name']}")
        print(f"[INFO] 員工編號: {user_info['empno']}")
        print(f"[INFO] is_supervisor: {user_info['is_supervisor']}")
        
        # 測試使用token訪問需要認證的API
        headers = {"Authorization": f"Bearer {token}"}
        
        # 測試檢查下屬關係
        print(f"\n[TEST] 測試檢查下屬關係...")
        subordinates_response = client.get("/api/supervisor/has-subordinates", headers=headers)
        print(f"[INFO] 下屬檢查響應狀態: {subordinates_response.status_code}")
        
        if subordinates_response.status_code == 200:
            subordinates_data = subordinates_response.json()
            print(f"[INFO] 有下屬: {subordinates_data['has_subordinates']}")
        
        # 測試獲取專案列表
        print(f"\n[TEST] 測試獲取專案列表...")
        projects_response = client.get("/api/projects/my-projects", headers=headers)
        print(f"[INFO] 專案列表響應狀態: {projects_response.status_code}")
        
        if projects_response.status_code == 200:
            projects_data = projects_response.json()
            print(f"[INFO] 可用專案數量: {len(projects_data)}")
            if projects_data:
                print(f"[INFO] 第一個專案: {projects_data[0]['plan_subj_c']} ({projects_data[0]['planno']})")
    
    else:
        print(f"[ERROR] 登入失敗: {response.text}")

    print(f"\n[SUCCESS] 認證流程測試完成!")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_complete_auth_flow())