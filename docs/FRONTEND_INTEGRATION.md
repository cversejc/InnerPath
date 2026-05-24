# 前端API集成说明

## 更新内容

前端已改造为调用后端API，不再直接调用DeepSeek API。主要变更：

### 新增文件

1. **src/utils/apiConfig.js** - API配置
   - 根据环境变量自动切换API地址
   - 配置请求超时时间

2. **src/utils/authService.js** - 认证服务
   - 发送验证码
   - 登录/注册
   - 登出
   - 获取/更新用户信息
   - Token管理

3. **.env.development** - 开发环境变量
   - API地址: http://localhost:8000/api/v1

4. **.env.production** - 生产环境变量
   - API地址: http://8.135.25.206/api/v1

### 修改文件

1. **src/utils/aiService.js**
   - 删除硬编码的API Key（安全隐患已解决）
   - 改为调用后端 `/api/v1/reports` 接口
   - 实现轮询机制查询报告生成状态
   - 保留降级方案（generateBasicReport）
   - 新增报告列表、详情、删除功能

## 使用说明

### 1. 启动后端服务

```bash
cd backend

# 使用Docker Compose（推荐）
docker-compose up -d

# 或手动启动
# 1. 启动PostgreSQL和Redis
# 2. 运行数据库迁移: alembic upgrade head
# 3. 启动API: uvicorn app.main:app --reload
# 4. 启动Celery: celery -A app.tasks.celery_app worker --loglevel=info
```

### 2. 启动前端

```bash
# 开发模式
npm run dev

# 生产构建
npm run build
```

### 3. 测试流程

1. **访问首页**: http://localhost:3000
2. **进入测评页面**: 填写用户信息
3. **生成报告**: 
   - 前端调用 `POST /api/v1/reports` 创建任务
   - 显示生成进度（轮询 `GET /api/v1/reports/tasks/{task_id}`）
   - 完成后显示报告预览
4. **查看报告列表**: 用户中心 → 我的报告
5. **查看报告详情**: 点击报告卡片

## API端点说明

### 认证相关
- `POST /api/v1/auth/send-code` - 发送验证码
- `POST /api/v1/auth/login` - 登录/注册
- `POST /api/v1/auth/logout` - 登出

### 报告相关
- `POST /api/v1/reports` - 创建报告（异步）
- `GET /api/v1/reports/tasks/{task_id}` - 查询任务状态
- `GET /api/v1/reports` - 获取报告列表
- `GET /api/v1/reports/{report_id}` - 获取报告详情
- `DELETE /api/v1/reports/{report_id}` - 删除报告

### 用户相关
- `GET /api/v1/users/me` - 获取当前用户信息
- `PUT /api/v1/users/me` - 更新用户信息

### 预约相关
- `POST /api/v1/bookings` - 创建预约
- `GET /api/v1/bookings` - 获取预约列表
- `POST /api/v1/bookings/{id}/cancel` - 取消预约

### 课程相关
- `GET /api/v1/courses` - 获取课程列表
- `GET /api/v1/courses/my-courses` - 获取我的课程

## 环境变量

### 开发环境 (.env.development)
```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### 生产环境 (.env.production)
```
VITE_API_BASE_URL=http://8.135.25.206/api/v1
```

## 注意事项

1. **API Key安全**: API Key现在存储在后端环境变量中，前端代码不再包含敏感信息
2. **认证机制**: 使用JWT token认证，token存储在localStorage中
3. **异步报告生成**: 报告生成改为异步，避免阻塞UI（2-5秒生成时间）
4. **错误处理**: 401错误会自动清除token并提示重新登录
5. **降级方案**: 如果后端API调用失败，会使用前端基础算法生成报告

## 后续优化建议

1. **添加登录页面**: 当前未实现登录UI，可以在需要认证时弹出登录框
2. **优化轮询机制**: 可以改用WebSocket实现实时进度推送
3. **添加加载动画**: 报告生成时显示更友好的进度条
4. **错误提示优化**: 统一错误提示样式和文案
5. **离线支持**: 考虑使用Service Worker实现离线访问

## 故障排查

### 前端无法连接后端
- 检查后端是否启动: `curl http://localhost:8000/health`
- 检查环境变量是否正确: 查看 `.env.development`
- 检查CORS配置: 后端 `.env` 中的 `CORS_ORIGINS`

### 报告生成失败
- 查看后端日志: `docker-compose logs api`
- 查看Celery日志: `docker-compose logs celery`
- 检查DeepSeek API Key是否有效

### Token过期
- Token有效期24小时，过期后需要重新登录
- 可以在后端 `.env` 中调整 `ACCESS_TOKEN_EXPIRE_MINUTES`
