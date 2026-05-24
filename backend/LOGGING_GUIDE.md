# 📊 日志系统完整指南

## 系统概述

已为 InnerSeek 项目实现了完整的日志系统，包括：
- ✅ 彩色控制台输出
- ✅ 分级文件日志（所有日志、错误日志、API日志）
- ✅ 请求/响应日志中间件
- ✅ 外部API调用日志
- ✅ 数据库操作日志
- ✅ 详细的错误追踪

---

## 日志文件结构

```
backend/logs/
├── innerseek_all.log      # 所有日志（DEBUG及以上）
├── innerseek_error.log    # 错误日志（ERROR及以上）
└── innerseek_api.log      # API调用日志（INFO及以上）
```

每个日志文件：
- 最大 10MB
- 自动轮转，保留 5 个备份
- UTF-8 编码

---

## 日志级别

### DEBUG
详细的调试信息，包括：
- 函数参数
- 中间变量
- 数据结构内容

### INFO
重要的业务流程信息，包括：
- 请求开始/完成
- API调用成功
- 数据库操作成功
- 业务流程关键节点

### WARNING
警告信息，不影响运行但需要注意：
- 使用降级方案
- 数据未找到
- 配置缺失

### ERROR
错误信息，影响功能但不崩溃：
- API调用失败
- 数据库操作失败
- 业务逻辑错误

### CRITICAL
严重错误，可能导致系统崩溃：
- 系统级错误
- 资源耗尽

---

## 日志格式

### 控制台输出（彩色）
```
12:34:56 | INFO     | 请求开始 | GET /api/v1/reports | 客户端: 127.0.0.1
12:34:57 | INFO     | 请求完成 | GET /api/v1/reports | 状态: 200 | 耗时: 123.45ms
```

### 文件输出（详细）
```
2026-05-24 12:34:56 | INFO     | app.api.v1.reports:45 | 开始生成报告，task_id: xxx
2026-05-24 12:34:57 | INFO     | app.services.ai_service:23 | 调用 DeepSeek API | URL: https://api.deepseek.com/v1/chat/completions
2026-05-24 12:35:02 | INFO     | app.services.ai_service:56 | DeepSeek API 调用成功 | 响应长度: 3456 字符
```

---

## 关键日志点

### 1. 应用启动/关闭
```python
# app/main.py
INFO: 应用启动中...
INFO: Redis 连接已建立
INFO: 应用启动完成 | 环境: development | 调试模式: True
INFO: 应用关闭中...
INFO: 应用已关闭
```

### 2. HTTP 请求
```python
# 自动记录所有请求
INFO: 请求开始 | POST /api/v1/reports | 客户端: 172.18.0.1 | ID: 1716532456.789
INFO: 请求完成 | POST /api/v1/reports | 状态: 202 | 耗时: 5234.56ms | ID: 1716532456.789
```

### 3. 报告生成流程
```python
# app/api/v1/reports.py
INFO: 开始生成报告，task_id: 6b9636fd-9941-49ce-a8a9-d74d51d8b7fe
INFO: 调用 AI 生成报告...
INFO: 报告生成完成，耗时: 5234ms
INFO: 报告数据键: ['basic_info', 'energy_profile', 'career_guidance', ...]
INFO: 游客报告已缓存，task_id: 6b9636fd-9941-49ce-a8a9-d74d51d8b7fe
INFO: 报告数据已添加到状态响应
INFO: 任务状态已更新为 completed
```

### 4. DeepSeek API 调用
```python
# app/services/ai_service.py
INFO: 开始生成 AI 报告 | 用户: 测试用户
DEBUG: Prompt 长度: 2345 字符
INFO: 外部 API 调用开始: DeepSeek API
INFO: 调用 DeepSeek API | URL: https://api.deepseek.com/v1/chat/completions
INFO: DeepSeek API 调用成功 | 响应长度: 3456 字符
DEBUG: AI 响应预览: ## 一、能量内核（基于八字分析）...
INFO: AI 报告解析完成 | 包含字段: ['basic_info', 'energy_profile', ...]
INFO: 外部 API 调用成功: DeepSeek API | 耗时: 5234.56ms
```

### 5. 降级方案
```python
# 当 DeepSeek API 失败时
ERROR: DeepSeek API HTTP 错误 | 状态码: 401 | 响应: {"error": "Invalid API key"}
WARNING: 使用降级方案生成报告
INFO: 使用基础算法生成报告（降级方案）
DEBUG: 出生日期: 1990-5-15
INFO: 主导五行: wood
```

### 6. 数据库操作
```python
# app/services/report_service.py
INFO: 创建报告 | 用户ID: 123 | 生成耗时: 5234ms
DEBUG: 出生日期: 1990-05-15
INFO: 报告创建成功 | 报告ID: 456

DEBUG: 查询报告 | 报告ID: 456 | 用户ID: 123
INFO: 报告查询成功 | 报告ID: 456
```

### 7. 错误处理
```python
# 全局异常捕获
ERROR: 全局异常捕获 | POST /api/v1/reports | 错误类型: ValueError | 错误信息: Invalid date format
Traceback (most recent call last):
  File "app/api/v1/reports.py", line 45, in create_report
    ...
ValueError: Invalid date format
```

---

## 使用方法

### 在代码中使用日志

```python
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# 基本日志
logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")

# 带变量的日志
logger.info(f"用户登录 | 用户ID: {user_id} | IP: {ip_address}")

# 带异常追踪的日志
try:
    # some code
    pass
except Exception as e:
    logger.error(f"操作失败: {str(e)}", exc_info=True)
```

### 使用装饰器记录 API 调用

```python
from app.core.logging_config import log_api_call, log_external_api

# 记录内部 API 调用
@log_api_call
async def my_api_function():
    # 自动记录开始、结束、耗时
    pass

# 记录外部 API 调用
@log_external_api("OpenAI API")
async def call_openai():
    # 自动记录外部 API 调用
    pass
```

---

## 查看日志

### 实时查看所有日志
```bash
tail -f backend/logs/innerseek_all.log
```

### 实时查看错误日志
```bash
tail -f backend/logs/innerseek_error.log
```

### 实时查看 API 日志
```bash
tail -f backend/logs/innerseek_api.log
```

### 搜索特定内容
```bash
# 搜索 DeepSeek 相关日志
grep -i "deepseek" backend/logs/innerseek_all.log

# 搜索错误日志
grep -i "error" backend/logs/innerseek_all.log

# 搜索特定 task_id
grep "6b9636fd-9941-49ce-a8a9-d74d51d8b7fe" backend/logs/innerseek_all.log
```

### 查看最近的错误
```bash
tail -100 backend/logs/innerseek_error.log
```

---

## 日志分析示例

### 示例 1: 追踪完整的报告生成流程

```bash
# 使用 task_id 追踪
grep "6b9636fd-9941-49ce-a8a9-d74d51d8b7fe" backend/logs/innerseek_all.log
```

输出：
```
2026-05-24 12:34:56 | INFO | 开始生成报告，task_id: 6b9636fd-9941-49ce-a8a9-d74d51d8b7fe
2026-05-24 12:34:56 | INFO | 调用 AI 生成报告...
2026-05-24 12:35:01 | INFO | DeepSeek API 调用成功 | 响应长度: 3456 字符
2026-05-24 12:35:01 | INFO | 报告生成完成，耗时: 5234ms
2026-05-24 12:35:01 | INFO | 游客报告已缓存，task_id: 6b9636fd-9941-49ce-a8a9-d74d51d8b7fe
2026-05-24 12:35:01 | INFO | 任务状态已更新为 completed
```

### 示例 2: 查看 API 调用统计

```bash
# 统计 DeepSeek API 调用次数
grep "DeepSeek API 调用成功" backend/logs/innerseek_api.log | wc -l

# 统计失败次数
grep "DeepSeek API 调用失败" backend/logs/innerseek_api.log | wc -l

# 查看平均耗时
grep "DeepSeek API 调用成功" backend/logs/innerseek_api.log | grep -oP "耗时: \K[0-9.]+" | awk '{sum+=$1; count++} END {print sum/count "ms"}'
```

### 示例 3: 查看错误趋势

```bash
# 按小时统计错误数量
grep "ERROR" backend/logs/innerseek_error.log | cut -d' ' -f1-2 | cut -d':' -f1 | uniq -c
```

---

## 配置调整

### 修改日志级别

编辑 `backend/.env`:
```bash
# 开发环境：详细日志
LOG_LEVEL=DEBUG

# 生产环境：精简日志
LOG_LEVEL=INFO
```

### 修改日志格式

编辑 `backend/app/core/logging_config.py`:
```python
# 修改详细格式
detailed_format = logging.Formatter(
    fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(funcName)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 修改简单格式
simple_format = ColoredFormatter(
    fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
```

### 添加新的日志文件

```python
# 在 setup_logging() 中添加
performance_log_file = log_path / f"{app_name.lower()}_performance.log"
performance_handler = RotatingFileHandler(
    performance_log_file,
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding='utf-8'
)
performance_handler.setLevel(logging.INFO)
performance_handler.setFormatter(detailed_format)

# 创建专门的 logger
perf_logger = logging.getLogger('performance')
perf_logger.addHandler(performance_handler)
```

---

## 性能影响

### 日志系统性能开销

- **控制台输出**: ~0.1ms per log
- **文件写入**: ~0.5ms per log
- **异步日志**: 可进一步优化（未实现）

### 建议

1. **开发环境**: 使用 DEBUG 级别，查看所有细节
2. **生产环境**: 使用 INFO 级别，减少日志量
3. **高并发场景**: 考虑使用异步日志或日志采样

---

## 故障排查流程

### 1. 报告生成失败

```bash
# 查看完整流程
grep "task_id: YOUR_TASK_ID" backend/logs/innerseek_all.log

# 查看错误
grep "task_id: YOUR_TASK_ID" backend/logs/innerseek_error.log
```

### 2. DeepSeek API 问题

```bash
# 查看所有 DeepSeek 调用
grep -i "deepseek" backend/logs/innerseek_api.log

# 查看失败的调用
grep "DeepSeek API 调用失败" backend/logs/innerseek_error.log
```

### 3. 性能问题

```bash
# 查看慢请求（耗时 > 5000ms）
grep "耗时:" backend/logs/innerseek_all.log | awk -F'耗时: ' '{print $2}' | awk -F'ms' '$1 > 5000 {print}'

# 查看 API 调用耗时
grep "外部 API 调用成功" backend/logs/innerseek_api.log
```

---

## 日志轮转和清理

### 自动轮转
日志文件达到 10MB 时自动轮转，保留 5 个备份：
```
innerseek_all.log
innerseek_all.log.1
innerseek_all.log.2
innerseek_all.log.3
innerseek_all.log.4
innerseek_all.log.5
```

### 手动清理旧日志
```bash
# 删除 7 天前的日志
find backend/logs -name "*.log.*" -mtime +7 -delete

# 压缩旧日志
find backend/logs -name "*.log.*" -mtime +1 -exec gzip {} \;
```

---

## 最佳实践

### 1. 日志内容
- ✅ 记录关键业务流程
- ✅ 记录外部依赖调用
- ✅ 记录错误和异常
- ❌ 不记录敏感信息（密码、token）
- ❌ 不记录大量重复信息

### 2. 日志级别选择
- DEBUG: 开发调试
- INFO: 业务流程
- WARNING: 异常但可恢复
- ERROR: 错误需要关注
- CRITICAL: 严重错误

### 3. 日志格式
- 使用结构化信息（key: value）
- 包含上下文（user_id, task_id）
- 便于搜索和分析

### 4. 性能考虑
- 避免在循环中大量日志
- 使用合适的日志级别
- 考虑异步日志（高并发场景）

---

## 总结

✅ **已实现的功能**:
- 完整的日志系统
- 彩色控制台输出
- 分级文件日志
- 请求/响应日志
- API 调用日志
- 错误追踪

✅ **日志覆盖**:
- 应用启动/关闭
- HTTP 请求
- 报告生成流程
- DeepSeek API 调用
- 数据库操作
- 错误处理

✅ **便于排查**:
- 详细的日志信息
- 清晰的日志格式
- 完整的错误追踪
- 便于搜索和分析

---

**创建时间**: 2026-05-24
**版本**: 1.0
