# 运维知识库问答系统

基于 MySQL + Redis + Milvus + LangChain + FastAPI 的运维知识库问答系统（学习/求职项目）。

## 当前进度

- 阶段 1（已完成）：MySQL 表结构设计 + 种子数据入库
- 阶段 2（已完成）：文档向量化 + 写入 Milvus 向量库
- 阶段 3（已完成）：RAG 问答链路（检索 + 通义千问生成）
- 阶段 4（已完成）：FastAPI 后端接口（REST API）
- 阶段 5（已完成）：Redis 缓存优化（Cache Aside）
- 阶段 6（已完成）：Web 聊天前端页面
- 阶段 7（已完成）：自动化测试与错误处理

## 运行方式

本项目使用 conda 环境 `langchain1.2`（Python 3.13 + LangChain 1.2），
解释器路径：`C:\Users\yxq1\.conda\envs\langchain1.2\python.exe`

在 PyCharm 中把解释器设置为该环境后，在项目根目录执行：

```powershell
# 1. 填写数据库配置（复制 .env.example 为 .env，填 MySQL 密码）

# 2. 初始化数据库并灌入种子数据
python -m app.init_db
python -m app.seed_data

# 3. 把文档向量化写入 Milvus（需先启动 Milvus，且 .env 配置好 DASHSCOPE_API_KEY）
python -m app.indexer

# 4. RAG 问答测试（需要 .env 配置好 DASHSCOPE_API_KEY）
python -m app.qa_chain

# 5. 启动 FastAPI 服务（浏览器打开 http://127.0.0.1:8000/docs 有交互式文档）
uvicorn app.main:app --reload
```

服务启动后，浏览器打开 **http://127.0.0.1:8000** 即可使用聊天页面；
打开 **http://127.0.0.1:8000/docs** 可查看交互式接口文档。

## 自动化测试

```powershell
python -m pytest tests/ -v
```

说明：`pytest.ini` 禁用了 cacheprovider 插件——在这台 Windows + Python 3.13
机器上 pytest 向项目内写 `.pytest_cache` 会导致进程退出卡死（已定位验证），
禁用后测试可正常退出，不影响测试结果。

## Redis 缓存

项目使用独立 Redis 容器（端口 6380，避免与机器上其他服务占用 6379 冲突）：

```powershell
docker run -d --name ops-redis -p 6380:6379 redis:6-alpine
```

问答接口采用 Cache Aside 模式：先查缓存，命中直接返回；未命中走 RAG 并写回缓存（TTL 1 小时）。
