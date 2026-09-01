"""初始化脚本：创建数据库 + 建表。

运行方式：python -m app.init_db
"""

from sqlalchemy import create_engine, text

from . import models  # 导入模型，让 SQLAlchemy 知道要建哪些表
from .config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER
from .database import Base, engine

# 不带库名的连接地址：先连到 MySQL 服务器本身
# 类比：先进入 MySQL 这栋"大楼"，再给项目开一个"房间"（数据库）
SERVER_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/"


def create_database() -> None:
    """创建数据库（如果不存在）。"""
    server_engine = create_engine(SERVER_URL)
    with server_engine.connect() as conn:
        # IF NOT EXISTS：库已存在就不重复创建（脚本可反复执行）
        conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS {DB_NAME} "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
        conn.commit()  # 建库是写操作，必须提交才真正生效
    server_engine.dispose()
    print(f"✅ 数据库 {DB_NAME} 已就绪")


def create_tables() -> None:
    """根据 models.py 的类定义，把缺失的表建出来。"""
    # 类比：照着"设计图纸"把书架搭好，已存在的表不会动
    Base.metadata.create_all(bind=engine)
    print("✅ 数据表已创建")


if __name__ == "__main__":
    create_database()
    create_tables()
