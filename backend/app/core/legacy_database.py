# backend/app/core/legacy_database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from .config import settings

# Legacy PostgreSQL Database Configuration
def get_legacy_database_url():
    """構建 PostgreSQL 資料庫連接字串"""
    if settings.LEGACY_DB_URL:
        return settings.LEGACY_DB_URL
    
    # 使用個別參數構建 PostgreSQL 連接字串
    return f"postgresql+psycopg2://{settings.LEGACY_DB_USER}:{settings.LEGACY_DB_PASSWORD}@{settings.LEGACY_DB_HOST}:{settings.LEGACY_DB_PORT}/{settings.LEGACY_DB_SERVICE}"

# Create legacy database engine
legacy_engine = create_engine(
    get_legacy_database_url(),
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=20,  # 增加基本連接池大小
    max_overflow=30,  # 增加溢出連接數
    pool_timeout=60,  # 增加等待時間
    connect_args={
        "connect_timeout": 10,
        "application_name": "topco_app_backend"
    }
)

# Create legacy session
LegacySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=legacy_engine)

# Legacy Base for models (if needed)
LegacyBase = declarative_base()

# Dependency to get legacy DB session
def get_legacy_db():
    db = LegacySessionLocal()
    try:
        yield db
    finally:
        db.close()