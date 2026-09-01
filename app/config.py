"""配置模块：集中管理所有环境相关的配置。"""

import os

from dotenv import load_dotenv

# 读取项目根目录下的 .env 文件，把里面的配置加载进环境变量
load_dotenv()

# MySQL 连接配置（带默认值，没填也能跑，只是连不上时会报错）
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "ops_kb")

# Milvus 向量库配置
MILVUS_HOST = os.getenv("MILVUS_HOST", "127.0.0.1")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", "19530"))
MILVUS_COLLECTION = os.getenv("MILVUS_COLLECTION", "ops_docs")

# Embedding 模型配置（阿里云百炼 DashScope）
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")

# 拼接成 SQLAlchemy 需要的连接地址（DSN）
# "mysql+pymysql" 的意思是：用 pymysql 这个驱动去连 MySQL
DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)
