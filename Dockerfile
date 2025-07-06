# 第一阶段：构建依赖环境
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 安装Poetry
RUN curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.8.5 python3 -

# 将Poetry添加到PATH
ENV PATH="/root/.local/bin:$PATH"

# 先复制依赖文件以利用Docker缓存
COPY pyproject.toml poetry.lock ./

# 配置Poetry并安装依赖
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# 复制项目文件
COPY . .

CMD cd reef && python3 run.py
