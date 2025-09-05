# backend/app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from sqlalchemy import text

from app.core.legacy_database import get_legacy_db
from app.schemas.user import LoginResponse, User as UserSchema
from app.schemas.employee import EmployeeForUser
from app.core.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(tags=["Authentication"])

@router.post("/token", response_model=LoginResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    使用 JPS Legacy 資料庫進行認證（暫時不驗證密碼）
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
            WHERE a.empno = :empno AND a.cocode = 'A'
        """)
        
        result = legacy_db.execute(user_sql, {"empno": form_data.username})
        user_row = result.fetchone()
        
        if not user_row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Employee ID not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 暫時不使用密碼驗證，只驗證員工編號是否存在
        
        # 檢查是否為主管 - 查詢是否有下屬
        supervisor_check_sql = text("""
            SELECT COUNT(*) FROM jps.groupfoodchn 
            WHERE supervisor = :empno AND cocode = 'A'
            UNION ALL
            SELECT COUNT(*) FROM jps.GROUPDEPTCHN 
            WHERE (leader = :empno OR pleader = :empno) AND cocode = 'A'
            UNION ALL
            SELECT COUNT(*) FROM jps.diarysupers 
            WHERE supervisor = :empno AND (VALID_DATE IS NULL OR VALID_DATE > TO_CHAR(sysdate, 'YYYYMMDD'))
        """)
        
        supervisor_result = legacy_db.execute(supervisor_check_sql, {"empno": form_data.username})
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
            data={"sub": form_data.username}, 
            expires_delta=access_token_expires
        )
        
        return {
            "token": {"access_token": access_token, "token_type": "bearer"},
            "user": user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 認證錯誤: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )