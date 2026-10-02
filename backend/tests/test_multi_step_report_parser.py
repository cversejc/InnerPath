from app.domains.reports.generation.multi_step_report_parser import MultiStepReportParser


def test_structured_parser_extracts_topic_sections_actions_and_summary():
    parser = MultiStepReportParser()
    topic_analysis = """## 针对【职业发展】的深度分析
### 1. 模式识别：经验丰富，当前需要收束方向
### 2. 心理机制：担心选择后失去其他可能
### 3. 具体行动方案：
- 列出三个岗位的实际工作内容并进行比较
- 与一位行业从业者进行一次交流
### 4. 成长资源：每周留出时间复盘
## 总结与寄语：
- 核心信念识别：我可以通过行动获得信息
- 成长的核心方向：先完成小范围尝试
"""

    sections = parser._parse_structured_content(
        {"bazi": {"day_master": "甲"}},
        "**核心驱动力**：稳步探索\n**思维模式**：系统分析",
        topic_analysis,
    )

    topic = sections["topics"][0]
    assert topic["title"] == "职业发展"
    assert [section["title"] for section in topic["subsections"]] == [
        "模式识别",
        "心理机制",
        "具体行动方案",
        "成长资源",
    ]
    assert topic["subsections"][2]["actions"] == [
        {"text": "列出三个岗位的实际工作内容并进行比较", "completed": False},
        {"text": "与一位行业从业者进行一次交流", "completed": False},
    ]
    assert sections["summary"]["core_beliefs"] == "我可以通过行动获得信息"
    assert sections["summary"]["growth_direction"] == "先完成小范围尝试"
