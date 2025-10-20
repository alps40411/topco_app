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
    正式環境優先順序：SSO Headers > JWT Token
    開發環境優先順序：JWT Token > SSO Headers
    """
    from app.core.config import settings

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    empno = None
    token_empno = None
    sso_empno = None

    # 嘗試從 JWT Token 獲取用戶信息
    if credentials and credentials.credentials:
        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            token_empno = payload.get("sub")
            logger.info(f"JWT token present: empno={token_empno}")
        except JWTError as e:
            logger.warning(f"JWT decode failed: {str(e)}")

    # 嘗試從 SSO Headers 獲取用戶信息
    sso_cocode = None
    try:
        sso_headers = get_sso_headers_with_mock(request, enable_mock=False)
        sso_empno = sso_headers.get_empno()
        sso_cocode = sso_headers.get_cocode()  # ✅ 同時獲取 cocode
        if sso_empno:
            print(f"SSO headers present: empno={sso_empno}, cocode={sso_cocode}")
    except Exception as e:
        logger.warning(f"SSO headers check failed: {str(e)}")

    # 正式環境：SSO Headers 優先（確保 EIP 帳號切換即時生效）
    # 開發環境：JWT Token 優先（保持開發便利性）
    if settings.SSO_ENABLED and not settings.SSO_MOCK_ENABLED:
        # 正式機環境：優先使用 SSO Headers
        if sso_empno:
            empno = sso_empno
            logger.info(f"Authentication via SSO headers (production): empno={empno}")

            # 一致性檢查：如果同時有 JWT Token 但與 SSO 不符，強制重新認證
            if token_empno and token_empno != sso_empno:
                logger.warning(f"SSO user changed: token={token_empno}, sso={sso_empno}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="SSO user changed, please re-authenticate",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        elif token_empno:
            # SSO Headers 不存在時，使用 JWT Token 作為後備
            empno = token_empno
            logger.info(f"Authentication via JWT token (fallback): empno={empno}")
    else:
        # 開發環境：優先使用 JWT Token
        if token_empno:
            empno = token_empno
            logger.info(f"Authentication via JWT token (development): empno={empno}")
        elif sso_empno:
            empno = sso_empno
            logger.info(f"Authentication via SSO headers (development fallback): empno={empno}")

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

    # ✅ 優先從 URL query params 獲取 cocode，其次是 SSO headers，最後預設為 'A'
    query_param_cocode = request.query_params.get("cocode")
    query_cocode = query_param_cocode or sso_cocode or 'A'
    logger.info(f"Determined cocode for query: {query_cocode} (URL: {query_param_cocode}, SSO: {sso_cocode})")

    user_sql = text("""
        SELECT a.empno, a.empnamec, a.cocode, a.deptno, a.dutyscript,
               a.mailbox, a.pass, b.deptabbv, a.adm_rank, a.sop_role
        FROM jps.dcd003$master a
        LEFT JOIN jps.dcd002$master b ON a.cocode = b.cocode AND a.deptno = b.deptno
        WHERE a.empno = :empno AND a.cocode = :cocode
    """)

    result = legacy_db.execute(user_sql, {"empno": empno, "cocode": query_cocode})
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