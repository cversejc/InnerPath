# InnerPath（离火引）

帮助你重构生命地图的个人成长咨询平台

---

## 项目简介

InnerPath 是一个融合东方传统文化人格叙事与现代心理学工具的个人成长咨询平台。

**核心功能**：
- 🎯 个人能量地图解读（基于时间节律的个性化分析）
- 💬 深度成长咨询服务
- 📚 东方人格洞察课程

**技术栈**：
- 前端：Vue 3 + Vite + Vue Router
- 后端：FastAPI + PostgreSQL + Redis
- AI：DeepSeek API
- 部署：Docker + Docker Compose + Nginx

---

## 快速开始（5分钟）

### 前置要求
- Docker 和 Docker Compose
- DeepSeek API Key（[获取地址](https://platform.deepseek.com/)）

### 启动步骤

```bash
# 1. 克隆项目
git clone <repository-url>
cd innerseek

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 DEEPSEEK_API_KEY

# 3. 启动服务
./scripts/dev.sh

# 4. 访问应用
# 前端：http://localhost
# 后端：http://localhost:8000
# API 文档：http://localhost:8000/docs
```

### 测试功能

1. 打开 http://localhost
2. 点击"开始探索"
3. 填写测评信息
4. 等待 AI 生成报告（约 30 秒）
5. 查看完整的个人成长报告

---

## 部署到生产环境

### 远程首次部署

```bash
# 1. 配置服务器信息
export REMOTE_HOST=your-server.com
export REMOTE_USER=root
export REMOTE_DIR=/opt/innerpath

# 2. 执行部署
./scripts/deploy.sh remote init

# 3. 登录服务器编辑配置
ssh root@your-server.com
vim /opt/innerpath/current/.env
# 修改 DEEPSEEK_API_KEY、数据库密码、SECRET_KEY 等

# 4. 重启服务
cd /opt/innerpath/current
docker-compose restart
```

### 快速更新代码

```bash
# 本地修改代码后，快速更新到生产环境
export REMOTE_HOST=your-server.com
./scripts/deploy.sh remote update
```

---

## 本地开发

### 开发模式（推荐）

前后端分离启动，支持热重载，方便调试：

**Windows:**
```bash
# 1. 启动后端（自动启动 Redis 和 PostgreSQL）
dev-backend.bat

# 2. 启动前端（新终端）
cd frontend
npm run dev

# 3. 启动 Celery Worker（可选，新终端）
dev-celery.bat
```

**Linux/Mac:**
```bash
# 1. 启动后端
./dev-backend.sh

# 2. 启动前端（新终端）
cd frontend
npm run dev

# 3. 启动 Celery Worker（可选，新终端）
./dev-celery.sh
```

访问地址：
- 前端: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

详细开发指南请查看 [DEV_GUIDE.md](DEV_GUIDE.md)

### 传统方式

#### 前端开发

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:3000
```

#### 后端开发

```bash
cd backend
pip install -r requirements.txt

# 确保根目录有 .env 文件
uvicorn app.main:app --reload --port 8000
# 访问 http://localhost:8000/docs
```

### 数据库迁移

```bash
cd backend

# 创建迁移
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head
```

---

## 项目结构

```
innerpath/
├── .env.example           # 配置模板（唯一配置文件）
├── docker-compose.yml     # Docker 编排
├── Dockerfile.frontend    # 前端镜像
├── nginx.conf            # Nginx 配置
├── package.json          # 前端依赖
├── vite.config.js        # Vite 配置
├── index.html
│
├── scripts/              # 脚本目录
│   ├── dev.sh           # 本地开发
│   └── deploy.sh        # 部署脚本
│
├── src/                  # 前端源码
│   ├── views/           # 页面组件
│   │   ├── Home.vue
│   │   ├── Assessment.vue
│   │   ├── Booking.vue
│   │   ├── Course.vue
│   │   └── UserCenter.vue
│   ├── router/          # 路由配置
│   ├── utils/           # 工具函数
│   ├── App.vue
│   ├── main.js
│   └── style.css
│
└── backend/              # 后端源码
    ├── app/
    │   ├── api/         # API 路由
    │   ├── core/        # 核心配置
    │   ├── models/      # 数据模型
    │   ├── schemas/     # Pydantic 模式
    │   ├── services/    # 业务逻辑
    │   ├── config.py    # 配置管理
    │   └── main.py      # 应用入口
    ├── alembic/         # 数据库迁移
    ├── tests/           # 测试
    ├── Dockerfile
    ├── requirements.txt
    └── alembic.ini
```

---

## 常用命令

### Docker 命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
docker-compose logs -f backend  # 只看后端日志

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 重新构建
docker-compose up -d --build
```

### 远程服务器管理

```bash
# 查看日志
ssh root@your-server.com "cd /opt/innerpath/current && docker-compose logs -f"

# 重启服务
ssh root@your-server.com "cd /opt/innerpath/current && docker-compose restart"

# 查看服务状态
ssh root@your-server.com "cd /opt/innerpath/current && docker-compose ps"
```

---

## 故障排查

### 端口被占用

修改 `docker-compose.yml` 中的端口映射：

```yaml
services:
  frontend:
    ports:
      - "3000:80"  # 改为 3000 端口
  
  backend:
    ports:
      - "8001:8000"  # 改为 8001 端口
```

### API Key 无效

检查 `.env` 文件中的配置：

```bash
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

确保 API Key 格式正确，没有多余的空格或引号。

### 服务无法启动

```bash
# 查看详细日志
docker-compose logs backend
docker-compose logs frontend

# 完全重建
docker-compose down
docker-compose up -d --build --force-recreate
```

### 数据库连接失败

```bash
# 检查数据库容器状态
docker-compose ps postgres

# 查看数据库日志
docker-compose logs postgres

# 重启数据库
docker-compose restart postgres
```

### 配置文件未生效

确保：
1. `.env` 文件在项目根目录
2. 修改配置后重启服务：`docker-compose restart`
3. 生产环境的敏感配置已修改（密码、密钥等）

---

## 核心功能模块

### 1. 用户测评系统
- 三步式测评流程：基本信息 → 生命议题 → 生成报告
- 支持游客模式（无需登录）
- 响应式设计（移动端适配）

### 2. AI 报告生成引擎
- 集成 DeepSeek API
- 深度整合八字、紫微斗数、心理学分析
- 生成包含 5 大模块的完整报告：
  - 能量内核（八字分析）
  - 人生剧场（紫微斗数）
  - 心智模式（心理学）
  - 职业发展指南
  - 行动方案

### 3. 咨询预约系统
- 三种服务套餐
- 完整的预约流程

### 4. 课程展示模块
- 6 大课程模块
- 三档价格体系

### 5. 用户中心
- 我的报告
- 我的预约
- 我的课程
- 账户设置

---

## 产品特色

### 话语体系创新
- 将传统命理包装为"东方能量测评"
- 使用"能量类型"、"心理动力"等现代化术语
- 避免"算命"等敏感词汇

### 漏斗模型设计
- **引流层**：免费/低价能量测评
- **转化层**：课程学习（¥399-999）
- **利润层**：1对1 深度咨询（¥1599-3599）

### 差异化优势
- 融合东方智慧与现代心理学
- 提供"结构化"而非"问题化"的分析视角
- 强调主体性和成长性，反对宿命论

---

## 环境变量说明

关键配置项（`.env` 文件）：

```bash
# DeepSeek API（必填）
DEEPSEEK_API_KEY=sk-your-api-key-here

# 数据库（生产环境必须修改密码）
POSTGRES_PASSWORD=change_this_in_production

# JWT 密钥（生产环境必须修改）
SECRET_KEY=change-this-to-random-string-in-production-min-32-chars

# 调试模式（生产环境设为 false）
DEBUG=false

# CORS 配置（生产环境添加实际域名）
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

完整配置说明见 `.env.example` 文件。

---

## 安全建议

### 生产环境检查清单

- [ ] 修改 `POSTGRES_PASSWORD` 为强密码
- [ ] 修改 `SECRET_KEY` 为随机字符串（至少 32 字符）
- [ ] 设置 `DEBUG=false`
- [ ] 配置 `CORS_ORIGINS` 为实际域名
- [ ] 配置 HTTPS（推荐使用 Let's Encrypt）
- [ ] 设置防火墙规则
- [ ] 定期备份数据库
- [ ] 使用 SSH 密钥而非密码登录

---

## 性能指标

- 报告生成时间：20-40 秒
- API 响应时间：< 100ms
- 前端加载时间：< 2 秒

---

## 开发计划

### 短期（1-2 周）
- [ ] 实现用户认证系统
- [ ] 添加报告历史记录
- [ ] 实现 PDF 导出功能

### 中期（1-3 个月）
- [ ] 集成支付系统
- [ ] 开发管理后台
- [ ] 添加数据统计功能

### 长期（3-12 个月）
- [ ] 建立咨询师网络
- [ ] 社群功能开发
- [ ] 品牌建设

---

## 联系方式

- 微信：innerpath2026
- 邮箱：hello@innerpath.me
- 公众号：离火引 InnerPath

---

## License

Copyright © 2026 离火引 InnerPath
