# InnerSeek 项目状态

最后更新：2026-05-24

## 项目概述

离火引 InnerSeek 是一个融合东方传统文化（八字、紫微斗数）与现代心理学的个人成长咨询平台。

## 当前状态：✅ 可部署

项目已完成核心功能开发，可以通过 Docker 一键部署。

## 核心功能

### ✅ 已完成

1. **用户测评系统**
   - 三步式测评流程（基本信息 → 生命议题 → 生成报告）
   - 支持游客模式（无需登录）
   - 响应式设计（移动端适配）

2. **AI 报告生成引擎**
   - 集成 DeepSeek API
   - 深度整合八字、紫微斗数、心理学分析
   - 生成包含 5 大模块的完整报告：
     - 能量内核（八字分析）
     - 人生剧场（紫微斗数）
     - 心智模式（心理学）
     - 职业发展指南
     - 行动方案

3. **咨询预约系统**
   - 三种服务套餐
   - 完整的预约流程

4. **课程展示模块**
   - 6 大课程模块
   - 三档价格体系

5. **用户中心**
   - 我的报告
   - 我的预约
   - 我的课程
   - 账户设置

6. **后端 API**
   - FastAPI 异步框架
   - PostgreSQL 数据库
   - Redis 缓存
   - 完整的日志系统
   - API 文档（Swagger）

7. **部署系统**
   - Docker Compose 编排
   - 一键部署脚本
   - 完整的部署文档

### 🚧 待开发

1. **用户认证系统**
   - 注册/登录功能
   - JWT 认证
   - 用户权限管理

2. **支付系统**
   - 微信支付
   - 支付宝支付
   - 订单管理

3. **报告管理**
   - 报告历史记录
   - PDF 导出
   - 报告分享

4. **管理后台**
   - 用户管理
   - 订单管理
   - 数据统计

## 技术栈

### 前端
- Vue 3 + Composition API
- Vue Router 4
- Vite 5
- Axios
- 原生 CSS

### 后端
- FastAPI (Python 3.11)
- SQLAlchemy 2.0 (异步)
- PostgreSQL 15
- Redis 7
- DeepSeek AI API

### 部署
- Docker & Docker Compose
- Nginx

## 快速开始

### 本地开发

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DeepSeek API Key

# 2. 启动服务（Windows）
deploy.bat

# 或启动服务（Linux/Mac）
./build.sh

# 3. 访问应用
# 前端: http://localhost
# 后端: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

详见 [QUICK_START.md](./QUICK_START.md)

### 远程部署

```bash
# 配置服务器信息
export REMOTE_HOST=your.server.com
export REMOTE_USER=root

# 执行部署
./deploy.sh
```

详见 [DEPLOYMENT.md](./DEPLOYMENT.md)

## 项目结构

```
innerseek/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心配置（数据库、日志）
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # Pydantic 模式
│   │   ├── services/       # 业务逻辑（AI、报告）
│   │   └── main.py         # 应用入口
│   ├── Dockerfile
│   └── requirements.txt
├── src/                     # 前端源码
│   ├── views/              # 页面组件
│   ├── utils/              # 工具函数
│   ├── router/             # 路由配置
│   └── main.js
├── docs/                    # 文档
│   ├── archive/            # 归档文档
│   ├── AI_INTEGRATION.md
│   ├── BACKEND_SUMMARY.md
│   └── ...
├── docker-compose.yml       # Docker 编排
├── Dockerfile.frontend      # 前端镜像
├── nginx.conf              # Nginx 配置
├── deploy.sh               # 部署脚本（Linux/Mac）
├── deploy.bat              # 部署脚本（Windows）
├── build.sh                # 构建脚本
├── .env.example            # 环境变量模板
├── README.md               # 项目说明
├── DEPLOYMENT.md           # 部署指南
├── QUICK_START.md          # 快速开始
└── PROJECT_STATUS.md       # 本文档
```

## 环境要求

### 开发环境
- Node.js 18+
- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### 生产环境
- Docker 20.10+
- Docker Compose 2.0+
- 2GB+ RAM
- 10GB+ 磁盘空间

## API 密钥

项目需要 DeepSeek API Key：
1. 访问 https://platform.deepseek.com/
2. 注册账号并获取 API Key
3. 在 `.env` 文件中配置：
   ```
   DEEPSEEK_API_KEY=sk-your-api-key-here
   ```

## 已知问题

无重大已知问题。

## 性能指标

- 报告生成时间：20-40 秒
- API 响应时间：< 100ms
- 前端加载时间：< 2 秒

## 安全性

- ✅ CORS 配置
- ✅ 环境变量隔离
- ✅ SQL 注入防护（ORM）
- ✅ XSS 防护（Vue 自动转义）
- ⚠️ 待添加：用户认证
- ⚠️ 待添加：HTTPS 配置
- ⚠️ 待添加：速率限制

## 日志系统

完整的日志系统已实现：
- 彩色控制台输出
- 分级文件日志（all/error/api）
- 请求/响应日志中间件
- API 调用日志装饰器

日志位置：`backend/logs/`

## 测试

### 手动测试

1. 访问 http://localhost
2. 点击"开始探索"
3. 填写测评信息
4. 等待报告生成
5. 查看完整报告

### API 测试

访问 http://localhost:8000/docs 使用 Swagger UI 测试 API。

## 下一步计划

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

## 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 联系方式

- 邮箱: hello@innerseek.me
- 微信: innerseek2026
- 公众号: 离火引InnerSeek

## License

Copyright © 2026 离火引 InnerSeek
