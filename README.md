# 离火引 InnerPath

帮助你重构生命地图的个人成长咨询平台

## 项目简介

离火引是一个融合东方传统文化人格叙事与现代心理学工具的个人成长咨询平台。我们提供：

- 个人能量地图解读
- 深度成长咨询
- 东方人格洞察课程

## 核心功能模块

### 1. 用户测评模块
- 三步式测评流程：基本信息 → 生命议题 → 生成报告
- 东方能量测评（基于时间节律的个人特质分析）
- 实时生成个性化能量地图报告

### 2. AI报告生成引擎
- 五行能量类型映射（生长驱动型、表达驱动型、稳定承载型等）
- 将传统命理语言转化为现代心理学语言
- 生成包含能量特质、职业建议、关系模式、行动方案的完整报告

### 3. 咨询预约系统
- 三种服务套餐：种子用户体验、能量地图解读、深度咨询
- 完整的预约流程和管理系统

### 4. 课程展示模块
- 6大课程模块（基础篇、工具篇、整合篇、应用篇、进阶篇）
- 三档价格体系（基础版、进阶版、VIP版）
- 系统化学习路径

### 5. 用户中心
- 我的报告：查看历史测评报告
- 我的预约：管理咨询预约记录
- 我的课程：跟踪学习进度
- 账户设置：管理个人信息

## 技术栈

### 前端
- Vue 3 (Composition API)
- Vue Router 4
- Vite 5
- Axios
- 原生 CSS (响应式设计)

### 后端
- FastAPI (Python 3.11)
- SQLAlchemy 2.0 (异步 ORM)
- PostgreSQL 15
- Redis 7
- DeepSeek AI API

### 部署
- Docker & Docker Compose
- Nginx

## 开发指南

### 快速开始（Docker 部署）

**推荐方式**：使用 Docker Compose 一键启动所有服务

#### Windows 用户

```bash
# 1. 配置环境变量
copy .env.example .env
# 编辑 .env 文件，填入 DeepSeek API Key

# 2. 启动服务
deploy.bat
```

#### Linux/Mac 用户

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 DeepSeek API Key

# 2. 启动服务
./build.sh
```

服务启动后：
- 前端：http://localhost
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 本地开发模式

#### 前端开发

```bash
npm install
npm run dev
```

项目将在 http://localhost:5173 启动

#### 后端开发

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 构建生产版本

```bash
npm run build
```

### Docker 命令

```bash
# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 重新构建
docker-compose up -d --build
```

### 远程部署

详见 [DEPLOYMENT.md](./DEPLOYMENT.md)

## 项目结构

```
innerpath/
├── src/
│   ├── views/              # 页面组件
│   │   ├── Home.vue        # 首页
│   │   ├── Services.vue    # 服务页
│   │   ├── Assessment.vue  # 能量测评
│   │   ├── Booking.vue     # 预约咨询
│   │   ├── Course.vue      # 课程展示
│   │   ├── UserCenter.vue  # 用户中心
│   │   └── About.vue       # 关于页
│   ├── utils/              # 工具函数
│   │   └── reportGenerator.js  # AI报告生成引擎
│   ├── router/             # 路由配置
│   ├── App.vue             # 根组件
│   ├── main.js             # 入口文件
│   └── style.css           # 全局样式
├── index.html
├── vite.config.js
├── package.json
└── 产品规划.md             # 产品规划文档
```

## 产品特色

### 1. 话语体系创新
- 将传统命理包装为"东方能量测评"
- 使用"能量类型"、"心理动力"等现代化术语
- 避免"算命"等敏感词汇

### 2. 漏斗模型设计
- **引流层**: 免费/低价能量测评
- **转化层**: 课程学习（¥399-999）
- **利润层**: 1对1深度咨询（¥1599-3599）

### 3. 差异化优势
- 融合东方智慧与现代心理学
- 提供"结构化"而非"问题化"的分析视角
- 强调主体性和成长性，反对宿命论

## 用户旅程

```
首页 → 开始探索
  ↓
能量测评 → 填写信息 → 选择议题 → 生成报告
  ↓
查看报告预览 → 三个选择：
  1. 预约深度咨询
  2. 学习系统课程
  3. 查看完整报告（用户中心）
```

## 移动端优化

本项目已针对移动端进行全面优化：

- 响应式布局设计
- 触摸友好的交互
- 移动端导航优化
- 字体和间距适配

## 下一步开发计划

### 短期（1-2周）
- 完善报告生成算法（接入真实八字排盘）
- 增加支付功能
- 优化用户体验（PDF导出、报告分享）

### 中期（1-3个月）
- 构建SaaS中台系统
- 社群功能开发
- 内容运营体系

### 长期（3-12个月）
- 建立咨询师网络
- 数据资产积累
- 品牌建设

## 联系方式

- 微信：innerpath2026
- 邮箱：hello@innerpath.me
- 公众号：离火引InnerPath

## License

Copyright © 2026 离火引 InnerPath
