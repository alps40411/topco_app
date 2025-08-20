#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8001"

def debug_frontend_requests():
    """調試前端請求的完整流程"""
    
    print("=== 調試前端請求流程 ===\n")
    
    # 1. 登入01446
    print("1. 登入01446:")
    login_data = {
        "username": "01446@topco.com",
        "password": "01446"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/auth/token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code != 200:
        print(f"   登入失敗: {response.status_code}")
        return
    
    token_data = response.json()
    token = token_data.get("token", {}).get("access_token")
    user_info = token_data.get("user", {})
    
    print(f"   登入成功")
    print(f"   用戶信息: {user_info}")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. 獲取昨天的日報列表 (模擬前端邏輯)
    yesterday = datetime.now() - timedelta(days=1)
    date_string = yesterday.strftime('%Y-%m-%d')
    
    print(f"\n2. 獲取 {date_string} 的日報列表:")
    response = requests.get(
        f"{BASE_URL}/api/supervisor/reports-by-date?date={date_string}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"   獲取日報失敗: {response.status_code}")
        return
    
    reports_data = response.json()
    print(f"   找到 {len(reports_data)} 份日報")
    
    for i, report in enumerate(reports_data):
        print(f"   報告 {i+1}: ID={report['id']}, 員工={report['employee']['name']}")
    
    # 3. 為每個報告獲取審核狀態 (模擬前端邏輯)
    print(f"\n3. 為每個報告獲取審核狀態:")
    
    for report in reports_data:
        report_id = report['id']
        print(f"   報告 {report_id} ({report['employee']['name']}):")
        
        approval_response = requests.get(
            f"{BASE_URL}/api/supervisor/reports/{report_id}/approvals",
            headers=headers
        )
        
        if approval_response.status_code == 200:
            approvals = approval_response.json()
            print(f"     審核狀態: {len(approvals)} 個主管")
            
            # 找到當前用戶的審核狀態
            current_user_employee_id = user_info.get('id')  # 這是錯誤的！應該用employee.id
            if 'employee' in user_info:
                current_user_employee_id = user_info['employee']['id']
            
            print(f"     當前用戶employee_id: {current_user_employee_id}")
            
            my_approval = None
            for approval in approvals:
                print(f"       主管 {approval['supervisor_empno']} (ID: {approval['supervisor_id']}): {approval['status']}")
                if approval['supervisor_id'] == current_user_employee_id:
                    my_approval = approval
            
            if my_approval:
                print(f"     ✓ 我的審核狀態: {my_approval['status']}")
            else:
                print(f"     ✗ 找不到我的審核記錄")
        else:
            print(f"     獲取審核狀態失敗: {approval_response.status_code}")
        
        print()
    
    print("=== 調試完成 ===")

if __name__ == "__main__":
    debug_frontend_requests()