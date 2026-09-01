"""数据库核心模块：创建引擎（engine）和会话（session）。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import DATABASE_URL

# Engine = 数据库连接池：提前和 MySQL 建好一批连接，随取随用
# pool_pre_ping=True：每次取连接前先"探活"，连接断了会自动重连
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# SessionLocal = 会话工厂：每次需要操作数据库时，通过它创建一个会话
# 一个会话就像一次"打开 Excel → 操作 → 保存 → 关闭"的过程
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Base：所有 ORM 模型的父类，模型继承它后就能自动映射成数据库表
Base = declarative_base()


def get_db():
    """给后续 FastAPI 阶段用的依赖函数：每次请求一个会话，用完自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
