# backend/app/core/deps.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from typing import Optional
import logging

from app.models.user import User
from app.models.employee import Employee
from app.schemas.user import TokenData
from app.core.security import SECRET_KEY, ALGORITHM
from app.core.sso import get_sso_headers_with_mock

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)  # 設置為 False，允許我們自定義錯誤處理

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    獲取當前用戶 - 支援 JWT Token 和 SSO Headers 雙重認證
    優先順序：JWT Token > SSO Headers
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    empno = None

    # 方法1：嘗試從 JWT Token 獲取用戶信息
    if credentials and credentials.credentials:
        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            empno = payload.get("sub")
            logger.info(f"Authentication via JWT token: empno={empno}")
        except JWTError as e:
            logger.warning(f"JWT decode failed: {str(e)}")

    # 方法2：如果 JWT Token 失敗，嘗試從 SSO Headers 獲取 (開發環境後備)
    if not empno:
        try:
            sso_headers = get_sso_headers_with_mock(request, enable_mock=False)
            sso_empno = sso_headers.get_empno()
            if sso_empno:
                empno = sso_empno
                logger.info(f"Authentication via SSO headers: empno={empno}")
        except Exception as e:
            logger.warning(f"SSO headers fallback failed: {str(e)}")

    # 如果兩種方法都失敗，拋出異常
    if not empno:
        logger.error("Authentication failed: no valid JWT token or SSO headers")
        raise credentials_exception

    token_data = TokenData(empno=empno)
    
    # 從 JPS Legacy 資料庫查詢用戶資訊
    from app.core.legacy_database import get_legacy_db
    from app.schemas.employee import EmployeeForUser
    from app.schemas.user import User as UserSchema
    from sqlalchemy import text
    
    legacy_db = next(get_legacy_db())
    
    user_sql = text("""
        SELECT a.empno, a.empnamec, a.cocode, a.deptno, a.dutyscript, 
               a.mailbox, a.pass, b.deptabbv, a.adm_rank, a.sop_role
        FROM jps.dcd003$master a
        LEFT JOIN jps.dcd002$master b ON a.cocode = b.cocode AND a.deptno = b.deptno
        WHERE a.empno = :empno AND a.cocode = 'A'
    """)
    
    result = legacy_db.execute(user_sql, {"empno": empno})
    user_row = result.fetchone()
    
    if not user_row:
        raise credentials_exception
    
    # 創建用戶物件，確保格式與認證 API 一致
    user = UserSchema(
        id=1,  # 使用非零 ID，避免前端條件檢查失敗
        name=user_row[1] or "",
        email=user_row[5] or "",
        is_active=True,
        is_supervisor=False,
        employee=EmployeeForUser(
            id=1,  # 使用非零 ID，避免前端條件檢查失敗
            empno=user_row[0],
            empnamec=user_row[1] or "",
            dutyscript=user_row[4] or "",    # dutyscript
            deptabbv=user_row[7] or "",      # deptabbv from join
            cocode=user_row[2] or "",      # cocode
            deptno=user_row[3] or "",       # deptno
        )
    )
    
    return user

async def get_current_user_with_employee(
    request: Request,
    current_user = Depends(get_current_user)
):
    """Get current user ensuring they have an employee relationship"""
    if not current_user.employee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with an employee profile"
        )
    return current_user