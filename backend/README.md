# InnerSeek Backend API

离火引个人成长咨询平台后端服务

## 技术栈

- **框架**: FastAPI 0.109.0
- **数据库**: PostgreSQL 15 + Redis 7
- **ORM**: SQLAlchemy 2.0 (异步)
- **任务队列**: Celery
- **认证**: JWT
- **Python**: 3.11+

## 功能特性

- ✅ 用户认证（手机号+验证码登录）
- ✅ AI报告生成（DeepSeek API集成）
- ✅ 异步任务处理（Celery）
- ✅ 报告管理（CRUD）
- ✅ 预约管理
- ✅ 课程管理
- ✅ 请求限流
- ✅ CORS配置
- ✅ 自动API文档（Swagger UI）

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 复制环境变量配置
cp .env.example .env
# 编辑 .env 文件，填入实际配置
```

### 2. 使用Docker Compose（推荐）

```bash
# 启动所有服务（PostgreSQL + Redis + API + Celery）
docker-compose up -d

# 查看日志
docker-compose logs -f api

# 停止服务
docker-compose down
```

### 3. 手动启动

**启动PostgreSQL和Redis:**
```bash
# 使用Docker
docker run -d --name postgres -p 5432:5432 \
  -e POSTGRES_DB=innerseek \
  -e POSTGRES_USER=innerseek \
  -e POSTGRES_PASSWORD=your_password \
  postgres:15

docker run -d --name redis -p 6379:6379 redis:7-alpine
```

**运行数据库迁移:**
```bash
alembic upgrade head
```

**启动API服务:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**启动Celery Worker:**
```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

## API文档

启动服务后访问：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 主要API端点

### 认证
- `POST /api/v1/auth/send-code` - 发送验证码
- `POST /api/v1/auth/login` - 登录/注册
- `POST /api/v1/auth/logout` - 登出

### 用户
- `GET /api/v1/users/me` - 获取当前用户信息
- `PUT /api/v1/users/me` - 更新用户信息

### 报告
- `POST /api/v1/reports` - 创建报告（异步）
- `GET /api/v1/reports/tasks/{task_id}` - 查询任务状态
- `GET /api/v1/reports` - 获取报告列表
- `GET /api/v1/reports/{report_id}` - 获取报告详情
- `DELETE /api/v1/reports/{report_id}` - 删除报告

### 预约
- `POST /api/v1/bookings` - 创建预约
- `GET /api/v1/bookings` - 获取预约列表
- `POST /api/v1/bookings/{id}/cancel` - 取消预约

### 课程
- `GET /api/v1/courses` - 获取课程列表
- `GET /api/v1/courses/my-courses` - 获取我的课程

## 数据库迁移

```bash
# 创建新迁移
alembic revision --autogenerate -m "description"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 开发

### 代码格式化
```bash
black app/
flake8 app/
```

### 运行测试
```bash
pytest
```

## 部署

### 生产环境配置

1. 修改 `.env` 文件：
   - 设置 `ENVIRONMENT=production`
   - 设置 `DEBUG=False`
   - 使用强密码和安全的 `SECRET_KEY`

2. 使用Supervisor管理进程（参考 `deployment/supervisor.conf`）

3. 配置Nginx反向代理（参考 `deployment/nginx.conf`）

### 环境变量说明

| 变量 | 说明 | 示例 |
|------|------|------|
| DATABASE_URL | PostgreSQL连接URL | postgresql+asyncpg://user:pass@localhost/db |
| REDIS_URL | Redis连接URL | redis://localhost:6379/0 |
| SECRET_KEY | JWT密钥 | 随机生成的长字符串 |
| DEEPSEEK_API_KEY | DeepSeek API密钥 | sk-xxx |
| CORS_ORIGINS | 允许的前端域名 | http://localhost:3000,http://example.com |

## 项目结构

```
backend/
├── app/
│   ├── api/v1/          # API路由
│   ├── core/            # 核心功能（认证、缓存、短信）
│   ├── models/          # 数据库模型
│   ├── schemas/         # Pydantic模型
│   ├── services/        # 业务逻辑
│   ├── tasks/           # Celery任务
│   ├── db/              # 数据库配置
│   ├── config.py        # 配置管理
│   ├── dependencies.py  # 依赖注入
│   └── main.py          # 应用入口
├── alembic/             # 数据库迁移
├── tests/               # 测试
├── requirements.txt     # Python依赖
├── docker-compose.yml   # Docker配置
└── .env.example         # 环境变量示例
```

## 安全注意事项

- ✅ API Key存储在环境变量中，不暴露在前端
- ✅ JWT token认证
- ✅ 请求限流（验证码5次/分钟，报告生成10次/小时）
- ✅ CORS配置
- ✅ SQL注入防护（SQLAlchemy ORM）
- ⚠️ 生产环境需配置HTTPS
- ⚠️ 生产环境需配置防火墙

## 故障排查

### 数据库连接失败
```bash
# 检查PostgreSQL是否运行
docker ps | grep postgres

# 检查连接
psql -h localhost -U innerseek -d innerseek
```

### Redis连接失败
```bash
# 检查Redis是否运行
docker ps | grep redis

# 测试连接
redis-cli ping
```

### Celery任务不执行
```bash
# 检查Celery worker日志
docker-compose logs celery

# 手动启动worker
celery -A app.tasks.celery_app worker --loglevel=debug
```

## 许可证

MIT License

## 联系方式

- 项目地址: https://github.com/your-org/innerseek
- 问题反馈: https://github.com/your-org/innerseek/issues
