# backend/app/core/oracle_db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from app.core.config import settings

# Create the SQLAlchemy engine for Oracle
# Using QueuePool for connection pooling
# echo=True will log all SQL statements, which is useful for debugging.
# You might want to set it to False in a production environment.
engine = create_engine(
    settings.ORACLE_DB_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    # echo=True
)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_oracle_db():
    """
    Dependency that provides a SQLAlchemy session for Oracle.
    It ensures the session is always closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
