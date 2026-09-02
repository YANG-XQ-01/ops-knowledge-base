"""索引脚本：把 MySQL 中的知识文档向量化，写入 Milvus。

运行方式：python -m app.indexer
"""

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from langchain_milvus import Milvus
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import select

from . import cache
from .config import (
    DASHSCOPE_API_KEY,
    EMBEDDING_MODEL,
    MILVUS_COLLECTION,
    MILVUS_HOST,
    MILVUS_PORT,
)
from .database import SessionLocal
from .models import Category, KnowledgeDoc


def load_docs_from_mysql() -> list[dict]:
    """第 1 步：从 MySQL 读出全部文档，并拼上分类名等元数据。"""
    db = SessionLocal()
    try:
        rows = db.execute(
            select(KnowledgeDoc, Category.name).join(
                Category, KnowledgeDoc.category_id == Category.id
            )
        ).all()
        docs = []
        for doc, category_name in rows:
            docs.append(
                {
                    "id": doc.id,
                    "title": doc.title,
                    "content": doc.content,
                    "tags": doc.tags or "",
                    "source": doc.source or "",
                    "category": category_name,
                }
            )
        return docs
    finally:
        db.close()


def split_docs(raw_docs: list[dict]) -> list[Document]:
    """第 2 步：把长文档切成小块（chunk）。

    类比：一本厚书直接整本比对太粗，先拆成「页」，
    检索时按页匹配，命中更精准。
    """
    # 真实项目 chunk_size 一般 300~500；这里种子文档偏短，
    # 为了让切分效果更明显，临时调小演示。
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=150,  # 每块最多约 150 个字符
        chunk_overlap=30,  # 相邻块重叠 30 字符，防止关键句被从中间切断
    )
    documents = []
    for raw in raw_docs:
        chunks = splitter.split_text(raw["content"])
        for index, chunk in enumerate(chunks):
            documents.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "doc_id": raw["id"],
                        "title": raw["title"],
                        "category": raw["category"],
                        "tags": raw["tags"],
                        "source": raw["source"],
                        "chunk_index": index,
                    },
                )
            )
    return documents


def build_embeddings() -> DashScopeEmbeddings:
    """第 3 步：创建 Embedding 模型客户端（阿里云百炼）。"""
    return DashScopeEmbeddings(
        model=EMBEDDING_MODEL,
        dashscope_api_key=DASHSCOPE_API_KEY,
    )


def index_to_milvus(
    documents: list[Document], embeddings: DashScopeEmbeddings
) -> Milvus:
    """第 4 步：向量化并写入 Milvus。

    drop_old=True：每次重建集合（重建式幂等），脚本可反复执行不产生重复数据。
    enable_dynamic_field=True：把 title、category 等元数据存成动态字段，
    检索时能一并带出来。
    """
    vector_store = Milvus.from_documents(
        documents,
        embedding=embeddings,
        collection_name=MILVUS_COLLECTION,
        connection_args={
            "uri": f"http://{MILVUS_HOST}:{MILVUS_PORT}",
        },
        drop_old=True,
        enable_dynamic_field=True,
    )
    return vector_store


def clear_qa_cache() -> None:
    """向量库重建后，清空旧问答缓存（主动失效）。

    对应阶段 5 的知识点：知识更新后不能只靠 TTL 被动过期，
    要主动清缓存，否则用户会拿到基于旧知识的回答。
    缓存清理失败不应该阻断入库，所以捕获异常降级。
    """
    try:
        removed = cache.clear_cache()
        print(f"    ✅ 已清空 {removed} 条旧问答缓存")
    except Exception as exc:
        print(f"    ⚠️ 缓存清理失败（不影响入库）：{exc}")


def verify(vector_store: Milvus) -> None:
    """第 5 步：验证——拿真实问题去检索，看能否召回相关文档。"""
    questions = [
        "Redis 缓存穿透怎么解决",
        "MySQL 主从复制是怎么工作的",
        "磁盘满了怎么排查",
    ]
    for question in questions:
        print(f"\n❓ 问题：{question}")
        results = vector_store.similarity_search_with_score(question, k=2)
        for doc, score in results:
            print(
                f"  [{doc.metadata['category']}] "
                f"《{doc.metadata['title']}》 相似度 {score:.4f}"
            )


def main() -> None:
    print("1/4 从 MySQL 读取文档...")
    raw_docs = load_docs_from_mysql()
    print(f"    ✅ 共 {len(raw_docs)} 篇文档")

    print("2/4 切分文档...")
    documents = split_docs(raw_docs)
    print(f"    ✅ 共切出 {len(documents)} 个块")

    print("3/4 创建 Embedding 模型...")
    embeddings = build_embeddings()
    print(f"    ✅ 模型：{EMBEDDING_MODEL}")

    print(f"4/4 写入 Milvus（集合：{MILVUS_COLLECTION}）...")
    vector_store = index_to_milvus(documents, embeddings)
    print("    ✅ 入库完成，开始检索验证")
    clear_qa_cache()  # 数据更新了，旧缓存作废
    verify(vector_store)


if __name__ == "__main__":
    main()
