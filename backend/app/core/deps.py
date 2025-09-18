# backend/app/core/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from jose import jwt, JWTError

from app.core.database import get_db
from app.models.user import User
from app.models.employee import Employee
from app.schemas.user import TokenData
# from app.services import user_service  # 已移除，改用 JPS Legacy 資料庫
from app.core.security import SECRET_KEY, ALGORITHM

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        empno: str | None = payload.get("sub")
        if empno is None: raise credentials_exception
        token_data = TokenData(empno=empno)
    except JWTError:
        raise credentials_exception
    
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
    current_user = Depends(get_current_user)
):
    """Get current user ensuring they have an employee relationship"""
    if not current_user.employee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with an employee profile"
        )
    return current_user