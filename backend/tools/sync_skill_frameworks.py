"""Build the current skill guidance from the two maintained product documents.

Run from the repository: py -3.11 backend/tools/sync_skill_frameworks.py
Use --check to detect a document change that has not been synchronized.
The generated asset is bundled with the backend; runtime never reads docs/tools.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "backend/app/domains/skills/framework_guidance.json"
REPORT_SOURCE = "docs/产品分析框架.md"
CALENDAR_SOURCE = "docs/日历生成思路.md"


def plain(value):
    value = re.sub(r"\\([.+()\-\[\]])", r"\1", value)
    value = re.sub(r"<br\s*/?>", "；", value)
    value = value.replace("**", "").replace("\u200b", "")
    return re.sub(r"\s+", " ", value).strip()


def section(document, prefix):
    lines = document.splitlines()
    for start, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+)", line)
        if match and plain(match[2]).startswith(prefix):
            depth = len(match[1])
            for end in range(start + 1, len(lines)):
                following = re.match(r"^(#{1,6})\s", lines[end])
                if following and len(following[1]) <= depth:
                    return lines[start:end]
            return lines[start:]
    raise ValueError(f"Framework section missing: {prefix}")


def guidance_items(document, prefix, *, rows=False, daily=False):
    lines = section(document, prefix)
    blocks, current, table_headers = [], [], None

    def flush():
        if current:
            text = "；".join(current)
            text = re.sub(r"([。！？；：])；+", r"\1", text)
            blocks.append(text)
            current.clear()

    for line in lines[1:]:
        stripped = line.strip()
        if not stripped or stripped in {"---", ">"} or stripped.startswith("!["):
            continue
        if stripped.startswith("> 目标：") or stripped.startswith("> 审核节点："):
            continue
        if "AI分析框架（指令级prompt）" in stripped:
            continue
        # Fixed output lengths and formatting remain in the program contract.
        if daily and (stripped.startswith("【今日关键词】")
                      or stripped.startswith("【今日色块】只展示")
                      or stripped.startswith("控制在30-60字。")
                      or stripped == "格式："):
            if stripped.startswith("控制在30-60字。"):
                current.append(plain(stripped.split("。", 1)[1]))
            continue
        if stripped.startswith("|"):
            cells = [plain(cell) for cell in stripped.strip("|").split("|")]
            if all(re.fullmatch(r"[-: ]+", cell) for cell in cells):
                continue
            if table_headers is None:
                table_headers = cells
                continue
            text = cells[0] + "：" + "；".join(
                f"{name}：{value}" for name, value in zip(table_headers[1:], cells[1:])
            )
            if rows:
                flush()
                blocks.append(text)
            else:
                current.append(text)
            continue
        table_headers = None
        if re.match(r"^#{4,6}\s", stripped):
            flush()
        elif re.match(r"^\d+\.\s", line):
            flush()
        elif re.match(r"^STEP \d+｜", stripped):
            flush()
        elif re.match(r"^[🟢🔵🟡🔴]", stripped):
            flush()
        elif re.match(r"^\*\*[A-G]\\?\.", stripped):
            flush()
        elif daily and stripped.startswith("【"):
            flush()
        text = re.sub(r"^>\s*", "", stripped)
        text = re.sub(r"^#{1,6}\s*", "", text)
        text = re.sub(r"^(?:- |\d+\. )", "", text)
        text = plain(text)
        if text:
            current.append(text)
    flush()
    items = []
    for block in blocks:
        # Keep each administrator-editable item within the existing API limit.
        chunk = ""
        for part in block.split("；"):
            if len(f"{chunk}；{part}") > 950 and chunk:
                items.append(chunk)
                chunk = ""
            chunk = f"{chunk}；{part}" if chunk else part
        if chunk:
            items.append(chunk)
    return items


REPORT_SKILLS = {
    "report.s1_foundation_analysis": (
        "完成命理层面的基础分析，为后续心理映射提供能量结构和场景依据。",
        ["1.1", "1.2"],
    ),
    "report.s2_psychology_mapping": (
        "将命理信息翻译为心理语言，解读表面性格之下的阴影与情结。",
        ["2.1", "2.2", "2.3", "2.4"],
    ),
    "report.s3_integration": (
        "将命理时序、心理成长、东方哲学融为一体，为用户绘制自性化路线图。",
        ["3.1", "3.2", "3.3", "3.4", "3.5"],
    ),
    "report.s4_mechanism_block_action": (
        "根据前三步与用户问卷，解读心理机制和卡点，给出具体可操作的练习工具、能量管理方案与成长实验。",
        ["4.1", "4.2", "4.3", "4.4", "4.5", "【往哪去】"],
    ),
    "report.narrative_plan": (
        "综合已审核的四步分析与用户问卷，设计围绕核心暗线、贴合用户的报告脉络，做到形散神不散。",
        ["第五步", "5.1", "5.3", "5.4", "5.6", "5.7"],
    ),
    "report.fragment_authoring": (
        "将已审核的分析写成围绕同一暗线的个性化人生说明书，帮助用户认识自己、理解卡点、找到方向并带入现实。",
        ["第五步", "5.1", "5.2", "5.3", "5.4", "5.6", "5.7"],
    ),
    "report.final_validator": (
        "作为独立质量审核员，按分析框架第六步复核报告是否达到可以交付的标准，逐维评分并标出应删的重复内容。",
        ["第六步"],
    ),
}
CALENDAR_SKILLS = {
    "calendar.temporal_analysis": (
        "根据已审核的案例结构与计算好的30天时序，识别每天更容易被激活的能量主题、心理课题和行动节奏。",
        "第一步",
    ),
    "calendar.monthly_tone": (
        "结合人生说明书、当前大运流年、30天分析与现实议题，形成决策日历总基调。",
        "第二步",
    ),
    "calendar.daily_authoring": (
        "把当天主题、行动色块与换气口转译为回应用户长期课题的逐日决策提醒和能量觉察。",
        "第三步",
    ),
    "calendar.calibration": (
        "作为30天成长节奏编辑，校准全月内容的变化、层次与一致性，形成真实成长循环。",
        "第四步",
    ),
}


def build_asset():
    documents = {path: (ROOT / path).read_text(encoding="utf-8-sig")
                 for path in (REPORT_SOURCE, CALENDAR_SOURCE)}
    asset = {"sources": {path: {"sha256": hashlib.sha256(text.encode()).hexdigest()}
                         for path, text in documents.items()}, "skills": {},
             "references": {}}
    report = documents[REPORT_SOURCE]
    core = guidance_items(report, "核心总领")
    boundaries = guidance_items(report, "5.5")
    for key, (objective, sections) in REPORT_SKILLS.items():
        # A parent section also contains its children. Include its introduction
        # only when the children are selected separately, preventing duplication.
        items = list(core)
        for prefix in sections:
            content = report
            if prefix == "第五步":
                content = report.split("### 5\\.1", 1)[0]
            items.extend(guidance_items(content, prefix,
                         rows=prefix in {"2.2", "2.3", "3.2", "3.5", "5.2"}))
        items.extend(boundaries)
        asset["skills"][key] = {"source": REPORT_SOURCE,
            "sections": ["核心总领", *sections, "5.5"],
            "objective": objective, "methodology": items}
    calendar = documents[CALENDAR_SOURCE]
    for key, (objective, prefix) in CALENDAR_SKILLS.items():
        # Later stages inherit the calendar's case-specific interpretation
        # principles, not the implementation details of its analysis output.
        principles = guidance_items(calendar, "【重要原则】")
        items = ([] if prefix == "第一步" else principles)
        items.extend(guidance_items(calendar, prefix, daily=prefix == "第三步"))
        asset["skills"][key] = {"source": CALENDAR_SOURCE,
            "sections": [prefix] if prefix == "第一步" else ["【重要原则】", prefix],
            "objective": objective, "methodology": items}
    for key, guidance in asset["skills"].items():
        if not 1 <= len(guidance["methodology"]) <= 40:
            raise ValueError(f"Invalid item count: {key}: {len(guidance['methodology'])}")
        if any(len(item) > 1000 for item in guidance["methodology"]):
            raise ValueError(f"Oversized item: {key}")
    for prefix, key in (("2.2", "ten_gods"), ("2.3", "stars"), ("3.2", "quadrants")):
        rows = [line.strip().strip("|").split("|")
                for line in section(report, prefix) if line.strip().startswith("|")]
        headers = [plain(value) for value in rows[0]]
        asset["references"][key] = {
            plain(row[0]): {name: plain(value) for name, value in zip(headers[1:], row[1:])}
            for row in rows[2:]
        }
    return asset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    serialized = json.dumps(build_asset(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if OUTPUT.read_text(encoding="utf-8") != serialized:
            raise SystemExit("Skill guidance is out of sync with product documents")
        print("Skill guidance matches both product documents")
    else:
        OUTPUT.write_text(serialized, encoding="utf-8")
        for key, guidance in build_asset()["skills"].items():
            print(f"{key}: {len(guidance['methodology'])} items")


if __name__ == "__main__":
    main()
