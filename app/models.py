"""ORM 模型：用 Python 类描述数据库表结构（表 = 类，行 = 对象）。"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class Category(Base):
    """分类表：给知识文档归类，比如「MySQL」「Redis」。"""

    __tablename__ = "categories"  # 表名

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    name = Column(String(50), unique=True, nullable=False, comment="分类名（唯一）")
    description = Column(String(200), comment="分类说明")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    # 反向关系：拿到一个分类对象，就能访问它下面的所有文档
    docs = relationship("KnowledgeDoc", back_populates="category")

    def __repr__(self):
        return f"<Category id={self.id} name={self.name}>"


class KnowledgeDoc(Base):
    """知识文档表：一条记录 = 一篇运维知识文档。"""

    __tablename__ = "knowledge_docs"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    # 外键：指向 categories.id，表示这篇文档属于哪个分类
    category_id = Column(
        BigInteger,
        ForeignKey("categories.id"),
        nullable=False,
        index=True,  # 建索引：按分类查询时更快
        comment="所属分类 ID",
    )
    title = Column(String(200), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容")
    tags = Column(String(200), comment="标签，多个用逗号分隔")
    source = Column(String(100), comment="内容来源")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,  # 记录更新时自动刷新时间
        comment="更新时间",
    )

    category = relationship("Category", back_populates="docs")

    def __repr__(self):
        return f"<KnowledgeDoc id={self.id} title={self.title}>"
