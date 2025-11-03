import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    """AsyncAttrs 允许在异步上下文中使用 await obj.related"""
    pass


load_dotenv()
DATABASE_URL = f"mysql+aiomysql://{os.getenv("db_username")}:{os.getenv("db_password")}@aleafy.top:23306/data?charset=utf8mb4"

# 创建异步引擎
# - echo=True 用于开发（打印 SQL），生产环境设为 False
# - pool_pre_ping=True 防止 MySQL 8 小时断连
# - pool_recycle=3600 避免长时间连接失效
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
    pool_recycle=3600,
    max_overflow=20,
    pool_size=10,
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,  # 避免提交后属性失效
    autoflush=False,
)


# ======================
# 3. 初始化数据库（创建表）
# ======================
async def init_db():
    """在应用启动时调用，创建所有表"""
    async with engine.begin() as conn:
        # 如果表已存在，不会重复创建
        await conn.run_sync(Base.metadata.create_all)


# ======================
# 4. FastAPI 依赖项（用于路由）
# ======================
async def get_db():
    """FastAPI 依赖：提供数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session
