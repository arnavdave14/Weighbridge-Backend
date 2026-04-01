from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config.settings import settings

# Create remote engine (optional, only if URL is provided)
remote_url = settings.postgres_url
remote_engine = None
remote_session = None

if remote_url:
    remote_engine = create_async_engine(
        remote_url, 
        echo=False,
        connect_args={"ssl": False}
    )
    
    remote_session = async_sessionmaker(
        remote_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
