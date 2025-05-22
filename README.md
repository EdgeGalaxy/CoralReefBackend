# CoralReef Backend

## 项目简介

CoralReef Backend 是 CoralReef 平台的后端服务，基于 FastAPI 构建的现代化 Web API 服务。它提供了一套完整的 RESTful API 接口，用于管理和操作 CoralReef 系统的各种功能，包括用户认证、工作流管理、模型部署、设备监控等。作为 CoralReef 生态系统的核心组件，该后端服务负责处理前端请求、管理数据库、与其他服务集成，以及协调各种系统操作。

## 功能特性

### 用户认证与管理
- 用户登录/注册/注销
- OAuth 认证支持（GitHub）
- 基于角色的权限管理
- 工作空间用户管理

### 网关管理
- 网关注册与管理
- 状态监控与告警
- 远程连接管理

### 摄像头管理
- 摄像头设备注册与管理
- 支持多种摄像头类型
- 状态监控与告警
- 视频流处理

### 工作流管理
- 工作流创建、编辑和删除
- 工作流模板管理
- 工作流执行状态监控
- 工作流部署与调度

### 部署管理
- 服务部署配置
- 部署状态监控
- 远程控制与管理
- 日志收集与查询

### 模型管理
- ML 模型管理（上传、删除、查看）
- 支持多种模型平台
- 模型转换功能
- 模型评估与监控

### 区块管理
- 区块可见性控制
- 区块翻译支持
- 区块关联设置

### 系统集成
- Roboflow 集成
- 云存储（阿里云 OSS）集成
- 推理服务集成

## 安装与部署

### 开发环境

1. 克隆代码库
```bash
git clone https://github.com/yourusername/CoralReefBackend.git
cd CoralReefBackend
```

2. 安装 Poetry（如果尚未安装）
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. 安装依赖
```bash
poetry install
```

4. 更新环境变量
```bash
mv .env.example .env
# 编辑 .env 填入正确的配置信息

```

5. 运行开发服务器
```bash
cd reef
python run.py
```

6. 访问 API 文档
```
http://localhost:8000/docs
```

### 生产环境部署

#### 使用 Docker（推荐）

1. 构建 Docker 镜像
```bash
docker build -t coralreef-backend .
```

2. 运行容器
```bash
docker run -p 8000:8000 --env-file .env coralreef-backend
```
