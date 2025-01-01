# 使用Python 3.10作为基础镜像
FROM  python:3.10-slim

# 设置工作目录
WORKDIR /workspace

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 安装Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# 将Poetry添加到PATH
ENV PATH="/root/.local/bin:$PATH"

# 复制Poetry配置文件
COPY pyproject.toml poetry.lock ./

# 安装项目依赖
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi --no-root && \
    rm -rf /root/.cache && \
    rm pyproject.toml poetry.lock

# 复制项目文件
COPY . .

CMD cd reef && python3 run.py
