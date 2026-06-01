"""
知识蒸馏 v2.0 - 报告生成器
纯数据驱动，不预设任何行业模板，从分析结果自动拼合知识库
"""
import os
from datetime import datetime


def generate_knowledge_base(
    summary: dict,
    corpus_text: str,
    output_path: str,
    config: dict = None,
) -> str:
    """
    从分析摘要生成 Markdown 知识库

    报告结构（全自动，无硬编码）：
    1. 概览：文件总量、时间跨度、工作性质推断
    2. 工作节奏：月度活动热力图
    3. 技能画像：工具链 + 角色推断
    4. 目录与组织逻辑
    5. 文件命名规范
    6. 模板与可复用资产
    7. 写作风格分析
    8. 行业线索
    9. 全文内容索引
    """

    cfg = config or {}
    report_cfg = cfg.get("report", {})

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []

    # ===== 头部 =====
    # 从目录名推断人物标识
    root_path = summary.get("file_snapshot", {}).get("root", "未知")
    person_name = os.path.basename(root_path) or root_path

    lines.append(f"# {person_name} 个人知识库")
    lines.append(f"> 由知识蒸馏工具 v2.0 自动生成  |  生成时间: {now}")
    lines.append("")

    # ===== 一、总体概览 =====
    fs = summary.get("file_snapshot", {})
    lines.append("## 一、总体概览")
    lines.append("")
    lines.append(f"- **扫描根目录**: `{root_path}`")
    lines.append(f"- **文件总量**: {fs.get('total', 0):,} 个")
    lines.append(f"- **总大小**: {fs.get('size_gb', 0)} GB")

    timeline = summary.get("timeline", {})
    if timeline and timeline.get("start"):
        lines.append(f"- **时间跨度**: {timeline['start']} → {timeline['end']}（{timeline.get('duration_days', 0)} 天）")

    wp = summary.get("work_portrait", {})
    if wp.get("inferred_roles"):
        lines.append(f"- **角色推断**: {'、'.join(wp['inferred_roles'])}")
    if wp.get("industry_clues"):
        clues = wp["industry_clues"]
        clue_parts = []
        for c in clues[:5]:
            clue_parts.append(c["industry"] + "(关键词:" + c["keyword"] + ")")
        lines.append("- **行业线索**: " + "、".join(clue_parts))

    lines.append("")

    # ===== 二、工作节奏 =====
    if timeline.get("monthly"):
        lines.append("## 二、工作节奏（月度活动）")
        lines.append("")
        lines.append("| 月份 | 文件数 | 主要类型 | 典型文件 |")
        lines.append("|------|--------|----------|----------|")
        for m in timeline["monthly"]:
            types_str = ", ".join(f"{k}:{v}" for k, v in sorted(m.get("types", {}).items(), key=lambda x: x[1], reverse=True)[:3])
            samples = m.get("samples", [])
            sample_str = samples[0] if samples else "-"
            if len(samples) > 1:
                sample_str += f" 等{len(samples)}个"
            lines.append(f"| {m['month']} | {m['count']} | {types_str} | {sample_str} |")
        lines.append("")

    # 活动趋势说明
    monthly_counts = [m["count"] for m in timeline.get("monthly", [])]
    if monthly_counts:
        avg_monthly = sum(monthly_counts) / len(monthly_counts)
        lines.append(f"月均产出约 {avg_monthly:.0f} 个文件，工作节奏: ", end="")
        if max(monthly_counts) > avg_monthly * 2:
            lines.append("有明显的高峰期和低谷期，存在项目密集交付周期。")
        elif max(monthly_counts) - min(monthly_counts) < avg_monthly * 0.5:
            lines.append("稳定持续，各月产出量波动不大。")
        else:
            lines.append("月度间有一定波动。")
        lines.append("")

    # ===== 三、技能画像 =====
    tc = summary.get("toolchain", {})
    if tc.get("detected_tools"):
        lines.append("## 三、技能画像与工具链")
        lines.append("")
        lines.append("| 工具 | 关联文件数 | 置信度 | 关键格式 |")
        lines.append("|------|-----------|--------|----------|")
        for t in tc["detected_tools"]:
            conf_map = {"high": "高", "medium": "中", "low": "低"}
            lines.append(f"| {t['tool']} | {t['file_count']} | {conf_map.get(t.get('confidence','low'),'低')} | {', '.join(t.get('extensions',[]))} |")
        lines.append("")

    # ===== 四、目录与组织逻辑 =====
    dir_st = summary.get("directory_structure", {})
    if dir_st:
        lines.append("## 四、目录与组织逻辑")
        lines.append(f"\n{dir_st.get('interpretation', '—')}，最大层级深度 {dir_st.get('max_depth', 0)}。")
        lines.append("")

        sig_dirs = dir_st.get("significant_dirs", [])
        if sig_dirs:
            lines.append("**高频目录**:")
            for sd in sig_dirs:
                examples = sd.get("examples", [])
                ex_str = "、".join(e["dir"] for e in examples[:3])
                lines.append(f"- 「{sd['keyword']}」相关: {ex_str}")
            lines.append("")

    # ===== 五、文件命名规范 =====
    naming = summary.get("naming", {})
    if naming.get("patterns"):
        lines.append("## 五、文件命名规范")
        lines.append("")
        for k, v in naming["patterns"].items():
            lines.append(f"- **{k}**: {v}")

        samples = naming.get("date_prefixed_samples", [])
        if samples:
            lines.append(f"\n日期前缀示例: {', '.join(samples[:5])}")
        lines.append("")

    # ===== 六、模板与可复用资产 =====
    tmpl = summary.get("templates", {})
    spreadsheet_templates = tmpl.get("spreadsheet_templates", [])
    presentations = tmpl.get("presentations", [])

    if spreadsheet_templates or presentations:
        lines.append("## 六、模板与可复用资产")
        lines.append("")

        if spreadsheet_templates:
            lines.append("### 结构化表格")
            lines.append("")
            lines.append("| 文件 | 工作表 | 行数 | 列数 | 表头 |")
            lines.append("|------|--------|------|------|------|")
            for st in spreadsheet_templates:
                hd = ", ".join(st.get("headers", [])[:5])
                lines.append(f"| {st['file']} | {st['sheet']} | {st['rows']} | {st['columns']} | {hd} |")
            lines.append("")

        if presentations:
            lines.append("### 演示文稿")
            lines.append("")
            for pr in presentations:
                note_info = f"（含 {pr['notes_count']} 条备注）" if pr.get("has_notes") else ""
                lines.append(f"- {pr['file']}: {pr['slides']} 页 {note_info}")
            lines.append("")

    # ===== 七、写作风格 =====
    style = summary.get("writing_style", {})
    if style.get("status") == "analyzed":
        lines.append("## 七、写作风格分析")
        lines.append("")
        lines.append(f"- 总分析字符: {style['total_chars']:,}")
        lines.append(f"- 段落数: {style['paragraphs']}")
        lines.append(f"- 句子数: {style['sentences']}")
        lines.append(f"- 平均句长: {style['avg_sentence_length']} 字")
        lines.append(f"- 平均段长: {style['avg_paragraph_length']} 字")

        tone = style.get("tone", {})
        lines.append(f"- 感叹号密度: {tone.get('exclamation_density', 0)}/千字")
        lines.append(f"- 问号密度: {tone.get('question_density', 0)}/千字")

        interp = style.get("style_interpretation", "")
        if interp:
            lines.append(f"\n**风格推断**: {interp}")

        keywords = style.get("top_keywords", [])
        if keywords:
            kw_parts = []
            for k in keywords[:10]:
                kw_parts.append(k["word"] + "(" + str(k["count"]) + ")")
            lines.append("\n**高频词**: " + "、".join(kw_parts))
        lines.append("")

    # ===== 八、行业线索 =====
    if wp.get("industry_clues"):
        lines.append("## 八、行业线索（自动推断）")
        lines.append("")
        for c in wp["industry_clues"]:
            lines.append(f"- 关键词「**{c['keyword']}**」出现 {c['frequency']} 次 → 关联行业: {c['industry']}")
        lines.append("")

    # ===== 九、全文内容索引 =====
    if corpus_text:
        lines.append("## 九、全文内容索引")
        lines.append("")
        # 提取各文件段落的标题
        headings = []
        for line in corpus_text.split("\n"):
            line = line.strip()
            if line.startswith("### "):
                headings.append(line[4:])
        if headings:
            for h in headings[:50]:
                lines.append(f"- {h}")
        lines.append("")

    # ===== 写作 =====
    content = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path


if __name__ == "__main__":
    print("ReportGenerator v2.0 loaded.")
（内容由AI生成，仅供参考）
