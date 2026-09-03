# 🔧 运维知识库问答系统（RAG）

基于 **MySQL + Redis + Milvus + LangChain + FastAPI** 的运维知识问答系统：
把 MySQL/Redis/Linux 运维知识文档向量化存入 Milvus，用户提问时先检索相关文档，
再交给通义千问生成有出处的回答；热点问题由 Redis 缓存秒回，整套系统可用 Docker Compose 一键部署。

> 学习/求职项目：完整覆盖 RAG、缓存设计、向量检索、接口封装、测试与容器化部署。

---

## ✨ 功能特性

- 💬 **Web 聊天页面**：仿 ChatGPT 风格，支持缓存命中标签（⚡）与参考来源展示
- 🔍 **RAG 问答**：检索 Milvus 中最相关的文档 → 通义千问基于资料回答，防幻觉
- 🚀 **Redis 缓存**：Cache Aside 模式，相同问题二次提问提速约 29 倍且不再调用大模型
- 🛡️ **容错降级**：Redis 故障自动降级为直连问答，接口不崩溃
- 🧪 **自动化测试**：pytest + mock，2 秒跑完 5 个用例，不依赖外部付费服务
- 🐳 **一键部署**：Docker Compose 编排 MySQL + Redis + Milvus + 应用

---

## 🏗️ 系统架构

```text
                    ┌────────────────────────────────────────────┐
                    │                 浏览器/客户端               │
                    └──────────────────────┬─────────────────────┘
                                           │ HTTP (JSON)
                    ┌──────────────────────▼─────────────────────┐
                    │            FastAPI (app/main.py)            │
                    │   GET / 聊天页面    POST /api/ask           │
                    └───┬──────────────┬──────────────┬──────────┘
                        │ ①查缓存      │ ②未命中      │ ③写回缓存
              ┌─────────▼─────────┐   │              │
              │ Redis 问答缓存     │   │              │
              └───────────────────┘   │              │
                                      ▼              ▼
                    ┌──────────────────────────────────────┐
                    │        RAG 流水线 (app/qa_chain.py)   │
                    │  检索：Milvus 向量库 ──► 相似文档      │
                    │  生成：通义千问(qwen-plus) ──► 回答    │
                    └──────────────┬───────────────────────┘
                                   │ 知识文档来源
                    ┌──────────────▼───────────────────────┐
                    │  MySQL：运维知识文档（27 篇种子数据）  │
                    └──────────────────────────────────────┘
```

**核心链路**：提问 → 查缓存 → 未命中则向量检索 + 大模型生成 → 写回缓存。

---

## 🧰 技术栈

| 层 | 技术 | 用途 |
|---|---|---|
| 数据 | MySQL 8 | 知识文档原始数据（ORM: SQLAlchemy 2） |
| 向量库 | Milvus 3.0 | 语义检索（写入端/读取端动态字段） |
| 缓存 | Redis | 问答结果缓存（Cache Aside + TTL + 主动失效） |
| RAG | LangChain 1.2 | 文档切分、检索器、LCEL 流水线 |
| 模型 | 通义千问 qwen-plus / text-embedding-v3（阿里云百炼） | 生成回答 / 文本向量化 |
| 后端 | FastAPI + Pydantic + uvicorn | REST API、参数校验、静态托管 |
| 前端 | 原生 HTML/CSS/JS | 聊天页面（无框架，含 XSS 防护） |
| 测试 | pytest + httpx + monkeypatch | 接口自动化测试 |
| 部署 | Docker / Docker Compose | 容器化编排与健康检查 |

---

## 📁 项目结构

```text
ops-knowledge-base/
├── app/
│   ├── config.py        # 配置读取（.env）
│   ├── database.py      # SQLAlchemy 引擎与会话
│   ├── models.py        # ORM 模型（categories / knowledge_docs）
│   ├── init_db.py       # 建库建表
│   ├── seed_data.py     # 27 篇运维知识种子数据（幂等）
│   ├── indexer.py       # 文档切分 → 向量化 → 写入 Milvus（重建后清缓存）
│   ├── qa_chain.py      # RAG 流水线（检索 + 通义千问）
│   ├── cache.py         # Redis 缓存模块
│   └── main.py          # FastAPI 入口（接口 + 错误处理 + 静态页面）
├── static/              # 前端页面（index.html / style.css / app.js）
├── tests/               # pytest 自动化测试
├── Dockerfile
├── docker-compose.yml
└── pytest.ini
```

---

## 🚀 快速开始

### 开发模式（本机已有 MySQL/Milvus/Redis 时）

环境：Python 3.13 + LangChain 1.2（conda 环境 `langchain1.2`）。

```powershell
# 1. 配置（复制 .env.example 为 .env，填 MySQL 密码与 DASHSCOPE_API_KEY）
#    注意：本机若已有服务占用 6379/3306，调整 .env 端口

# 2. 初始化数据
python -m app.init_db        # 建库建表
python -m app.seed_data      # 灌入 27 篇种子文档

# 3. 向量化入库（先启动 Milvus，端口 19530）
python -m app.indexer        # 切分 + 向量化 + 写入 Milvus + 清旧缓存

# 4. 启动服务
uvicorn app.main:app --reload
```

访问：**http://127.0.0.1:8000**（聊天页面）· **http://127.0.0.1:8000/docs**（Swagger 接口文档）

### Docker Compose 模式（干净服务器一键部署）

```bash
cp .env.example .env          # 填写 MYSQL_ROOT_PASSWORD / DASHSCOPE_API_KEY

# 1. 先只启动三个数据库服务（不要带 app），等待全部 healthy
docker compose up -d --build mysql redis milvus
docker compose ps            # milvus 首次启动约 1 分钟，等它 healthy 再继续

# 2. 用 app 镜像执行数据初始化（此时 MySQL/Milvus 都已就绪）
docker compose run --rm app python -m app.init_db
docker compose run --rm app python -m app.seed_data
docker compose run --rm app python -m app.indexer

# 3. 最后启动 app——确保它启动时集合已存在
docker compose up -d app
# 浏览器访问 http://<服务器IP>:8000
```

> 注意：Compose 里的 MySQL 是从空卷启动的，**必须先执行上面三条初始化命令**
> （建库 → 灌种子数据 → 向量化入库），否则问答接口没有数据可用。
> 顺序很关键：**app 必须在数据初始化之后启动**，否则它会在 Milvus 集合还不存在时
> 加载到无效的向量库状态（详见 FAQ Q5）。

### 本机已有服务时的部署提示

- Compose 中 MySQL/Redis/Milvus **不映射宿主机端口**（只在容器内网互通），
  与本机已运行的 MySQL（3306）、Redis 容器等不冲突；
- 但 **app 会占用宿主机 8000 端口**，如果本机已启动 uvicorn，先停掉再 `docker compose up`；
- 若在干净服务器部署，则无需关心以上提示。

---

## 🩹 常见问题（踩坑记录）

**Q1：Docker 构建报错 `langchain-community>=1.0` 无法满足？**

答：`langchain-community` 使用**独立的 0.x 版本号**（当前 PyPI 最新为 0.4.x），
与 `langchain` 核心的 1.x 版本号并不同步，**不存在 ≥1.0 的版本**。
requirements.txt 中应写 `langchain-community>=0.4,<0.5`。

**Q2：容器启动报 `ModuleNotFoundError: No module named 'redis'`？**

答：`redis`（Python 客户端库）必须显式写进 requirements.txt——
conda 环境里「有」不代表清单里有，Docker 是从零安装，缺一不可。

**Q3：本地 conda 能跑，为什么 Docker 构建还要再验证？**

答：「你的环境能跑」≠「依赖清单正确」。conda 环境是预装且版本互相兼容的；
requirements.txt 是给从零安装的人用的，必须以 Docker 等干净环境实测为准。

**Q4：pytest 跑完测试后进程不退出？**

答：这台 Windows + Python 3.13 机器上，pytest 向项目内写 `.pytest_cache`
会导致退出卡死（已定位验证）。`pytest.ini` 已禁用 cacheprovider 插件解决，
不影响测试结果。

**Q5：页面提问返回 500，日志报 `The number of search params is larger than 1`？**

答：启动顺序问题——app 容器在 `ops_docs` 集合创建**之前**就启动了，
内存里加载了无效的向量库状态。修复：数据初始化完成后执行
`docker compose restart app` 让它重新加载即可；正确做法见上方部署顺序。

---

## 🔌 API 说明

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 聊天页面 |
| GET | `/health` | 健康检查（部署探活） |
| POST | `/api/ask` | 问答接口 |

`POST /api/ask` 请求体：

```json
{ "question": "Redis 缓存穿透怎么解决？" }
```

响应体：

```json
{
  "question": "Redis 缓存穿透怎么解决？",
  "answer": "...",
  "sources": ["缓存穿透、击穿与雪崩"],
  "from_cache": false
}
```

---

## 🧪 测试

```powershell
python -m pytest tests/ -v
```

测试要点：外部依赖（大模型 / Milvus / Redis / MySQL）全部 mock，
2 秒内完成且不产生费用；包含「缓存命中时禁止调用大模型」的行为断言。
（本机 pytest 退出卡死问题已定位为环境兼容问题，`pytest.ini` 中禁用了 cacheprovider。）

---

## 💡 项目亮点（面试版）

1. **RAG 防幻觉设计**：系统提示词强制「无资料即答不知道」，并返回 `sources` 溯源
2. **缓存工程完整闭环**：Cache Aside + 哈希 key + TTL 被动过期 + 数据更新主动失效 + 故障降级
3. **生产级细节**：读写两端动态字段一致性、幂等脚本（查重式 + 重建式）、utf8mb4、密码不进 git
4. **自动化测试思维**：mock 付费模型、断言缓存命中不调模型、httpx ASGITransport 轻量驱动
5. **容器化交付**：Docker Compose 编排 + 健康检查 + 数据卷持久化 + 数据库不对外暴露

---

## 📚 知识库内容

内置 3 个分类共 27 篇运维文档（MySQL 10 / Redis 10 / Linux 7），覆盖主从复制、
慢查询、缓存穿透/击穿/雪崩、持久化、哨兵/集群、systemd 等高频运维知识点。

**如何扩展**：向 MySQL `knowledge_docs` 表插入新文档后，重跑 `python -m app.indexer`
（会自动清空旧问答缓存），新知识即可被检索回答。
