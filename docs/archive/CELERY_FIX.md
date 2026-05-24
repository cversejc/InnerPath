# 🔧 紧急修复：Celery Worker 问题

## 问题诊断

**症状**：
- 报告一直显示"生成中"
- 前端不断轮询任务状态
- 任务状态一直是 "processing"，progress 为 0
- 报告详情页面空白

**根本原因**：
Celery worker 没有运行，异步任务无法执行

---

## ✅ 已应用的修复

**改为同步生成报告**（不依赖 Celery）

修改了 `backend/app/api/v1/reports.py`，将异步任务改为同步执行：
- 直接在 API 中调用 AI 生成报告
- 不再依赖 Celery worker
- 适合快速测试和小规模使用

---

## 🚀 立即执行

### 1. 重启后端服务

**如果使用 Docker:**
```bash
docker-compose restart backend
docker-compose logs -f backend
```

**如果直接运行:**
```bash
# 按 Ctrl+C 停止当前进程
# 然后重新启动
cd backend
uvicorn app.main:app --reload
```

### 2. 清除浏览器缓存

```javascript
// 在浏览器控制台（F12）中执行
localStorage.clear()
```

### 3. 重新测试

1. 刷新页面
2. 重新填写测评表单
3. 提交并等待报告生成
4. 这次应该能看到报告内容了

---

## 📊 预期结果

### 成功的标志：
- ✅ 报告生成完成（不再无限轮询）
- ✅ 能看到报告内容（不再空白）
- ✅ 后端日志显示 AI 调用过程

### 后端日志示例：
```
INFO: 开始生成报告
INFO: 调用 DeepSeek API
INFO: DeepSeek API 调用成功
INFO: 报告生成完成
INFO: "POST /api/v1/reports HTTP/1.1" 202 Accepted
INFO: "GET /api/v1/reports/tasks/xxx HTTP/1.1" 200 OK (status: completed)
```

---

## 🔄 两种方案对比

### 方案1：同步生成（当前已应用）
**优点**：
- ✅ 不需要 Celery worker
- ✅ 部署简单
- ✅ 适合快速测试

**缺点**：
- ❌ API 响应时间长（5-10秒）
- ❌ 并发能力有限
- ❌ 不适合大规模使用

### 方案2：异步生成（需要 Celery）
**优点**：
- ✅ API 立即返回
- ✅ 并发能力强
- ✅ 适合生产环境

**缺点**：
- ❌ 需要运行 Celery worker
- ❌ 需要 Redis
- ❌ 部署复杂

---

## 🎯 如果想使用 Celery（可选）

### 启动 Celery Worker

**方法1：直接运行**
```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info
```

**方法2：使用 Docker Compose**

在 `backend/docker-compose.yml` 中添加 Celery 服务：
```yaml
services:
  celery:
    build: .
    command: celery -A app.tasks.celery_app worker --loglevel=info
    depends_on:
      - redis
      - postgres
    env_file:
      - .env
```

然后运行：
```bash
docker-compose up -d celery
```

### 恢复异步模式

如果 Celery worker 正常运行，可以恢复使用异步任务：
1. 将 `backend/app/api/v1/reports.py` 改回使用 Celery
2. 重启后端服务

---

## 🐛 故障排查

### 问题1：报告仍然空白

**检查**：
```bash
# 1. 查看后端日志
docker-compose logs backend | tail -50

# 2. 检查任务状态
curl http://localhost:8000/api/v1/reports/tasks/YOUR_TASK_ID

# 3. 查看浏览器控制台
# 按 F12，查看 Console 和 Network 标签
```

### 问题2：DeepSeek API 调用失败

**检查**：
```bash
# 测试 API Key
curl https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer sk-ee08eb8ba6d343f582b6a61209b94654" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"测试"}],"max_tokens":50}'
```

如果 API Key 无效，报告会使用降级方案（基础算法）。

### 问题3：Redis 连接失败

**检查**：
```bash
# 测试 Redis 连接
redis-cli ping
# 应该返回: PONG

# 或使用 Docker
docker-compose exec redis redis-cli ping
```

---

## 📝 修改的文件

1. ✅ `backend/app/api/v1/reports.py` - 改为同步生成
2. ✅ `backend/.env` - 已创建配置文件

---

## ⏭️ 下一步

1. **立即重启后端服务**
2. **清除浏览器缓存**
3. **重新测试报告生成**
4. **查看报告内容是否正常显示**

如果测试成功，报告应该能正常生成和显示了！

---

**修复时间**: 2026-05-24 12:25
**状态**: ✅ 已修复，等待重启测试
