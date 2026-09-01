"""RAG 问答链路：检索（Retrieval）+ 生成（Generation）。

运行方式：python -m app.qa_chain
"""

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_milvus import Milvus

from .config import (
    DASHSCOPE_API_KEY,
    EMBEDDING_MODEL,
    LLM_MODEL,
    MILVUS_COLLECTION,
    MILVUS_HOST,
    MILVUS_PORT,
)

# 系统提示词：告诉大模型「你是谁、怎么回答」
# 关键设计：强制模型只依据参考资料回答，答不出就说不知道（防幻觉）
SYSTEM_PROMPT = """你是一个专业的 MySQL、Redis、Linux 运维知识库助手。
请严格根据下面提供的「参考资料」回答用户问题。
要求：
1. 参考资料中有答案时，直接回答，并在末尾注明参考了哪篇文档；
2. 参考资料中没有答案时，明确回答「知识库中没有相关内容」，不要编造；
3. 回答简洁、有条理，使用中文。"""


def load_vector_store() -> Milvus:
    """加载阶段 2 写入 Milvus 的向量库（读取模式）。"""
    embeddings = DashScopeEmbeddings(
        model=EMBEDDING_MODEL,
        dashscope_api_key=DASHSCOPE_API_KEY,
    )
    return Milvus(
        embedding_function=embeddings,
        collection_name=MILVUS_COLLECTION,
        connection_args={"uri": f"http://{MILVUS_HOST}:{MILVUS_PORT}"},
        # 读取端也要开启动态字段，才能把 title、category 等元数据查回来
        enable_dynamic_field=True,
    )


def format_context(docs: list[Document]) -> str:
    """把检索到的文档拼成一段「参考资料」文本，作为 prompt 的上下文。

    类比：开卷考试时，把翻到的几页书抄在草稿纸上，
    标注页码（标题），方便答题时引用。
    """
    parts = []
    for i, doc in enumerate(docs, start=1):
        parts.append(
            f"[{i}] 标题：《{doc.metadata['title']}》\n"
            f"{doc.page_content}"
        )
    return "\n\n".join(parts)


def build_chain(vector_store: Milvus) -> Runnable:
    """用 LCEL（LangChain 表达式）搭问答流水线。

    流水线图解：
    {question}
       │
       ├─► 检索器（从 Milvus 找 top-3 相关文档）──► format_context ──┐
       │                                                              ├─► prompt ─► 大模型 ─► 答案
       └─────────────────────────────► 原样传给 prompt ───────────────┘
    """
    # 检索器：把 Milvus 包装成「按问题找文档」的工具
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})

    # 创建通义千问大模型客户端
    llm = ChatTongyi(
        model_name=LLM_MODEL,
        dashscope_api_key=DASHSCOPE_API_KEY,
    )

    # 提示词模板：系统提示 + 人类提问（留两个插槽：context 和 question）
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", "参考资料：\n{context}\n\n用户问题：{question}"),
        ]
    )

    # LCEL 流水线：
    #   1) context 由「检索器 + 格式化」并行计算
    #   2) question 原样透传
    #   3) 组装 prompt → 调大模型 → 提取纯文本
    chain = (
        {
            "context": retriever | format_context,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


def ask(question: str, chain: Runnable) -> str:
    """问一个问题，返回大模型的回答。"""
    return chain.invoke(question)


def main() -> None:
    print("加载向量库...")
    vector_store = load_vector_store()
    chain = build_chain(vector_store)
    print("✅ RAG 流水线就绪\n")

    questions = [
        "Redis 缓存穿透怎么解决？",
        "MySQL 主从复制延迟很大，怎么排查？",
        "如何用 Kubernetes 部署一个应用？",  # 故意问知识库里没有的
    ]
    for question in questions:
        print("=" * 50)
        print(f"❓ 问题：{question}\n")
        print("📚 检索到的资料：")
        # 直接调用检索器，展示大模型看到了哪些文档（教学用）
        docs = vector_store.as_retriever(search_kwargs={"k": 3}).invoke(question)
        for doc in docs:
            print(f"  - 《{doc.metadata['title']}》")
        print("\n💬 回答：")
        answer = ask(question, chain)
        print(answer)
        print()


if __name__ == "__main__":
    main()
