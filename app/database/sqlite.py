from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config.settings import settings

# Engine options for SQLite
sqlite_connect_args = {"check_same_thread": False}

# Create local engine
local_engine = create_async_engine(
    settings.sqlite_url, 
    echo=False, 
    connect_args=sqlite_connect_args if settings.sqlite_url.startswith("sqlite") else {"ssl": False}
)

# Session maker
local_session = async_sessionmaker(
    local_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
