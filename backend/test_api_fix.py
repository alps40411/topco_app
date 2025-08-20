#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
import requests
import json

# Test script to verify the API fix

BASE_URL = "http://localhost:8001"

def test_api_health():
    """Test if the API is running"""
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"[OK] API server is running (status: {response.status_code})")
        return True
    except Exception as e:
        print(f"[ERROR] API server is not accessible: {e}")
        return False

def test_login():
    """Test login with existing user"""
    try:
        # Try to login with the user 05489@topco.com (user ID 32, employee ID 7090)
        login_data = {
            "username": "05489@topco.com",
            "password": "05489"  # Updated to use empno as password
        }
        
        response = requests.post(
            f"{BASE_URL}/api/auth/token",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            print(f"[DEBUG] Response data: {token_data}")
            token = token_data.get("token", {}).get("access_token")
            print(f"[OK] Login successful, token: {token[:20] if token else 'None'}...")
            return token
        else:
            print(f"[ERROR] Login failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Login error: {e}")
        return None

def test_create_work_record(token):
    """Test creating a work record with the fixed employee_id"""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Create a test work record
        work_record_data = {
            "content": "測試記錄 - 驗證API修復",
            "project_id": 9,  # Use an existing project ID
            "files": []
        }
        
        response = requests.post(
            f"{BASE_URL}/api/records/",
            json=work_record_data,
            headers=headers
        )
        
        if response.status_code == 201:
            record_data = response.json()
            print(f"[OK] Work record created successfully with employee_id: {record_data.get('employee_id', 'N/A')}")
            return record_data
        else:
            print(f"[ERROR] Failed to create work record: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Work record creation error: {e}")
        return None

def main():
    print("=== Testing API Fix ===\n")
    
    # Test 1: Check if API is running
    if not test_api_health():
        return
    
    # Test 2: Try to login
    print("\n1. Testing login...")
    token = test_login()
    if not token:
        print("Cannot proceed without valid token")
        return
    
    # Test 3: Try to create work record (this should now work with correct employee_id)
    print("\n2. Testing work record creation...")
    work_record = test_create_work_record(token)
    
    if work_record:
        print(f"\n[OK] All tests passed! The foreign key constraint issue has been resolved.")
        print(f"   Work record was created with correct employee_id reference.")
    else:
        print(f"\n[ERROR] Tests failed. The issue may not be fully resolved.")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()