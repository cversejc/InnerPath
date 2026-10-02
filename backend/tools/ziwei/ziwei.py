#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Streamlit rendering adapter for the Reports-owned Zi Wei chart calculator."""
import streamlit as st

from app.domains.reports.generation.ziwei_chart import (
    EARTHLY_BRANCHES,
    HEAVENLY_STEMS,
    HOUR_BRANCH_NAMES,
    LUNAR_MONTH_NAMES,
    SIHUA_TABLE,
    STAR_ATTRIBUTES,
    TIANFU_GROUP,
    WU_XING_JU_NAMES,
    ZIWEI_GROUP,
    ZiweiChart,
    ZiweiPalace,
    compute_ziwei_chart,
    _compute_feixing,
)
from astro.ziwei_vietnamese import (
    VIETNAMESE_CULTURAL_NOTE,
    VIETNAMESE_DA_XIAN_TIPS,
    VIETNAMESE_MARRIAGE_COMPAT,
    VIETNAMESE_ZODIAC_NAMES,
    VI_ACCENT_COLOR,
    VI_FLAG,
    VI_STAR_COLOR,
    build_vietnam_mode_header_html,
    get_palace_vietnamese_info,
    get_star_vietnamese_info,
    get_vietnamese_zodiac_name,
    get_zodiac_year_label,
)

compute_ziwei_chart = st.cache_data(ttl=3600, show_spinner=False)(compute_ziwei_chart)
# ============================================================
# 渲染函數 (Rendering)
# ============================================================

def render_ziwei_chart(chart: ZiweiChart, after_chart_hook=None) -> None:
    """渲染完整的紫微斗數命盤。"""
    if chart.vietnam_mode:
        st.markdown(build_vietnam_mode_header_html(), unsafe_allow_html=True)
        st.subheader(f"{VI_FLAG} 越南 Tử Vi Đẩu Số 命盤")
    else:
        st.subheader("🌟 紫微斗數命盤")
    _render_sihua_legend()
    _render_palace_grid(chart)
    if after_chart_hook:
        after_chart_hook()
    st.divider()
    _render_info(chart)
    st.divider()
    _render_star_table(chart)
    st.divider()
    _render_feixing_table(chart)
    st.divider()
    _render_palace_details(chart)
    if chart.vietnam_mode:
        st.divider()
        _render_vietnam_cultural_section(chart)


def _render_info(chart: ZiweiChart) -> None:
    """渲染基本排盤資訊卡片。"""
    leap_str = "（閏月）" if chart.is_leap_month else ""
    lunar_date = (
        f"{chart.lunar_year}年"
        f"（{HEAVENLY_STEMS[chart.lunar_year_stem]}{EARTHLY_BRANCHES[chart.lunar_year_branch]}年）"
        f" {LUNAR_MONTH_NAMES[chart.lunar_month - 1]}{leap_str}"
        f" 初{_day_to_chinese(chart.lunar_day)}"
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**公曆:** {chart.year}/{chart.month}/{chart.day}")
        st.write(f"**時間:** {chart.hour:02d}:{chart.minute:02d}")
        st.write(f"**時區:** UTC{chart.timezone:+.1f}")
        st.write(f"**性別:** {chart.gender}命 ({chart.yin_yang})")
    with col2:
        st.write(f"**農曆:** {lunar_date}")
        st.write(f"**時辰:** {HOUR_BRANCH_NAMES[chart.hour_branch]}")
        st.write(f"**地點:** {chart.location_name}")
    with col3:
        wu_ju_name = WU_XING_JU_NAMES[chart.wu_xing_ju]
        st.write(f"**命宮:** {EARTHLY_BRANCHES[chart.ming_gong_branch]}宮")
        st.write(f"**身宮:** {EARTHLY_BRANCHES[chart.shen_gong_branch]}宮")
        st.write(f"**五行局:** {wu_ju_name}")
        st.write(f"**命主:** {chart.ming_zhu}　**身主:** {chart.shen_zhu}")

    # 四化資訊
    sihua_str = "　".join(
        f"{star}化{hua}" for star, hua in chart.sihua.items()
    )
    st.info(f"**四化:** {sihua_str}")


def _day_to_chinese(day: int) -> str:
    """將農曆日數字轉為中文（如 1→一、11→十一）。"""
    units = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    if day <= 10:
        return units[day]
    if day < 20:
        return f"十{units[day - 10]}"
    if day == 20:
        return "二十"
    if day < 30:
        return f"二十{units[day - 20]}"
    return "三十"


def _palace_cell_html(
    palace: ZiweiPalace, is_ming: bool, is_shen: bool
) -> str:
    """產生單一宮位的 HTML 卡片（用於 CSS Grid 命盤方格）。"""
    bg = "#1a1a2e"
    border_style = "border:1px solid #444;"
    if is_ming and is_shen:
        border_style = "border:3px solid #FFD700;"
        bg = "#2d1b00"
    elif is_ming:
        border_style = "border:3px solid #FF6B6B;"
        bg = "#2d0000"
    elif is_shen:
        border_style = "border:3px solid #4ECDC4;"
        bg = "#001a1a"

    label = ""
    if is_ming:
        label += '<span style="color:#FF6B6B;font-weight:bold;font-size:11px">【命】</span>'
    if is_shen:
        label += '<span style="color:#4ECDC4;font-weight:bold;font-size:11px">【身】</span>'

    # 四化顏色
    SIHUA_COLORS = {"祿": "#00E676", "權": "#FF5252", "科": "#42A5F5", "忌": "#FF9800"}

    # 主星 HTML（含亮度和四化標記）
    stars_html = ""
    for star in palace.stars:
        attr = STAR_ATTRIBUTES.get(star, ("", "", "#aaa"))
        color = attr[2]
        bright = palace.brightness.get(star, "")
        bright_html = f'<span style="color:#aaa;font-size:9px">{bright}</span>' if bright else ""
        hua = palace.sihua.get(star, "")
        hua_html = ""
        if hua:
            hc = SIHUA_COLORS.get(hua, "#fff")
            hua_html = f'<span style="color:{hc};font-size:10px;font-weight:bold">化{hua}</span>'
        stars_html += (
            f'<div style="display:flex;align-items:center;gap:2px">'
            f'<span style="color:{color};font-size:13px;font-weight:bold">{star}</span>'
            f'{bright_html}{hua_html}</div>'
        )

    # 輔助星 HTML（含亮度和四化標記）
    aux_html = ""
    for star in palace.aux_stars:
        bright = palace.brightness.get(star, "")
        bright_str = f"({bright})" if bright else ""
        hua = palace.sihua.get(star, "")
        hua_str = ""
        if hua:
            hc = SIHUA_COLORS.get(hua, "#fff")
            hua_str = f'<span style="color:{hc};font-size:9px"> 化{hua}</span>'
        aux_html += (
            f'<span style="color:#888;font-size:10px">{star}{bright_str}</span>{hua_str} '
        )

    if not stars_html and not aux_html:
        stars_html = '<div style="color:#666;font-size:11px">─</div>'

    return (
        f'<div style="background:{bg};padding:6px 5px;border-radius:6px;'
        f'min-height:130px;{border_style}">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<span style="color:#c8a96e;font-size:10px">'
        f'{palace.stem_name}{palace.branch_name}</span>'
        f'{label}'
        f'<span style="color:#8B8000;font-size:9px">{palace.da_xian}</span>'
        f'</div>'
        f'<div style="color:#e0e0e0;font-size:11px;font-weight:bold;'
        f'border-bottom:1px solid #555;margin-bottom:3px;padding-bottom:1px">'
        f'{palace.name}</div>'
        f'{stars_html}'
        f'<div style="margin-top:3px;line-height:1.4">{aux_html}</div>'
        f'</div>'
    )


def _center_info_html(chart: ZiweiChart) -> str:
    """產生中宮資訊 HTML（顯示在命盤中央 2×2 格）。"""
    wu_ju = WU_XING_JU_NAMES[chart.wu_xing_ju]
    leap = "（閏）" if chart.is_leap_month else ""
    lm = LUNAR_MONTH_NAMES[chart.lunar_month - 1]
    ld = f"初{_day_to_chinese(chart.lunar_day)}"
    ys = HEAVENLY_STEMS[chart.lunar_year_stem]
    yb = EARTHLY_BRANCHES[chart.lunar_year_branch]

    # 越南模式：生肖名稱覆寫（卯→貓）
    zodiac_label = get_zodiac_year_label(chart.lunar_year_branch, chart.vietnam_mode)
    if chart.vietnam_mode:
        title_text = f"{VI_FLAG} 越南 Tử Vi 命盤"
        title_color = VI_STAR_COLOR
        _zh, yb_vi_full = VIETNAMESE_ZODIAC_NAMES[chart.lunar_year_branch]
        # yb_vi_full is like "Tý / Chuột"; take the first part
        yb_vi = yb_vi_full.split(" / ")[0]
        year_line = (
            f'{chart.lunar_year}年 {ys}{yb}年（{zodiac_label}年/{yb_vi}）'
        )
    else:
        title_text = "紫微斗數命盤"
        title_color = "#c8a96e"
        year_line = f'{chart.lunar_year}年 {ys}{yb}年'

    sihua_html = ""
    SIHUA_COLORS = {"祿": "#00E676", "權": "#FF5252", "科": "#42A5F5", "忌": "#FF9800"}
    for star, hua in chart.sihua.items():
        hc = SIHUA_COLORS.get(hua, "#fff")
        sihua_html += f'<span style="color:{hc};font-size:11px;margin:0 3px">{star}化{hua}</span>'

    return (
        f'<div style="background:#0d0d1a;border:2px solid {title_color};border-radius:10px;'
        f'padding:12px;text-align:center;height:100%;color:#e0d5b0;'
        f'display:flex;flex-direction:column;justify-content:center;">'
        f'<div style="font-size:20px;font-weight:bold;color:{title_color};margin-bottom:4px">'
        f'{title_text}</div>'
        f'<div style="font-size:12px;margin:2px 0">'
        f'{chart.gender}命 / {chart.yin_yang}{chart.gender} / {wu_ju}</div>'
        f'<div style="font-size:12px;margin:2px 0">'
        f'{year_line}</div>'
        f'<div style="font-size:12px;margin:2px 0">'
        f'{lm}{leap} {ld} {HOUR_BRANCH_NAMES[chart.hour_branch]}</div>'
        f'<div style="font-size:11px;margin:2px 0;color:#aaa">'
        f'命主: {chart.ming_zhu}  身主: {chart.shen_zhu}</div>'
        f'<div style="font-size:11px;margin:4px 0;color:#FF6B6B">'
        f'命宮: {EARTHLY_BRANCHES[chart.ming_gong_branch]}宮 '
        f'<span style="color:#4ECDC4">身宮: {EARTHLY_BRANCHES[chart.shen_gong_branch]}宮</span>'
        f'</div>'
        f'<div style="margin-top:4px">{sihua_html}</div>'
        f'<div style="font-size:10px;color:#888;margin-top:4px">'
        f'自化圖示: <span style="color:#00E676">→祿</span>'
        f'<span style="color:#FF5252">→權</span>'
        f'<span style="color:#42A5F5">→科</span>'
        f'<span style="color:#FF9800">→忌</span></div>'
        f'</div>'
    )


def _render_palace_grid(chart: ZiweiChart) -> None:
    """
    渲染南式紫微斗數命盤方格（使用 CSS Grid 單一 HTML 元素）。

    佈局（4×4 方格，中央 2×2 為命盤資訊）：
      巳(5)  午(6)  未(7)  申(8)
      辰(4)  [中宮 info]   酉(9)
      卯(3)  [中宮 info]   戌(10)
      寅(2)  丑(1)  子(0)  亥(11)
    """
    st.markdown("#### 🀄 十二宮命盤方格")

    branch_to_palace: dict[int, ZiweiPalace] = {p.branch: p for p in chart.palaces}

    def cell(branch: int) -> str:
        p = branch_to_palace[branch]
        return _palace_cell_html(
            p,
            is_ming=(p.branch == chart.ming_gong_branch),
            is_shen=(p.branch == chart.shen_gong_branch),
        )

    # 4×4 grid 佈局，中央 2×2 合併為命盤資訊
    # Grid positions (row, col): 1-indexed
    grid_layout = [
        # Row 1: 巳5, 午6, 未7, 申8
        (1, 1, 5), (1, 2, 6), (1, 3, 7), (1, 4, 8),
        # Row 2 left + right: 辰4, 酉9
        (2, 1, 4), (2, 4, 9),
        # Row 3 left + right: 卯3, 戌10
        (3, 1, 3), (3, 4, 10),
        # Row 4: 寅2, 丑1, 子0, 亥11
        (4, 1, 2), (4, 2, 1), (4, 3, 0), (4, 4, 11),
    ]

    cells_html = ""
    for row, col, branch in grid_layout:
        cells_html += (
            f'<div style="grid-row:{row};grid-column:{col}">'
            f'{cell(branch)}</div>'
        )

    # 中宮（rows 2-3, cols 2-3）
    center_html = (
        f'<div style="grid-row:2/4;grid-column:2/4">'
        f'{_center_info_html(chart)}</div>'
    )

    full_html = (
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);'
        f'grid-template-rows:repeat(4,auto);gap:4px;'
        f'background:#111;padding:6px;border-radius:10px;'
        f'border:2px solid #c8a96e;">'
        f'{cells_html}'
        f'{center_html}'
        f'</div>'
    )

    st.markdown(full_html, unsafe_allow_html=True)


def _render_star_table(chart: ZiweiChart) -> None:
    """渲染主星位置匯總表格。"""
    if chart.vietnam_mode:
        st.markdown("#### ⭐ 主星分佈表（越南 Tử Vi）")
    else:
        st.markdown("#### ⭐ 主星分佈表")

    all_stars = list(ZIWEI_GROUP.keys()) + list(TIANFU_GROUP.keys())
    branch_to_palace: dict[int, ZiweiPalace] = {p.branch: p for p in chart.palaces}

    if chart.vietnam_mode:
        header = "| 星曜 | 越南名 (Tên Việt) | 五行 | 所在宮位 | 亮度 | 四化 |"
        sep = "|:---:|:---:|:---:|:---:|:---:|:---:|"
    else:
        header = "| 星曜 | 五行 | 別稱 | 所在宮位 | 地支 | 亮度 | 四化 |"
        sep = "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|"
    rows = [header, sep]

    for star in all_stars:
        attr = STAR_ATTRIBUTES[star]
        wuxing, alias, color = attr
        palace = next(
            (p for p in chart.palaces if star in p.stars), None
        )
        if palace is None:
            continue
        is_ming = "【命】" if palace.branch == chart.ming_gong_branch else ""
        is_shen = "【身】" if palace.branch == chart.shen_gong_branch else ""
        marker = f"{is_ming}{is_shen}"
        name_html = f'<span style="color:{color};font-weight:bold">{star}</span>'
        bright = palace.brightness.get(star, "")
        hua = chart.sihua.get(star, "")
        hua_str = f"化{hua}" if hua else ""
        if chart.vietnam_mode:
            vi_info = get_star_vietnamese_info(star)
            vi_name = vi_info["vi_name"] if vi_info else star
            rows.append(
                f"| {name_html} | {vi_name} | {wuxing} "
                f"| {palace.name}{marker} "
                f"| {bright} "
                f"| {hua_str} |"
            )
        else:
            rows.append(
                f"| {name_html} | {wuxing} | {alias} "
                f"| {palace.name}{marker} "
                f"| {palace.branch_name} "
                f"| {bright} "
                f"| {hua_str} |"
            )

    st.markdown("\n".join(rows), unsafe_allow_html=True)


def _render_sihua_legend() -> None:
    """渲染四化圖例說明。"""
    st.markdown(
        '<div style="text-align:center;padding:4px;font-size:12px">'
        '四化圖示: '
        '<span style="color:#00E676;font-weight:bold">●祿</span> '
        '<span style="color:#FF5252;font-weight:bold">●權</span> '
        '<span style="color:#42A5F5;font-weight:bold">●科</span> '
        '<span style="color:#FF9800;font-weight:bold">●忌</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_feixing_table(chart: ZiweiChart) -> None:
    """渲染飛星四化表（各宮位天干的四化）。"""
    st.markdown("#### 🌠 飛星四化表")
    st.markdown("*各宮位天干所引發的四化（宮干飛星）*")

    header = "| 宮位 | 天干 | 化祿 | 化權 | 化科 | 化忌 |"
    sep = "|:---:|:---:|:---:|:---:|:---:|:---:|"
    rows = [header, sep]

    SIHUA_COLORS = {"祿": "#00E676", "權": "#FF5252", "科": "#42A5F5", "忌": "#FF9800"}

    for palace in chart.palaces:
        feixing = _compute_feixing(palace.stem)
        lu_star = SIHUA_TABLE[palace.stem][0]
        quan_star = SIHUA_TABLE[palace.stem][1]
        ke_star = SIHUA_TABLE[palace.stem][2]
        ji_star = SIHUA_TABLE[palace.stem][3]
        rows.append(
            f"| {palace.name}({palace.branch_name}) | {palace.stem_name} "
            f'| <span style="color:{SIHUA_COLORS["祿"]}">{lu_star}</span> '
            f'| <span style="color:{SIHUA_COLORS["權"]}">{quan_star}</span> '
            f'| <span style="color:{SIHUA_COLORS["科"]}">{ke_star}</span> '
            f'| <span style="color:{SIHUA_COLORS["忌"]}">{ji_star}</span> |'
        )

    st.markdown("\n".join(rows), unsafe_allow_html=True)


def _render_palace_details(chart: ZiweiChart) -> None:
    """渲染十二宮位詳細說明。"""
    if chart.vietnam_mode:
        st.markdown("#### 📋 十二宮位詳情（越南 Tử Vi）")
    else:
        st.markdown("#### 📋 十二宮位詳情")

    _PALACE_DESC = {
        "命宮":  "代表人的個性、才能、命運走向",
        "兄弟宮": "兄弟姐妹、朋友關係",
        "夫妻宮": "婚姻、伴侶、感情",
        "子女宮": "子女、創造、學生",
        "財帛宮": "金錢、財富、財運",
        "疾厄宮": "健康、疾病、意外",
        "遷移宮": "旅行、遷徙、外出緣份",
        "交友宮": "朋友、同事、下屬",
        "官祿宮": "事業、工作、官運",
        "田宅宮": "房產、家庭、祖業",
        "福德宮": "福份、精神、享樂",
        "父母宮": "父母、長輩、文書",
    }

    # 三合組顯示
    st.markdown("##### 🔺 三合")
    sanhe_names = {
        (0, 4, 8): "水局 (子辰申)",
        (1, 5, 9): "金局 (丑巳酉)",
        (2, 6, 10): "火局 (寅午戌)",
        (3, 7, 11): "木局 (卯未亥)",
    }
    branch_to_palace = {p.branch: p for p in chart.palaces}
    for group in chart.sanhe_groups:
        group_name = sanhe_names.get(group, "")
        palace_names = [
            branch_to_palace[b].name if b in branch_to_palace else EARTHLY_BRANCHES[b]
            for b in group
        ]
        st.write(f"**{group_name}:** {' ↔ '.join(palace_names)}")

    st.markdown("---")

    cols = st.columns(3)
    for i, palace in enumerate(chart.palaces):
        with cols[i % 3]:
            stars_str = "、".join(palace.stars) if palace.stars else "（空宮）"
            aux_str = "、".join(palace.aux_stars) if palace.aux_stars else ""
            markers = []
            if palace.branch == chart.ming_gong_branch:
                markers.append("🔴命")
            if palace.branch == chart.shen_gong_branch:
                markers.append("🔵身")
            marker_str = " ".join(markers)

            # 四化
            sihua_str = ""
            for star, hua in palace.sihua.items():
                sihua_str += f" {star}化{hua}"

            if chart.vietnam_mode:
                vi_info = get_palace_vietnamese_info(palace.name)
                vi_name = vi_info["vi_name"] if vi_info else ""
                desc = vi_info["zh_interp"] if vi_info else _PALACE_DESC.get(palace.name, "")
                vi_desc = vi_info["vi_interp"] if vi_info else ""
                st.markdown(
                    f"**{palace.stem_name}{palace.branch_name} {palace.name}**"
                    + (f" *{vi_name}*" if vi_name else "")
                    + f" {marker_str} 大限:{palace.da_xian}\n\n"
                    f"⭐ 主星: {stars_str}\n\n"
                    f"🔹 輔星: {aux_str}\n\n"
                    + (f"🔸 四化: {sihua_str}\n\n" if sihua_str else "")
                    + f"*{desc}*\n\n"
                    + (f'<span style="color:#aaa;font-size:11px">🇻🇳 {vi_desc}</span>' if vi_desc else ""),
                    unsafe_allow_html=True,
                )
            else:
                desc = _PALACE_DESC.get(palace.name, "")
                st.markdown(
                    f"**{palace.stem_name}{palace.branch_name} {palace.name}** "
                    f"{marker_str} 大限:{palace.da_xian}\n\n"
                    f"⭐ 主星: {stars_str}\n\n"
                    f"🔹 輔星: {aux_str}\n\n"
                    + (f"🔸 四化: {sihua_str}\n\n" if sihua_str else "")
                    + f"*{desc}*"
                )


def _render_vietnam_cultural_section(chart: ZiweiChart) -> None:
    """渲染越南 Tử Vi 文化特色說明區塊（僅在越南模式時顯示）。"""
    st.markdown(f"#### {VI_FLAG} 越南 Tử Vi 特色說明")

    # 文化說明
    st.info(VIETNAMESE_CULTURAL_NOTE)

    # 生肖資訊：特別標示「貓年」
    zodiac_zh, zodiac_vi = get_vietnamese_zodiac_name(chart.lunar_year_branch)
    st.markdown(
        f"**🐾 生肖年份（越南）**：{zodiac_zh}年（{zodiac_vi}）"
        + ("　← 越南曆法以**貓**代替中國的「兔」🐱" if chart.lunar_year_branch == 3 else "")
    )

    # 越南命宮大限詮釋
    ming_gong_palace = next(
        (p for p in chart.palaces if p.branch == chart.ming_gong_branch), None
    )
    if ming_gong_palace:
        da_xian_key = f"{ming_gong_palace.name}大限"
        da_xian_tip = VIETNAMESE_DA_XIAN_TIPS.get(da_xian_key)
        if da_xian_tip:
            st.markdown(f"**🔮 大限提示**：{da_xian_tip}")

    # 越南婚姻合婚提示（基於年支）
    st.markdown("---")
    st.markdown(f"##### 💕 越南傳統合婚參考（{zodiac_zh}年生人）")

    compat_rows = []
    branch1 = chart.lunar_year_branch
    for branch2 in range(12):
        if branch2 == branch1:
            continue
        key = (min(branch1, branch2), max(branch1, branch2))
        info = VIETNAMESE_MARRIAGE_COMPAT.get(key)
        if info:
            zh2, vi2 = VIETNAMESE_ZODIAC_NAMES[branch2]
            level_color = {
                "大吉": VI_ACCENT_COLOR,
                "吉": "#4CAF50",
                "不利": "#888",
            }.get(info["level"], "#aaa")
            compat_rows.append(
                f'<span style="color:{level_color};font-weight:bold">{info["level"]}</span> '
                f'{zh2}（{vi2}） — {info["note"]}'
            )

    if compat_rows:
        st.markdown(
            "<br>".join(f"• {r}" for r in compat_rows),
            unsafe_allow_html=True,
        )
    else:
        st.write("（無特殊合婚記錄，請查看夫妻宮星曜）")
