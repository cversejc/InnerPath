# 辰鉴（ChenJian）

星辰引路，镜子照见——用人生说明书与行动决策，陪你见自己、知其序、行其路。

---

## 项目简介

辰鉴是一个融合东方时间结构、现代心理学与哲学脉络的个人成长产品。它不替用户算命或预测未来，而是把个人属性、环境时序与现实行动放到同一张地图上。

**核心功能**：
- 🪞 **fi / 人生说明书**：性格密码、能量通路、关系模式、核心矛盾与人生时序
- 🧭 **te / 行动与决策**：最小可行行动、6—12 个月能力建设、决策日历与陪伴
- 🌌 **辰鉴·共鉴计划**：玄学、心理学、哲学的当代翻译与长期人本实践

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
cd InnerPath

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
2. 直接注册或登录账号（手机号仅作为登录账号，不发送短信验证码）
3. 点击“开始测评”并填写测评信息
4. 等待 AI 生成报告（约 30 秒）
5. 在用户中心或报告详情中查看已绑定到当前账号的报告

### 账户与后台初始化

所有业务页面和业务 API 都要求登录。首个管理员通过后端初始化命令创建，后续管理员或咨询师由管理员生成一次性邀请：

```bash
cd backend
python -m app.cli create-admin --phone 13800138000 --name 系统管理员
```

登录入口支持手机号 + 密码；注册不校验手机号归属，工作人员通过管理员生成的一次性邀请令牌完成账号初始化。当前版本不启用短信找回密码，忘记密码请联系管理员在后台重置。刷新令牌只保存在 HttpOnly Cookie，访问令牌保存在当前浏览器会话中。

---

## 项目文档

- [辰鉴产品定位](docs/辰鉴产品定位.md)：产品核心、fi / te 双端结构与产品边界
- [多步报告生成系统使用指南](MULTISTEP_REPORT_GUIDE.md)：配置开关、生成流程、数据结构与降级策略

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

### Docker 全栈开发（推荐）

脚本会检查根目录 `.env`，构建前后端镜像，并启动 PostgreSQL、Redis、Celery 和 Nginx：

```bash
./scripts/dev.sh
```

Windows PowerShell 可直接运行等价命令：

```powershell
docker compose up -d --build
```

访问地址：
- 前端：http://localhost
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 前端热重载

在项目根目录安装依赖并启动 Vite。开发服务器会把 `/api` 请求代理到 `http://localhost:8000`：

```bash
npm install
npm run dev
# 访问 http://localhost:3000
```

### 后端和 Celery 直接运行

先启动 PostgreSQL 与 Redis，再分别运行 API 和 Worker：

```bash
docker compose up -d postgres redis

cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

另开终端启动 Celery Worker：

```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info
```

### 数据库迁移

```bash
cd backend

# 创建迁移
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 初始化首个管理员（迁移完成后执行）
python -m app.cli create-admin --phone 13800138000 --name 系统管理员
```

---

## 项目结构

```
InnerPath/
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
│   ├── assets/           # 图片资源
│   ├── components/       # BrandNav、BrandFooter 等共享组件
│   ├── data/             # 决策日历等前端数据
│   ├── views/            # 页面组件
│   │   ├── Home.vue / Assessment.vue / ReportDetail.vue
│   │   ├── Services.vue / Booking.vue / Course.vue
│   │   ├── Calendar.vue / About.vue / UserCenter.vue
│   ├── router/           # 路由配置
│   ├── utils/            # API 与报告工具函数
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

### 1. 用户说明书系统
- 三步式说明书流程：先天坐标 → 当下处境 → 生成说明书
- 报告任务、报告历史和报告详情均绑定当前登录用户
- 响应式设计（移动端适配）

### 2. AI 报告生成引擎
- 集成 DeepSeek API
- 深度整合八字、紫微斗数、心理学与哲学翻译
- 生成包含“我是谁 / 我卡在哪 / 我往哪去”的人生说明书
- 明确不做命盘等级、财富等级、能力高低与具体未来因果预测

### 3. 咨询预约系统
- 三种服务套餐
- 完整的预约流程

### 4. 课程展示模块
- 6 大课程模块
- 三档价格体系

### 5. 决策日历
- 路由：`/pages/calendar/calendar`
- 提供月度阶段、每日适合 / 不适合事项、关键决策节点和记录提示
- 点开日期后可同时查看“今天适合做什么”和“今天实际做了什么”，支持行动 / 决策记录、状态和备注
- 记录优先保存到账号；接口不可用时暂存于当前浏览器，日历格子会显示已有记录的日期
- 日历内容来自管理员创建并发布的用户日历；暂无已发布内容时，前端会自动使用 `src/data/decisionCalendar.js` 的示例数据，发布真实日历后自动切换

### 6. 用户中心
- 我的报告
- 我的预约
- 我的课程
- 账户设置

### 7. 账户与角色权限
- `user` 只能访问自己的报告、预约、课程进度和已发布日历
- `consultant` 只能访问已分配预约关联用户的必要资料、报告和已发布日历
- `admin` 管理用户、后台邀请、预约分配、日历和审计记录

---

## 产品特色

### 话语体系创新
- 以“星辰引路，镜子照见”作为品牌核心
- fi 端负责看见个人属性，te 端负责支持现实行动
- 用当代语言翻译传统经验，不机械套用古代社会角色

### 长期人本方向
- 不算命，不审判，不点评命盘层次、财富等级和能力高低
- 可以给希望，但不预测客户未来具体走向和因果
- 社会属性的批评回到个人属性的肯定，把主动权留给用户

### 差异化优势
- 融合玄学、心理学与哲学，但让三者各自负责不同问题
- 提供“人生说明书 + 行动决策”的双端结构
- 强调“用舍由时，行藏在我”：顺环境选择，在助推时冲锋，在风浪时修整

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

# 是否启用多步报告生成（默认关闭）
USE_MULTISTEP_GENERATION=false

# CORS 配置（生产环境添加实际域名）
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

完整配置说明见 `.env.example` 文件；多步生成的流程、降级和排查方式见
[MULTISTEP_REPORT_GUIDE.md](MULTISTEP_REPORT_GUIDE.md)。

---

## 安全建议

### 生产环境检查清单

- [ ] 修改 `POSTGRES_PASSWORD` 为强密码
- [ ] 修改 `SECRET_KEY` 为随机字符串（至少 32 字符）
- [ ] 设置 `DEBUG=false`
- [ ] 配置 `CORS_ORIGINS` 为实际域名
- [ ] 配置 HTTPS（推荐使用 Let's Encrypt）
- [ ] 设置 `SESSION_COOKIE_SECURE=true`
- [ ] 设置防火墙规则
- [ ] 定期备份数据库
- [ ] 使用 SSH 密钥而非密码登录

---

## 性能指标

- 报告生成时间：单步约 20-40 秒，多步模式约 60-80 秒（取决于 API 响应）
- API 响应时间：< 100ms
- 前端加载时间：< 2 秒

---

## 开发计划

### 短期（1-2 周）
- [x] 实现用户认证系统
- [x] 添加报告历史记录
- [ ] 实现 PDF 导出功能

### 中期（1-3 个月）
- [ ] 集成支付系统
- [x] 开发管理后台
- [ ] 添加数据统计功能

### 长期（3-12 个月）
- [ ] 建立咨询师网络
- [ ] 社群功能开发
- [ ] 品牌建设

---

## 联系方式

- 微信：chenjian2026
- 邮箱：hello@chenjian.me
- 公众号：辰鉴 ChenJian

---

## License

Copyright © 2026 辰鉴 ChenJian
