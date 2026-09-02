"""FastAPI 后端接口：把 RAG 问答包装成 HTTP API。

运行方式：uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import cache
from .qa_chain import ask, build_chain, load_vector_store

# ---------- 请求 / 响应模型（Pydantic） ----------
# 类比：餐厅菜单和结账单——规定「客人点什么、我们上什么」


class AskRequest(BaseModel):
    """请求体：客人点的菜（问题）。"""

    question: str = Field(
        ...,
        min_length=1,  # 问题不能为空
        max_length=500,  # 问题不能太长
        description="用户问题",
    )


class AskResponse(BaseModel):
    """响应体：上给客人的菜（回答 + 参考来源）。"""

    question: str
    answer: str
    sources: list[str] = []  # 参考的文档标题列表
    from_cache: bool = False  # 是否来自缓存（教学/调试用）


# ---------- 全局状态（服务启动时初始化一次） ----------
# 类比：餐厅后厨的设备——开张时备好，营业期间反复用
_vector_store = None
_chain = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务启动 / 关闭时执行的生命周期钩子。"""
    global _vector_store, _chain
    print("🚀 服务启动：正在加载 RAG 链路...")
    _vector_store = load_vector_store()
    _chain = build_chain(_vector_store)
    print("✅ RAG 链路就绪")
    yield
    print("🛑 服务关闭")


app = FastAPI(
    title="运维知识库问答系统",
    description="基于 MySQL + Redis + Milvus + LangChain 的运维知识问答 API",
    version="1.0.0",
    lifespan=lifespan,
)

# 静态资源目录：项目根目录下的 static 文件夹
# 把 /static/xxx 的请求映射到 static/xxx 文件（CSS、JS 都靠它）
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    """首页：返回聊天页面。"""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    """健康检查：确认服务活着（面试常问：探活接口）。"""
    return {"status": "ok"}


@app.post("/api/ask", response_model=AskResponse)
def ask_endpoint(request: AskRequest):
    """核心接口：接收问题，返回 RAG 回答。

    注意：这里用的是普通 def（同步函数），FastAPI 会自动把它丢进
    线程池执行，不会阻塞其他请求——先记住这个结论，面试加分点。
    """
    question = request.question

    # 第 1 步：先查缓存（Cache Aside 模式第一步）
    # 命中 = 别人问过同样的问题，直接把存好的回答端出去，不调大模型
    cached = cache.get_cached(question)
    if cached is not None:
        return AskResponse(
            question=question,
            answer=cached["answer"],
            sources=cached["sources"],
            from_cache=True,
        )

    # 第 2 步：缓存未命中，走完整 RAG 流程
    # 单独检索一次，把参考文档的标题带回来给用户看（溯源）
    retriever = _vector_store.as_retriever(search_kwargs={"k": 3})
    docs = retriever.invoke(question)
    sources = [doc.metadata["title"] for doc in docs]

    # 走 RAG 流水线拿回答
    answer = ask(question, _chain)

    # 第 3 步：把结果写回缓存，下次同样的问题直接命中
    cache.set_cached(question, answer, sources)

    return AskResponse(
        question=question,
        answer=answer,
        sources=sources,
        from_cache=False,
    )
