# backend/sync_employees.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from datetime import datetime

# --- 讓此獨立腳本可以載入 app 內的模組 ---
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.models import Employee

# --- 來源資料庫 (舊資料庫) 的連線資訊 ---
SOURCE_DB_CONFIG = {
    'user': settings.SOURCE_DB_USER,
    'password': settings.SOURCE_DB_PASSWORD,
    'host': '10.129.7.28',
    'port': 5444,
    'dbname': 'myrpt'
}
SOURCE_TABLE = 'jps.groupfoodchn'

# --- 目標資料庫 (新資料庫) 的連線資訊 ---
TARGET_DB_URL = settings.DATABASE_URL

# --- Helper 函式 ---
def to_str(value):
    """安全地將任何值轉換為字串，處理 None 的情況。"""
    if value is None:
        return None
    return str(value)

def parse_date(date_str):
    if not date_str or (isinstance(date_str, str) and date_str.lower() == 'null'):
        return None
    if isinstance(date_str, datetime):
        return date_str.date()
    try:
        return datetime.strptime(str(date_str), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None

async def sync_employees():
    source_db_url = f"postgresql+asyncpg://{SOURCE_DB_CONFIG['user']}:{SOURCE_DB_CONFIG['password']}@{SOURCE_DB_CONFIG['host']}:{SOURCE_DB_CONFIG['port']}/{SOURCE_DB_CONFIG['dbname']}"
    source_engine = create_async_engine(source_db_url, echo=False)
    SourceSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=source_engine, class_=AsyncSession)

    target_engine = create_async_engine(TARGET_DB_URL, echo=False)
    TargetSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine, class_=AsyncSession)

    print("開始從來源資料庫讀取員工資料...")
    source_rows = []
    try:
        async with SourceSessionLocal() as source_db:
            result = await source_db.execute(text(f"SELECT * FROM {SOURCE_TABLE}"))
            source_rows = result.mappings().all()
            print(f"從來源資料庫成功讀取 {len(source_rows)} 筆員工資料。")
    except Exception as e:
        print(f"讀取來源資料庫時發生錯誤: {e}")
        return

    async with TargetSessionLocal() as target_db:
        print("\n正在從目標資料庫讀取現有的員工編號...")
        existing_empnos_result = await target_db.execute(select(Employee.empno))
        existing_empnos = {row[0] for row in existing_empnos_result}
        print(f"目標資料庫中已存在 {len(existing_empnos)} 位員工。")

        print("\n第一階段：正在比對並插入新員工的基本資料...")
        employees_to_create = []
        all_empnos_in_source = set()

        for row in source_rows:
            empno = to_str(row.get('empno'))
            if not empno:
                continue
            if empno in existing_empnos or empno in all_empnos_in_source:
                continue
            
            all_empnos_in_source.add(empno)
            employees_to_create.append(Employee(
                empno=empno,
                name=to_str(row.get('empnamec')) or 'N/A',
                department_no=to_str(row.get('deptno')),
                department_name=to_str(row.get('deptnamec')),
                department_abbr=to_str(row.get('deptabbv')),
                group_dept_no=to_str(row.get('g_deptno')),
                dclass=to_str(row.get('dclass')),
                xlevel=to_str(row.get('xlevel')),
                admin_rank=to_str(row.get('adm_rank')),
                company_code=to_str(row.get('cocode')),
                group_emp_no=to_str(row.get('grp_empno')),
                quit_date=parse_date(row.get('quitdate'))
            ))
        
        if not employees_to_create:
            print("沒有新的員工資料需要新增。")
        else:
            print(f"準備新增 {len(employees_to_create)} 位新員工...")
            target_db.add_all(employees_to_create)
            await target_db.commit()
            print(f"成功新增 {len(employees_to_create)} 位新員工。")

        print("\n正在建立員工編號與ID的對應字典...")
        all_employees_result = await target_db.execute(select(Employee.empno, Employee.id))
        empno_to_id_map = {empno: id for empno, id in all_employees_result}
        print("對應字典建立完成。")

        print("\n第二階段：正在更新主管資訊...")
        updates_count = 0
        for row in source_rows:
            empno = to_str(row.get('empno'))
            supervisor_empno = to_str(row.get('supervisor'))

            if not empno or not supervisor_empno or supervisor_empno == '00000':
                continue

            employee_id = empno_to_id_map.get(empno)
            supervisor_id = empno_to_id_map.get(supervisor_empno)

            if employee_id and supervisor_id:
                stmt = select(Employee).where(Employee.id == employee_id)
                result = await target_db.execute(stmt)
                employee_to_update = result.scalar_one_or_none()
                if employee_to_update and not employee_to_update.supervisor_id:
                    employee_to_update.supervisor_id = supervisor_id
                    updates_count += 1
        
        if updates_count > 0:
            await target_db.commit()
            print(f"成功更新 {updates_count} 位員工的主管資訊。")
        else:
            print("沒有需要更新的主管資訊。")

    print("\n資料同步完成！")

if __name__ == "__main__":
    asyncio.run(sync_employees())