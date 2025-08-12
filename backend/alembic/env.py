# backend/alembic/env.py
import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine
import asyncio

from alembic import context

# 將專案根目錄 (backend 資料夾) 加入 Python 的搜尋路徑
# 這一行必須在 'from app.models import Base' 之前
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models import Base # 現在 Python 才能正確找到 app 模組
from app.core.config import settings # 順便引入我們的設定檔


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 將資料庫連線 URL 設定到 Alembic 的 config 中
# 這樣 Alembic 才知道要連線到哪個資料庫
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


# Interpret the config file for Python logging.
# This line not longer needs to be COMMENTED OUT.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, encoding='utf-8')

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.
    Calls to context.execute() here emit the given string to the
    script output.
    """
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = create_async_engine(settings.DATABASE_URL)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
