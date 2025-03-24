from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from fastapi import Depends

# Database URL should come from environment variables in production
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://michaelayoade@localhost/isp_management")
ASYNC_SQLALCHEMY_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL", "postgresql+asyncpg://michaelayoade@localhost/isp_management")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800
)

# Create async engine
async_engine = create_async_engine(
    ASYNC_SQLALCHEMY_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=async_engine, class_=AsyncSession)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_session() -> AsyncSession:
    """
    Get an async database session.
    
    Returns:
        AsyncSession: An async database session
    """
    async with AsyncSessionLocal() as session:
        yield session

def get_engine():
    """
    Get the SQLAlchemy engine.
    
    Returns:
        The SQLAlchemy engine instance.
    """
    return engine
