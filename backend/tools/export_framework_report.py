"""Export a saved synthetic real-model report as a readable, labelled PDF."""
import argparse
from html import escape
import json
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether,
)


INK = colors.HexColor("#2f241b")
ACCENT = colors.HexColor("#9e3f35")
SOFT = colors.HexColor("#fffaf0")
LINE = colors.HexColor("#ead9bf")


def execution_summary(source):
    traces = []
    for path in source.rglob("*.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and value.get("trace", {}).get("request_id"):
            traces.append(value["trace"])
    return {
        "calls": len(traces),
        "input_tokens": sum(item["input_tokens"] for item in traces),
        "output_tokens": sum(item["output_tokens"] for item in traces),
        "model_seconds": round(sum(item["latency_ms"] for item in traces) / 1000, 1),
        "validation_passed": all(item.get("output_validation") == "passed" for item in traces),
    }


def export_markdown(source, manifest, report, summary, execution):
    """Preserve every generated section verbatim; add only navigation and test notes."""
    chapter_titles = {"identity": "第一章 · 你是谁", "challenge": "第二章 · 卡在哪",
                      "direction": "第三章 · 往哪去"}
    lines = ["# 最新技能真实测试报告", "",
        f"> 合成案例，真实模型输出，未经咨询师审核。AI 评分 {summary['scorecard']['total']}/100。交付门槛：{'通过' if summary['scorecard']['passes_threshold'] else '未通过'}。", "",
        "分析日期：2026-10-06。女性，1996-06-15 15:15，济南出生，现居杭州，项目运营。",
        "关注工作透支、边界表达与朋友关系；工作日晚间可用5–10分钟、周末20分钟。全部经历为合成数据。", "",
        "模型：deepseek-v4-flash；使用运行开始时数据库中的最新已发布技能快照。", ""]
    chapter = None
    for fragment in report["fragments"]:
        if fragment.get("chapter") != chapter:
            chapter = fragment.get("chapter")
            lines.extend(["## " + chapter_titles.get(chapter, "报告正文"), ""])
        lines.extend(["### " + fragment["title"], "", fragment["content"], ""])
    lines.extend(["---", "", "## 测试说明与 AI 质检", "",
        "本次测试范围为报告 S1–S6，日历技能不在本次真实模型报告测试范围内。通过生产技能执行器和报告规划、引用与覆盖校验生成本地测试稿，未写入客户报告、未进行客户交付。", "",
        f"真实模型调用 {execution['calls']} 次；生成 {summary['analysis_count']} 个分析片段、{summary['report_count']} 个正文小节。",
        f"输入 {execution['input_tokens']:,} tokens，输出 {execution['output_tokens']:,} tokens；模型调用累计耗时 {execution['model_seconds']} 秒（不是端到端耗时）。", "",
        "程序结构、覆盖和引用校验通过；AI 内容质检未通过。", "",
        "### 冻结的发布版本", "", "| 技能 | 版本 |", "| --- | --- |"])
    for key, value in manifest["skills"].items():
        lines.append(f"| {key} | {value['publication']['version']} |")
    lines.extend(["", "### AI 评分", "", "| 维度 | 得分 | 原因 |", "| --- | --- | --- |"])
    for item in summary["scorecard"]["dimensions"].values():
        lines.append(f"| {item['label']} | {item['score']}/{item['max_score']} | {item['reason']} |")
    lines.extend(["", f"总分：{summary['scorecard']['total']}/100。交付门槛要求总分≥80、事实忠实度≥16、安全≥8；本次总分与事实忠实度不达标。", "",
        "### 框架覆盖复核", "",
        "下列是独立 AI 对17项报告要求的复核记录，均标记为覆盖；这不等同内容质量通过，也不替代人工审核。", "",
        "| 要求 | AI 状态 | 复核理由 |", "| --- | --- | --- |"])
    for item in summary["framework_review"]:
        lines.append(f"| {item['requirement_id']} | {item['status']} | {item['reason']} |")
    lines.extend(["", "### AI 标记的待复核问题", "",
        "以下保留质检原话。其中对章节边界等问题的判定仍需结合原框架人工核对。", ""])
    for index, issue in enumerate(summary["issues"], 1):
        lines.extend([f"#### {index}. {issue['severity']} · {issue['message']}", "",
            "引用：" + issue.get("evidence", ""), "",
            "复核方向：" + issue.get("suggestion", ""), ""])
    lines.extend(["人工审核状态：未审核。", "",
        "原始输出与请求追踪保存在本目录中的 S1–S6、fragments 和 manifest 文件；正文排版没有修改模型原文。", ""])
    (source / "report.md").write_text("\n".join(lines), encoding="utf-8")


def inline(value):
    text = escape(value)
    # Preserve emphasis without relying on a synthetic heavy Chinese font.
    text = re.sub(r"\*\*(.+?)\*\*", r'<font color="#9e3f35">\1</font>', text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


def styles():
    font_dir = Path("C:/Windows/Fonts")
    pdfmetrics.registerFont(TTFont("ReportBody", str(font_dir / "msyh.ttc"), subfontIndex=0))
    pdfmetrics.registerFont(TTFont("ReportDisplay", str(font_dir / "simsun.ttc"), subfontIndex=0))
    body = ParagraphStyle("Body", fontName="ReportBody", fontSize=10.5, leading=19,
        textColor=INK, spaceAfter=9, wordWrap="CJK", alignment=TA_LEFT)
    return {
        "body": body,
        "small": ParagraphStyle("Small", parent=body, fontSize=8.5, leading=14, spaceAfter=7),
        "title": ParagraphStyle("Title", parent=body, fontName="ReportDisplay", fontSize=23,
            leading=32, spaceAfter=18, keepWithNext=True),
        "chapter": ParagraphStyle("Chapter", parent=body, fontName="ReportDisplay", fontSize=19,
            leading=27, spaceAfter=14, keepWithNext=True),
        "section": ParagraphStyle("Section", parent=body, fontName="ReportDisplay", fontSize=14,
            leading=22, spaceBefore=13, spaceAfter=10, keepWithNext=True),
        "subhead": ParagraphStyle("Subhead", parent=body, fontSize=11.5,
            leading=20, spaceBefore=8, spaceAfter=7, keepWithNext=True),
        "note": ParagraphStyle("Note", parent=body, fontSize=9.5, leading=17,
            textColor=ACCENT, borderColor=LINE, borderWidth=0.7, borderPadding=10,
            backColor=SOFT, spaceAfter=16),
    }


def markdown_story(text, role_styles, width):
    lines = text.splitlines()
    story, buffer = [], []

    def flush():
        if buffer:
            story.append(Paragraph(inline(" ".join(buffer)), role_styles["body"]))
            buffer.clear()

    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            flush()
        elif line.startswith("|"):
            flush()
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[:\- ]+", cell) for cell in cells):
                    rows.append([Paragraph(inline(cell), role_styles["small"]) for cell in cells])
                index += 1
            if rows:
                count = len(rows[0])
                rows = [row + [""] * (count - len(row)) for row in rows]
                table = Table(rows, colWidths=[width / count] * count, repeatRows=1, hAlign="LEFT")
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), SOFT),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.5, LINE),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]))
                story.extend([table, Spacer(1, 9)])
            continue
        elif re.match(r"^#{1,6}\s+", line):
            flush()
            heading = re.sub(r"^#+\s+", "", line)
            story.append(Paragraph(inline(heading), role_styles["subhead"]))
        elif line.startswith(">"):
            flush()
            story.append(Paragraph(inline(line.lstrip("> ")), role_styles["note"]))
        elif re.match(r"^(?:[-*] |\d+[.、] )", line):
            flush()
            story.append(Paragraph(inline(line), role_styles["body"]))
        elif line in {"---", "***"}:
            flush()
            story.append(Spacer(1, 8))
        else:
            buffer.append(line)
        index += 1
    flush()
    return story


def export(source, destination):
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    case = json.loads((source / "input.json").read_text(encoding="utf-8"))
    report = json.loads((source / "S5-report.json").read_text(encoding="utf-8"))
    summary_path = source / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else None
    execution = execution_summary(source)
    role_styles = styles()
    destination.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(destination), pagesize=A4,
        leftMargin=24*mm, rightMargin=24*mm, topMargin=22*mm, bottomMargin=22*mm,
        title="辰鉴·人生说明书 | 最新技能真实测试报告", author="辰鉴 / 合成案例测试")
    story = [
        Paragraph("辰鉴·人生说明书", role_styles["title"]),
        Paragraph("最新技能真实测试报告 · 2026年10月6日", role_styles["section"]),
        Paragraph("测试用途 · 合成案例 · 未经咨询师人工审核<br/>"
            "以下正文由真实模型调用生成，供评估最新技能内容与报告质量使用。AI 质检结论不等同人工签核，本文不可作为客户交付报告。",
            role_styles["note"]),
        Paragraph("案例简介", role_styles["subhead"]),
        Paragraph("1996年6月15日 15:15，女性；出生地济南，现居杭州，项目运营。"
            "关注工作透支、边界表达、朋友关系中的反复模式；可用练习时间为工作日晚间5–10分钟、周末20分钟。"
            "这些资料和经历全部为合成测试数据。", role_styles["body"]),
        Paragraph("分析日期：" + case["context"]["analysis_date"] + "。模型：deepseek-v4-flash。", role_styles["small"]),
    ]
    chapter = None
    titles = {"identity": "第一章 · 你是谁", "challenge": "第二章 · 卡在哪",
              "direction": "第三章 · 往哪去", "ending": "结语", "overview": "你的整体心灵结构"}
    for fragment in report["fragments"]:
        current = fragment.get("chapter")
        if current != chapter:
            if chapter is not None:
                story.append(PageBreak())
            story.append(Paragraph(titles.get(current, "你的整体心灵结构"), role_styles["chapter"]))
            chapter = current
        story.append(Paragraph(inline(fragment["title"]), role_styles["section"]))
        story.extend(markdown_story(fragment["content"], role_styles, doc.width))
    story.extend([PageBreak(), Paragraph("测试说明与 AI 质检", role_styles["chapter"])])
    story.append(Paragraph("以下内容用于说明这份测试稿的来源和当前质量状态，不属于报告正文。", role_styles["small"]))
    story.append(Paragraph("执行范围与链路结果", role_styles["section"]))
    story.append(Paragraph("本次范围为报告 S1–S6，日历技能不在本次真实模型测试范围内。"
        "使用运行开始时数据库中最新已发布技能的冻结快照，经生产技能执行器生成本地测试稿；未写入客户报告、未向客户交付。", role_styles["body"]))
    story.append(Paragraph(f"真实模型调用 {execution['calls']} 次；输入 {execution['input_tokens']:,} tokens，"
        f"输出 {execution['output_tokens']:,} tokens；模型调用累计耗时 {execution['model_seconds']} 秒（非端到端耗时）。", role_styles["body"]))
    if summary:
        story.append(Paragraph(f"生成 {summary['analysis_count']} 个分析片段、{summary['report_count']} 个正文小节。"
            "程序结构、覆盖和引用校验通过；独立 AI 将17项报告框架要求标记为覆盖，但内容质检未通过。", role_styles["body"]))
        story.append(Paragraph("交付门槛要求总分≥80、事实忠实度≥16、安全≥8；本次总分与事实忠实度不达标。"
            "质检意见仍需结合原框架人工复核。", role_styles["note"]))
    story.append(Paragraph("使用的最新发布技能", role_styles["section"]))
    names = {"report.s1_foundation_analysis": "命理基础", "report.s2_psychology_mapping": "心理映射",
        "report.s3_integration": "三重整合", "report.s4_mechanism_block_action": "机制、卡点与行动",
        "report.narrative_plan": "报告主线", "report.fragment_authoring": "报告写作",
        "report.final_validator": "独立质检"}
    for key, value in manifest["skills"].items():
        publication = value.get("publication") or {}
        story.append(Paragraph(f"{names.get(key, key)}：第 {publication.get('version', '?')} 版", role_styles["body"]))
    if summary:
        scorecard = summary["scorecard"]
        story.append(Paragraph(f"AI 评分：{scorecard['total']} / 100", role_styles["section"]))
        for item in scorecard["dimensions"].values():
            story.append(Paragraph(inline(f"{item['label']}：{item['score']} / {item['max_score']}。{item['reason']}"), role_styles["body"]))
        issues = summary.get("issues") or []
        story.append(Paragraph(f"AI 标记的待复核问题：{len(issues)} 项", role_styles["section"]))
        for index, issue in enumerate(issues, 1):
            story.append(KeepTogether([
                Paragraph(inline(f"{index}. [{issue.get('severity')}] {issue.get('message')}"), role_styles["body"]),
                Paragraph(inline("复核方向：" + issue.get("suggestion", "")), role_styles["small"]),
            ]))
    else:
        story.append(Paragraph("正文已生成，独立 AI 质检尚未完成。", role_styles["note"]))
    story.append(Paragraph("人工审核状态：未审核。", role_styles["note"]))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(24*mm, 17*mm, A4[0]-24*mm, 17*mm)
        canvas.setFont("ReportBody", 8)
        canvas.setFillColor(INK)
        canvas.drawString(24*mm, 12*mm, "辰鉴 | 合成测试稿 · 未经人工审核")
        canvas.drawRightString(A4[0]-24*mm, 12*mm, str(document.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    if summary:
        export_markdown(source, manifest, report, summary, execution)
    print(f"Exported PDF: {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    export(args.source, args.output)
