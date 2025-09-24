# backend/app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from sqlalchemy import text
import logging

from app.core.legacy_database import get_legacy_db
from app.schemas.user import LoginResponse, User as UserSchema
from app.schemas.employee import EmployeeForUser
from app.core.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.sso import get_sso_headers_with_mock, SSOHeaders

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Authentication"])

# 新增 SSO 認證端點
@router.post("/sso", response_model=LoginResponse)
async def sso_login(request: Request):
    """
    SSO 認證端點 - 從 HTTP Headers 獲取用戶信息
    """
    try:
        # 獲取 SSO Headers (在開發環境啟用 Mock)
        sso_headers = get_sso_headers_with_mock(request, enable_mock=False)

        empno = sso_headers.get_empno()
        cocode = sso_headers.get_cocode()

        if not empno:
            logger.error("SSO login failed: missing empno")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="SSO authentication failed: missing employee ID",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info(f"SSO login attempt: empno={empno}, cocode={cocode}")

        # 驗證用戶和創建 token (復用現有邏輯)
        login_response = await _create_user_token_from_empno(empno, cocode or "A")

        logger.info(f"SSO login successful for empno: {empno}")
        return login_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SSO login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SSO authentication service error"
        )

async def _create_user_token_from_empno(empno: str, cocode: str = "A") -> LoginResponse:
    """
    共用函數：根據 empno 和 cocode 創建用戶 token
    """
    try:
        # 取得 legacy 資料庫連接
        legacy_db = next(get_legacy_db())

        # 從 JPS 查詢用戶資訊（使用完整的員工主檔查詢）
        user_sql = text("""
            SELECT a.empno, a.empnamec, a.cocode, a.deptno, a.dutyscript,
                   a.mailbox, a.pass, b.deptabbv, a.adm_rank, a.sop_role
            FROM jps.dcd003$master a
            LEFT JOIN jps.dcd002$master b ON a.cocode = b.cocode AND a.deptno = b.deptno
            WHERE a.empno = :empno AND a.cocode = :cocode
        """)

        result = legacy_db.execute(user_sql, {"empno": empno, "cocode": cocode})
        user_row = result.fetchone()

        if not user_row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Employee ID not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 檢查是否為主管 - 查詢是否有下屬
        supervisor_check_sql = text("""
            SELECT COUNT(*) FROM jps.groupfoodchn
            WHERE supervisor = :empno AND cocode = :cocode
            UNION ALL
            SELECT COUNT(*) FROM jps.GROUPDEPTCHN
            WHERE (leader = :empno OR pleader = :empno) AND cocode = :cocode
            UNION ALL
            SELECT COUNT(*) FROM jps.diarysupers
            WHERE supervisor = :empno AND (VALID_DATE IS NULL OR VALID_DATE > TO_CHAR(sysdate, 'YYYYMMDD'))
        """)

        supervisor_result = legacy_db.execute(supervisor_check_sql, {"empno": empno, "cocode": cocode})
        supervisor_counts = supervisor_result.fetchall()
        is_supervisor = any(count[0] > 0 for count in supervisor_counts) if supervisor_counts else False

        # 創建用戶物件，確保格式與前端期望一致
        user = UserSchema(
            id=1,  # 使用非零 ID，避免前端條件檢查失敗
            name=user_row[1] or "",  # 使用 EMPNAMEC 作為 name
            email=user_row[5] or "",  # 使用 MAILBOX 作為 email
            is_active=True,
            is_supervisor=is_supervisor,  # 根據實際資料判斷
            employee=EmployeeForUser(
                id=1,  # 使用非零 ID，避免前端條件檢查失敗
                empno=user_row[0],
                empnamec=user_row[1] or "",
                dutyscript=user_row[4] or "",  # dutyscript
                deptabbv=user_row[7] or "",    # deptabbv from join
                cocode=user_row[2] or ""       # cocode
            )
        )

        # 使用員工編號作為 JWT subject
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": empno},
            expires_delta=access_token_expires
        )

        return LoginResponse(
            token={"access_token": access_token, "token_type": "bearer"},
            user=user
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create user token error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )

@router.post("/token", response_model=LoginResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    使用 JPS Legacy 資料庫進行認證（暫時不驗證密碼，向後兼容）
    """
    try:
        logger.info(f"Traditional login attempt: empno={form_data.username}")

        # 使用共用函數創建 token
        login_response = await _create_user_token_from_empno(form_data.username, "A")

        logger.info(f"Traditional login successful for empno: {form_data.username}")
        return login_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Traditional login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )