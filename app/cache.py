"""Redis 缓存模块：给问答结果加一层「秒回」缓存。"""

import hashlib
import json

import redis

from .config import CACHE_TTL, REDIS_DB, REDIS_HOST, REDIS_PORT

# 全局 Redis 客户端（懒加载单例：第一次用时才连接）
_client = None


def get_client() -> redis.Redis:
    """获取 Redis 客户端（decode_responses=True 让返回值直接是字符串）。"""
    global _client
    if _client is None:
        _client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True,
        )
    return _client


def make_key(question: str) -> str:
    """根据问题生成缓存 key。

    为什么不直接用问题当 key？
    - 问题可能很长，Redis key 太长浪费内存；
    - 问题里可能有空格、中文等特殊字符，容易出问题。
    所以用 SHA256 哈希压缩成一串固定长度的十六进制字符。
    """
    digest = hashlib.sha256(question.encode("utf-8")).hexdigest()
    return f"qa:{digest}"


def get_cached(question: str) -> dict | None:
    """查缓存：命中返回 {answer, sources}，未命中返回 None。"""
    data = get_client().get(make_key(question))
    if data is None:
        return None
    return json.loads(data)


def set_cached(question: str, answer: str, sources: list[str]) -> None:
    """写缓存：setex = 设置值 + 过期时间（TTL），原子完成。"""
    payload = json.dumps(
        {"answer": answer, "sources": sources},
        ensure_ascii=False,  # 保留中文，方便调试时直接看
    )
    get_client().setex(make_key(question), CACHE_TTL, payload)


def clear_cache() -> int:
    """清空本服务的问答缓存（知识库更新后调用）。"""
    keys = get_client().keys("qa:*")
    if keys:
        return get_client().delete(*keys)
    return 0
