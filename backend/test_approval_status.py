#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

BASE_URL = "http://localhost:8001"

def test_approval_status():
    """測試審核狀態API"""
    
    print("=== 測試審核狀態API ===\n")
    
    # 1. 登入01446 (應該看到已審核)
    print("1. 測試01446登入:")
    login_data = {
        "username": "01446@topco.com",
        "password": "01446"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/auth/token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        token_data = response.json()
        token_01446 = token_data.get("token", {}).get("access_token")
        print(f"   01446登入成功, token: {token_01446[:20] if token_01446 else 'None'}...")
        
        # 測試獲取審核狀態
        headers = {"Authorization": f"Bearer {token_01446}"}
        
        # 獲取報告審核狀態
        approval_response = requests.get(
            f"{BASE_URL}/api/supervisor/reports/2/approvals",
            headers=headers
        )
        
        if approval_response.status_code == 200:
            approvals = approval_response.json()
            print(f"   報告2的審核狀態: {len(approvals)} 個主管")
            for approval in approvals:
                if approval['supervisor_empno'] == '01446':
                    print(f"     01446的狀態: {approval['status']}")
                    break
        else:
            print(f"   獲取審核狀態失敗: {approval_response.status_code}")
    
    print()
    
    # 2. 登入其他主管 (應該看到待審核)
    print("2. 測試其他主管登入:")
    login_data = {
        "username": "00006@topco.com",
        "password": "00006"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/auth/token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        token_data = response.json()
        token_00006 = token_data.get("token", {}).get("access_token")
        print(f"   00006登入成功, token: {token_00006[:20] if token_00006 else 'None'}...")
        
        # 測試獲取審核狀態
        headers = {"Authorization": f"Bearer {token_00006}"}
        
        # 獲取報告審核狀態
        approval_response = requests.get(
            f"{BASE_URL}/api/supervisor/reports/2/approvals",
            headers=headers
        )
        
        if approval_response.status_code == 200:
            approvals = approval_response.json()
            print(f"   報告2的審核狀態: {len(approvals)} 個主管")
            for approval in approvals:
                if approval['supervisor_empno'] == '00006':
                    print(f"     00006的狀態: {approval['status']}")
                    break
        else:
            print(f"   獲取審核狀態失敗: {approval_response.status_code}")
    
    print("\n=== 測試完成 ===")

if __name__ == "__main__":
    test_approval_status()