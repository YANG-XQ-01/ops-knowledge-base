# Dockerfile：构建 FastAPI 应用的容器镜像
#
# 基础镜像：官方 Python 3.13 精简版（约 50MB，不含编译工具）
FROM python:3.13-slim

# 容器内工作目录：后续 COPY/CMD 都基于这个目录
WORKDIR /app

# 先复制依赖清单并安装——利用 Docker 层缓存：
# 只要 requirements.txt 没变，之后每次构建都不重复安装依赖（大幅提速）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再复制项目代码（排除 .dockerignore 里列出的文件，如 .env、.venv）
COPY app ./app
COPY static ./static

# 容器启动命令：uvicorn 监听 0.0.0.0:8000
# （0.0.0.0 = 接受外部访问；本机开发用 127.0.0.1 就够了）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
