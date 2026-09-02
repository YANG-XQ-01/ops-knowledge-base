"""接口自动化测试。

运行方式：python -m pytest tests/ -v

设计要点（面试考点）：
- 测试不能依赖真实的大模型（慢、花钱），所以把 ask 函数 mock 掉；
- 缓存命中路径要证明「没有调用大模型」；
- 外部依赖（Milvus/Redis/MySQL）全部用假对象隔离，测试又快又稳；
- 用 httpx.ASGITransport 直接驱动 FastAPI：不启动真实端口、
  不创建后台线程，Windows 上 pytest 能干净退出。
"""

import httpx
import pytest
from langchain_core.documents import Document

from app import cache as cache_module
from app import main as main_module


# ---------- 假对象（替代真实的外部依赖） ----------


class FakeRetriever:
    """假的检索器：不管问什么，都返回同一篇「测试文档」。"""

    def invoke(self, question):
        return [
            Document(
                page_content="测试内容",
                metadata={"title": "测试文档"},
            )
        ]


class FakeVectorStore:
    """假的向量库：只提供 as_retriever，避免连真实 Milvus。"""

    def as_retriever(self, **kwargs):
        return FakeRetriever()


@pytest.fixture
async def client(monkeypatch):
    """给 app 换上假对象，返回一个不联网的异步 HTTP 客户端。

    注意：httpx.ASGITransport 不会执行 lifespan（启动事件），
    所以直接给全局变量赋值假对象，模拟「服务已启动」的状态。
    """
    monkeypatch.setattr(main_module, "_vector_store", FakeVectorStore())
    monkeypatch.setattr(main_module, "_chain", object())
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as c:
        yield c


# ---------- 测试用例 ----------


@pytest.mark.anyio
async def test_health(client):
    """健康检查接口应该返回 ok。"""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_empty_question_rejected(client):
    """空问题应该被 Pydantic 拒收（422）。"""
    resp = await client.post("/api/ask", json={"question": ""})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_cache_hit_does_not_call_llm(client, monkeypatch):
    """缓存命中时：直接返回缓存，绝不能调大模型。"""
    # 让缓存假装有数据
    monkeypatch.setattr(
        cache_module,
        "get_cached",
        lambda q: {"answer": "缓存中的答案", "sources": ["旧文档"]},
    )

    # 一旦 ask 被调用就报错（证明缓存命中时不会走到 RAG）
    def should_not_call(*args, **kwargs):
        raise AssertionError("缓存命中时不应调用大模型！")

    monkeypatch.setattr(main_module, "ask", should_not_call)

    resp = await client.post(
        "/api/ask",
        json={"question": "Redis 缓存穿透怎么解决？"},
    )
    data = resp.json()

    assert resp.status_code == 200
    assert data["from_cache"] is True
    assert data["answer"] == "缓存中的答案"
    assert data["sources"] == ["旧文档"]


@pytest.mark.anyio
async def test_cache_miss_runs_rag_and_writes_back(client, monkeypatch):
    """缓存未命中时：走 RAG，并把结果写回缓存。"""
    monkeypatch.setattr(cache_module, "get_cached", lambda q: None)

    # 记录「写回缓存」时收到的内容
    written = {}

    def fake_set_cached(question, answer, sources):
        written["question"] = question
        written["answer"] = answer
        written["sources"] = sources

    monkeypatch.setattr(cache_module, "set_cached", fake_set_cached)
    monkeypatch.setattr(
        main_module,
        "ask",
        lambda q, ch: "测试回答（模拟大模型生成）",
    )

    resp = await client.post(
        "/api/ask",
        json={"question": "MySQL 主从复制原理是什么？"},
    )
    data = resp.json()

    assert resp.status_code == 200
    assert data["from_cache"] is False
    assert data["answer"] == "测试回答（模拟大模型生成）"
    assert data["sources"] == ["测试文档"]
    # 确认写回缓存的内容正确
    assert written["answer"] == "测试回答（模拟大模型生成）"
    assert written["sources"] == ["测试文档"]


def test_cache_key_deterministic():
    """缓存 key 应该是确定性的：同样的问题 → 同样的 key。"""
    assert cache_module.make_key("问题A") == cache_module.make_key("问题A")
    assert cache_module.make_key("问题A") != cache_module.make_key("问题B")
    assert cache_module.make_key("问题A").startswith("qa:")
