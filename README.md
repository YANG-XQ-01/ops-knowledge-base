# 运维知识库问答系统

基于 MySQL + Redis + Milvus + LangChain + FastAPI 的运维知识库问答系统（学习/求职项目）。

## 当前进度

- 阶段 1（已完成）：MySQL 表结构设计 + 种子数据入库

## 运行方式

本项目使用 conda 环境 `langchain1.2`（Python 3.13 + LangChain 1.2），
解释器路径：`C:\Users\yxq1\.conda\envs\langchain1.2\python.exe`

在 PyCharm 中把解释器设置为该环境后，在项目根目录执行：

```powershell
# 1. 填写数据库配置（复制 .env.example 为 .env，填 MySQL 密码）

# 2. 初始化数据库并灌入种子数据
python -m app.init_db
python -m app.seed_data
```
