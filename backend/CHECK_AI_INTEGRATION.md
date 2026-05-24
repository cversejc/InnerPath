# AI 集成检查清单

## 已完成的修复

### 1. ✅ 修复 403 错误（游客模式）
**问题**: 用户未登录时生成报告返回 403 Forbidden
**解决方案**: 
- 修改 `backend/app/api/v1/reports.py` - 移除认证要求
- 修改 `backend/app/tasks/report_tasks.py` - 支持 user_id=None 的游客用户
- 游客报告临时存储在 Redis 缓存中（1小时）

### 2. ✅ 增强 AI Prompt
**改进内容**:
- 更专业的系统提示词，强调深度整合传统命理与现代心理学
- 详细的报告结构要求，包含：
  - 能量内核（八字分析）
  - 人生剧场（紫微斗数）
  - 心智模式与成长导航（心理学整合）
  - 针对关注议题的深度建议
- 要求实际推算八字和紫微命盘
- 每个分析都要说明"为什么"和"怎么做"
- max_tokens 从 2000 提升到 4000

### 3. ✅ 修复前端数据显示问题
**改进内容**:
- `src/utils/aiService.js` - 添加 `formatReportForFrontend()` 函数处理数据格式
- `src/views/ReportDetail.vue` - 添加 `normalizeReportData()` 标准化数据结构
- 改进 Markdown 渲染逻辑
- 添加空值检查，防止页面空白

## 如何验证 AI 是否被调用

### 方法 1: 查看后端日志
```bash
# 在后端容器或进程中查看日志
# 如果看到 "DeepSeek API call failed"，说明尝试调用了但失败
# 如果没有任何 DeepSeek 相关日志，说明直接使用了降级方案
```

### 方法 2: 检查生成的报告内容
**AI 生成的报告特征**:
- 包含 `aiGeneratedContent` 字段且不为空
- 内容深度高，包含八字、紫微斗数的具体分析
- 有明确的"为什么"和"怎么做"
- 语言专业且温暖

**降级方案（基础算法）的特征**:
- `aiGeneratedContent` 为 null
- 只有简单的五行分类
- 内容较为模板化

### 方法 3: 检查 DeepSeek API 配置
```bash
# 检查环境变量
cd backend
cat .env | grep DEEPSEEK

# 应该看到:
# DEEPSEEK_API_KEY=sk-xxxxxx
# DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
# DEEPSEEK_MODEL=deepseek-chat
```

### 方法 4: 测试 API 调用
```bash
# 使用 curl 测试 DeepSeek API
curl https://api.deepseek.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 100
  }'
```

## 常见问题排查

### 问题 1: API Key 无效
**症状**: 报告生成成功但内容简单，没有深度分析
**检查**:
1. 确认 `.env` 文件中的 `DEEPSEEK_API_KEY` 是否正确
2. 检查 API Key 是否过期或额度用完
3. 访问 DeepSeek 控制台确认 API Key 状态

### 问题 2: 网络连接问题
**症状**: 报告生成时间长或超时
**检查**:
1. 服务器能否访问 `api.deepseek.com`
2. 是否需要配置代理
3. 防火墙是否阻止了出站连接

### 问题 3: 报告显示空白（网页版）
**症状**: 手机端正常，网页版空白
**原因**: 数据结构不匹配或字段名差异（snake_case vs camelCase）
**解决**: 已通过 `normalizeReportData()` 函数修复

## 下一步建议

### 1. 添加日志记录
在 `backend/app/services/ai_service.py` 中添加详细日志：
```python
import logging
logger = logging.getLogger(__name__)

# 在 generate_report_with_ai 函数中
logger.info(f"Calling DeepSeek API with prompt length: {len(prompt)}")
logger.info(f"DeepSeek API response received, content length: {len(ai_content)}")
```

### 2. 添加监控指标
- AI 调用成功率
- AI 调用平均耗时
- 降级方案使用率

### 3. 优化降级策略
当前降级方案过于简单，建议：
- 使用更复杂的算法（真实的八字排盘）
- 提供更有价值的基础分析
- 明确告知用户使用了降级方案

### 4. 用户反馈收集
- 添加报告评分功能
- 收集用户对报告质量的反馈
- 根据反馈持续优化 prompt

## 测试步骤

1. **启动后端服务**
   ```bash
   cd backend
   docker-compose up -d
   # 或
   uvicorn app.main:app --reload
   ```

2. **启动前端服务**
   ```bash
   npm run dev
   ```

3. **生成测试报告**
   - 访问 http://localhost:3000
   - 填写测评表单
   - 提交并等待报告生成

4. **检查报告内容**
   - 查看是否有 "AI 深度分析" 标签
   - 检查内容深度和专业性
   - 确认网页版和手机端都能正常显示

5. **查看后端日志**
   ```bash
   docker-compose logs -f backend
   # 查找 DeepSeek 相关日志
   ```

## 配置文件位置

- 后端环境变量: `backend/.env`
- 前端环境变量: `.env.development` / `.env.production`
- AI 服务配置: `backend/app/config.py`
- AI 服务实现: `backend/app/services/ai_service.py`
- 报告生成任务: `backend/app/tasks/report_tasks.py`
- 前端 API 调用: `src/utils/aiService.js`
- 报告详情页面: `src/views/ReportDetail.vue`
