# 多步报告生成系统使用指南

## 概述

新的多步报告生成系统通过三个渐进式步骤生成个性化报告，解决了两个核心问题：
1. **信息过载**：避免一次性投喂所有指令给 AI
2. **忽略用户需求**：针对用户选择的每个议题进行深度分析

## 功能特性

### 三步生成流程

**Step 1: 基础推算（Foundation Calculation）**
- 纯计算八字四柱和紫微命盘
- Temperature: 0.2（精确计算）
- 输出 JSON 格式
- 不做任何解读

**Step 2: 能量特质解读（Energy Profile Analysis）**
- 基于 Step 1 的命理基础解读能量特质
- 包含：核心驱动力、思维模式、能量平衡点、人生主题
- Temperature: 0.7
- 用户关注领域作为背景上下文

**Step 3: 议题深度分析（Topic-Specific Deep Dive）**
- 针对用户选择的每个议题生成独立分析章节
- 每个议题包含：
  - 模式识别（200-250字）
  - 心理机制（200-250字）
  - 具体行动方案（300-400字，3-5个可操作步骤）
  - 成长资源（100-150字）
- 深度整合用户的补充说明
- Temperature: 0.7
- Token 数量根据议题数量动态调整

### 美化展示

**结构化内容展示**：
- ✨ 能量特质卡片：带图标的子章节卡片，悬停效果
- 💼 议题分析卡片：每个议题独立展示，清晰分层
- ✅ 行动清单：可勾选的行动项，完成后划线
- 🌟 总结寄语：高亮核心信念和成长方向

**视觉优化**：
- 渐变背景色
- 图标标识（⚡ 核心驱动力、🧠 思维模式、💕 关系模式等）
- 悬停动画效果
- 响应式布局

## 启用方法

### 1. 设置环境变量

在后端 `.env` 文件中添加：

```bash
USE_MULTISTEP_GENERATION=true
```

或在系统环境变量中设置：

```bash
export USE_MULTISTEP_GENERATION=true  # Linux/Mac
set USE_MULTISTEP_GENERATION=true     # Windows CMD
$env:USE_MULTISTEP_GENERATION="true"  # Windows PowerShell
```

### 2. 重启后端服务

```bash
cd backend
# 如果使用 Docker
docker-compose restart

# 如果直接运行
# 停止现有进程，然后重新启动
uvicorn app.main:app --reload
```

### 3. 重启 Celery Worker

```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info
```

## 测试方法

### 测试场景 1：单个议题

**输入**：
- 出生信息：1990年1月1日
- 选择议题：职业发展
- 补充说明："感觉工作没有成就感，想换工作但不知道方向"

**预期输出**：
- 报告包含"针对【职业发展】的深度分析"章节
- 模式识别中提到"成就感"
- 具体行动方案包含 3-5 个可操作步骤
- 前端显示可勾选的行动清单

### 测试场景 2：多个议题

**输入**：
- 出生信息：1985年6月15日
- 选择议题：职业发展、亲密关系、压力焦虑
- 补充说明："工作压力大，影响了和伴侣的关系"

**预期输出**：
- 报告包含 3 个独立的议题分析章节
- 每个议题都有完整的 4 个子章节
- 补充说明中的"压力"和"伴侣"在相关议题中被引用
- 前端显示 3 个独立的议题卡片

### 测试场景 3：无补充说明

**输入**：
- 出生信息：1995年12月20日
- 选择议题：个人成长
- 补充说明：（空）

**预期输出**：
- 报告仍然生成完整的个人成长分析
- 基于命理配置提供通用但深度的分析
- 不会因为缺少补充说明而降低质量

## 性能对比

| 指标 | 单步生成 | 多步生成 |
|------|---------|---------|
| 生成时间 | ~30秒 | ~60-80秒 |
| Token 消耗 | ~4000 | ~6000 |
| API 调用次数 | 1 | 3 |
| 议题覆盖率 | 低（泛泛而谈） | 高（每个议题独立分析） |
| 补充说明整合 | 低 | 高（深度整合到具体情境） |
| 个性化程度 | 中 | 高 |

## 降级策略

系统具有多层降级保护：

1. **多步生成失败** → 自动降级到单步生成
2. **单步生成失败** → 使用基础算法生成简化报告
3. **Step 1 失败** → 使用简化计算
4. **Step 2/3 失败** → 降级到单步方法

## 前端展示逻辑

前端会按以下优先级展示报告：

1. **优先**：`structuredSections` 存在 → 使用美化的结构化展示
2. **次选**：`aiGeneratedContent` 存在 → 使用 Markdown 渲染
3. **降级**：使用旧版结构化字段（`energyProfile`, `careerGuidance` 等）

## 日志监控

启用多步生成后，查看日志确认运行状态：

```bash
# 后端日志
tail -f backend/logs/app.log

# Celery 日志
tail -f backend/logs/celery.log
```

关键日志标识：
- `使用多步生成模式` - 多步生成已启用
- `Step 1: 推算命理基础...` - Step 1 开始
- `Step 2: 解读能量特质...` - Step 2 开始
- `Step 3: 分析关注议题...` - Step 3 开始
- `多步报告生成完成` - 成功完成
- `多步生成失败，降级到单步模式` - 降级

## 数据结构

### 后端返回结构

```json
{
  "basic_info": {
    "name": "用户名",
    "birth_date": "1990-01-01",
    "report_date": "2026-05-24",
    "generated_by": "DeepSeek AI (Multi-Step)"
  },
  "structured_sections": {
    "foundation": {
      "title": "命理基础",
      "type": "foundation",
      "data": { /* 八字和紫微数据 */ }
    },
    "energy": {
      "title": "能量特质解读",
      "type": "energy",
      "subsections": [
        {
          "title": "核心驱动力",
          "icon": "⚡",
          "content": "..."
        },
        {
          "title": "思维模式",
          "icon": "🧠",
          "content": "..."
        }
      ]
    },
    "topics": [
      {
        "title": "职业发展",
        "icon": "💼",
        "type": "topic",
        "subsections": [
          {
            "title": "模式识别",
            "content": "..."
          },
          {
            "title": "具体行动方案",
            "content": "...",
            "actions": [
              { "text": "每天...", "completed": false }
            ]
          }
        ]
      }
    ],
    "summary": {
      "title": "总结与寄语",
      "icon": "🌟",
      "type": "summary",
      "content": "...",
      "core_beliefs": "...",
      "growth_direction": "..."
    }
  },
  "ai_generated_content": "完整的 Markdown 内容",
  "energy_profile": { /* 兼容旧版 */ },
  "career_guidance": { /* 兼容旧版 */ },
  "relationship_pattern": { /* 兼容旧版 */ },
  "personal_growth": { /* 兼容旧版 */ },
  "summary": "总结文本"
}
```

## 常见问题

### Q: 多步生成比单步慢很多，用户会不会不满意？

A: 虽然时间增加了一倍（30秒 → 60-80秒），但：
1. 报告质量显著提升，用户愿意等待高质量内容
2. 前端显示具体进度："推算命理基础..." → "解读能量特质..." → "分析关注议题..."
3. 用户能看到系统在做什么，不是黑盒等待

### Q: API 成本增加了 50%，值得吗？

A: 值得。当前最大问题是用户选择议题但报告不回应，导致用户流失。解决后用户留存率会显著提升，ROI 为正。

### Q: 如何回退到单步生成？

A: 设置环境变量 `USE_MULTISTEP_GENERATION=false` 或删除该环境变量，然后重启服务即可。

### Q: 前端如何判断是否使用新版展示？

A: 前端检查 `report.structuredSections` 是否存在。存在则使用新版美化展示，否则降级到旧版展示。

## 下一步优化

1. **缓存 Step 1 结果**：相同出生信息的基础推算可以缓存
2. **并行处理 Step 3**：不同议题的分析可以并行调用 API
3. **流式输出**：边生成边展示，提升用户体验
4. **A/B 测试**：对比单步和多步的用户满意度和留存率

## 技术支持

如有问题，请查看：
- 后端日志：`backend/logs/app.log`
- Celery 日志：`backend/logs/celery.log`
- 前端控制台：浏览器开发者工具

或联系开发团队。
