"""
知识蒸馏 v2.0 - 通用分析引擎
完全数据驱动：从文件结构、内容、时间线自动推断工作模式，不预设行业或角色
"""
import re
import json
import math
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict


class KnowledgeAnalyzer:
    """通用知识分析器"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.ac = self.config.get("analysis", {})
        self.tc = self.config.get("toolchain", {}).get("rules", {})

    # ========== 1. 时间线分析 ==========
    def analyze_timeline(self, files: list) -> dict:
        """从文件修改时间反推工作节奏"""
        monthly = defaultdict(lambda: {"count": 0, "types": defaultdict(int), "samples": []})
        all_dates = []

        for f in files:
            mtime_str = f.get("modified") or f.get("mtime") or f.get("modified_time", "")
            if not mtime_str:
                continue
            try:
                dt = datetime.fromisoformat(mtime_str.replace("Z", "+00:00").replace("+00:00", ""))
                if dt.tzinfo:
                    dt = dt.replace(tzinfo=None)
            except Exception:
                try:
                    dt = datetime.strptime(mtime_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue

            all_dates.append(dt)
            month_key = dt.strftime("%Y-%m")
            monthly[month_key]["count"] += 1

            ext = Path(f.get("name", "")).suffix.lower()
            cat = self._classify_extension(ext)
            monthly[month_key]["types"][cat] += 1

            if len(monthly[month_key]["samples"]) < 5:
                monthly[month_key]["samples"].append(f.get("name", ""))

        if not all_dates:
            return {"error": "无可用时间数据"}

        all_dates.sort()
        months_sorted = sorted(monthly.keys())

        return {
            "start": all_dates[0].strftime("%Y-%m-%d"),
            "end": all_dates[-1].strftime("%Y-%m-%d"),
            "duration_days": (all_dates[-1] - all_dates[0]).days,
            "monthly": [
                {
                    "month": m,
                    "count": monthly[m]["count"],
                    "types": dict(monthly[m]["types"]),
                    "samples": monthly[m]["samples"][:5],
                }
                for m in months_sorted
            ],
            "active_months": len(months_sorted),
        }

    # ========== 2. 目录结构语义推断 ==========
    def analyze_directory_structure(self, files: list) -> dict:
        """从目录层级和命名推断组织逻辑"""
        dirs = defaultdict(int)
        depth_counter = Counter()
        keyword_dirs = defaultdict(list)

        for f in files:
            path = f.get("path") or f.get("file_path", "")
            if not path:
                continue
            p = Path(path)
            dir_name = p.parent.name if p.parent != p else ""
            if dir_name:
                dirs[dir_name] += 1

            # 计算深度
            parts = p.parts
            depth = max(0, len(parts) - 2)
            depth_counter[depth] += 1

            # 匹配有意义的目录名关键词
            for kw in ["项目", "project", "设计", "design", "素材", "material", "asset",
                        "模板", "template", "周报", "weekly", "月报", "monthly",
                        "品牌", "brand", "产品", "product", "培训", "training",
                        "推文", "post", "视频", "video", "图片", "image", "img",
                        "文案", "copy", "数据", "data", "分析", "analysis",
                        "合同", "contract", "方案", "proposal", "汇报", "report"]:
                if kw.lower() in dir_name.lower():
                    keyword_dirs[kw].append({"dir": dir_name, "count": dirs[dir_name]})
                    break

        max_depth = max(depth_counter.keys()) if depth_counter else 0

        interpretation = "扁平结构，文件集中存放"
        if max_depth >= 5:
            interpretation = "深层嵌套，有详细的项目分类体系"
        elif max_depth >= 3:
            interpretation = "中等层级，按模块/项目组织"
        elif max_depth >= 2:
            interpretation = "简单分类，按大类组织"

        return {
            "max_depth": max_depth,
            "depth_distribution": dict(depth_counter.most_common()),
            "top_dirs": dict(dirs.most_common(15)),
            "significant_dirs": [
                {"keyword": k, "examples": v[:5]}
                for k, v in keyword_dirs.items()
                if len(v) >= 3
            ],
            "interpretation": interpretation,
        }

    # ========== 3. 文件类型画像 ==========
    def analyze_file_portrait(self, files: list) -> dict:
        """从文件类型分布推断工作性质"""
        type_counter = Counter()
        total_size = 0
        big_files = []

        for f in files:
            ext = Path(f.get("name", "")).suffix.lower()
            cat = self._classify_extension(ext)
            type_counter[cat] += 1

            size_mb = float(f.get("size_mb") or f.get("size", 0) or 0)
            total_size += size_mb
            if size_mb > 5:
                big_files.append({
                    "name": f.get("name", ""),
                    "type": cat,
                    "size_mb": round(size_mb, 1),
                    "modified": f.get("modified", ""),
                })

        total = sum(type_counter.values())
        portrait = {}

        # 推断工作性质
        image_ratio = type_counter.get("image", 0) / max(total, 1)
        doc_ratio = type_counter.get("document", 0) / max(total, 1)
        design_ratio = type_counter.get("design", 0) / max(total, 1)
        video_ratio = type_counter.get("video", 0) / max(total, 1)
        code_ratio = type_counter.get("code", 0) / max(total, 1)

        roles = []
        if doc_ratio > 0.02:
            roles.append("文档产出型（报告/方案/表格密集）")
        if image_ratio > 0.5:
            roles.append("视觉密集型（大量图片素材/效果图）")
        if design_ratio > 0.03:
            roles.append("设计创作型（PS/AI 源文件）")
        if video_ratio > 0.03:
            roles.append("视频内容型（视频素材/剪辑产出）")
        if code_ratio > 0.05:
            roles.append("技术/开发型（代码文件占比高）")

        # 行业关键词
        industry_clues = self._detect_industry_from_names(files)

        portrait = {
            "total_files": total,
            "total_size_gb": round(total_size / 1024, 2),
            "type_distribution": dict(type_counter.most_common()),
            "type_ratios": {k: round(v / max(total, 1) * 100, 1) for k, v in type_counter.items()},
            "inferred_roles": roles if roles else ["通用型（无明显倾向）"],
            "industry_clues": industry_clues[:10],
            "big_files": sorted(big_files, key=lambda x: x["size_mb"], reverse=True)[:20],
        }

        return portrait

    def _detect_industry_from_names(self, files: list) -> list:
        """从文件名高频词推测行业"""
        name_words = []
        for f in files:
            name = f.get("name", "")
            # 拆分中文词组
            words = re.findall(r"[\u4e00-\u9fff]{2,}", name)
            name_words.extend(words)

        word_freq = Counter(name_words).most_common(50)

        # 行业词典
        industry_map = {
            "入户门": "建材/门窗行业",
            "门窗": "建材/门窗行业",
            "智能锁": "智能家居/安防",
            "家居": "家居/装修",
            "装修": "家居/装修",
            "产品图册": "产品/制造",
            "款式": "产品设计/制造",
            "品牌": "品牌/营销",
            "营销": "市场营销",
            "抖音": "新媒体/短视频运营",
            "短视频": "新媒体/短视频",
            "公众号": "新媒体/内容运营",
            "运营": "运营管理",
            "研发": "研发/技术",
            "生产": "生产制造",
            "销售": "销售/商务",
            "培训": "培训/HR",
            "财务": "财务/会计",
            "设计": "设计/创意",
            "开发": "软件开发",
            "测试": "软件测试",
            "部署": "运维/DevOps",
            "架构": "软件架构",
        }

        clues = []
        for word, freq in word_freq:
            if word in industry_map and freq >= 2:
                clues.append({"keyword": word, "frequency": freq, "industry": industry_map[word]})

        return clues

    # ========== 4. 工具链推断 ==========
    def analyze_toolchain(self, files: list) -> dict:
        """基于文件类型推断工具链"""
        ext_counter = Counter()
        for f in files:
            ext = Path(f.get("name", "")).suffix.lower()
            if ext:
                ext_counter[ext] += 1

        detected = []
        ext_used = set()

        for tool_name, rule in self.tc.items():
            exts = rule.get("extensions", [])
            weight = rule.get("weight", "low")
            hits = sum(ext_counter.get(e, 0) for e in exts)
            if hits > 0:
                detected.append({
                    "tool": tool_name,
                    "file_count": hits,
                    "extensions": [e for e in exts if ext_counter.get(e, 0) > 0],
                    "confidence": weight,
                })
                ext_used.update(e for e in exts if ext_counter.get(e, 0) > 0)

        # 未匹配的扩展名
        unmatched = {ext: cnt for ext, cnt in ext_counter.items() if ext not in ext_used and cnt >= 3}
        if unmatched:
            detected.append({
                "tool": "未知工具",
                "file_count": sum(unmatched.values()),
                "extensions": list(unmatched.keys()),
                "confidence": "low",
                "note": "未在配置中匹配到对应工具",
            })

        return {
            "detected_tools": sorted(detected, key=lambda x: x["file_count"], reverse=True),
            "total_tools": len(detected),
        }

    # ========== 5. 命名规范检测 ==========
    def analyze_naming(self, files: list) -> dict:
        """分析文件命名模式"""
        names = [f.get("name", "") for f in files if f.get("name")]
        patterns = {
            "date_prefix": 0,     # 2026.04-xxx
            "number_prefix": 0,   # 01-xxx, R-24012
            "version_suffix": 0,  # xxx_v2, xxx-副本
            "status_marker": 0,   # xxx_终稿, xxx_定稿
        }

        date_pattern = re.compile(r"^\d{4}[.\-/]\d{1,2}")
        version_pattern = re.compile(r"[-_](v\d+|ver\d+|副本|修订|修改|终稿|定稿|final)")
        number_prefix = re.compile(r"^[A-Z]-\d+")

        samples = []
        for name in names[:200]:
            if date_pattern.match(name):
                patterns["date_prefix"] += 1
                if len(samples) < 20:
                    samples.append(name)
            if version_pattern.search(name):
                patterns["version_suffix"] += 1
            if number_prefix.match(name):
                patterns["number_prefix"] += 1

        total = len(names)
        return {
            "total": total,
            "patterns": {
                "日期前缀": f"{patterns['date_prefix']}/{total}",
                "编号前缀": f"{patterns['number_prefix']}/{total}",
                "版本标记": f"{patterns['version_suffix']}/{total}",
            },
            "date_prefixed_samples": samples[:15],
        }

    # ========== 6. 写作风格分析 ==========
    def analyze_writing_style(self, corpus_text: str) -> dict:
        """通用文本风格分析"""
        if not corpus_text or len(corpus_text) < self.ac.get("min_chars_for_writing_style", 200):
            return {"status": "insufficient", "total_chars": len(corpus_text)}

        # 基础统计
        sentences = re.split(r"[。！？；\n.!?;]+", corpus_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", corpus_text) if p.strip()]

        # 标题识别
        title_lines = []
        for line in corpus_text.split("\n"):
            line = line.strip()
            if len(line) < 60 and len(line) > 2 and (
                re.match(r"^[#一二三四五六七八九十\d]+[、.．)]", line)
                or re.match(r"^[#]+ ", line)
                or "脚本" in line
                or "方案" in line
            ):
                title_lines.append(line)

        # 语气
        exclamation = corpus_text.count("！") + corpus_text.count("!")
        question = corpus_text.count("？") + corpus_text.count("?")
        brackets = corpus_text.count("（") + corpus_text.count("(")

        # 高频词
        words = re.findall(r"[\u4e00-\u9fff]{2,}", corpus_text)
        word_freq = Counter(words).most_common(30)

        # 句子长度分布
        sent_lens = [len(s) for s in sentences]
        avg_sent_len = sum(sent_lens) / max(len(sent_lens), 1)

        return {
            "status": "analyzed",
            "total_chars": len(corpus_text),
            "paragraphs": len(paragraphs),
            "sentences": len(sentences),
            "avg_sentence_length": round(avg_sent_len, 1),
            "avg_paragraph_length": round(len(corpus_text) / max(len(paragraphs), 1), 1),
            "tone": {
                "exclamation_density": round(exclamation / max(len(corpus_text), 1) * 1000, 2),
                "question_density": round(question / max(len(corpus_text), 1) * 1000, 2),
                "bracket_density": round(brackets / max(len(corpus_text), 1) * 1000, 2),
            },
            "title_patterns": title_lines[:20],
            "top_keywords": [{"word": w, "count": c} for w, c in word_freq],
            "style_interpretation": self._interpret_style(avg_sent_len, exclamation, question, word_freq),
        }

    def _interpret_style(self, avg_sent_len: float, exclamation: int, question: int, word_freq: list) -> str:
        parts = []
        if avg_sent_len < 20:
            parts.append("短句为主，节奏快")
        elif avg_sent_len < 50:
            parts.append("中长句，叙述平稳")
        else:
            parts.append("长句为主，偏正式/报告风格")

        if exclamation > 10:
            parts.append("感叹号密集，情感表达强")
        if question > 10:
            parts.append("问句较多，互动性强")

        top_words = [w for w, _ in word_freq[:5]]
        parts.append(f"高频词: {'、'.join(top_words)}")

        return "；".join(parts)

    # ========== 7. 模板检测 ==========
    def analyze_templates(self, extraction_results: list) -> dict:
        """检测可复用的模板"""
        spreadsheets = []
        presentations = []

        for r in extraction_results:
            fname = Path(r.get("file", "")).name
            if r.get("type") == "xlsx" and r.get("sheets"):
                for s in r["sheets"]:
                    if s.get("rows", 0) > 20:
                        spreadsheets.append({
                            "file": fname,
                            "sheet": s["name"],
                            "rows": s["rows"],
                            "columns": s["columns"],
                            "headers": s.get("headers", [])[:10],
                        })
            if r.get("type") == "pptx":
                presentations.append({
                    "file": fname,
                    "slides": r.get("slides", 0),
                    "has_notes": r.get("has_notes", False),
                    "notes_count": r.get("notes_count", 0),
                })

        return {
            "spreadsheet_templates": spreadsheets[:10],
            "presentations": presentations[:10],
        }

    # ========== 辅助方法 ==========
    def _classify_extension(self, ext: str) -> str:
        ext = ext.lower()
        if ext in {".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".pdf", ".txt", ".md", ".csv"}:
            return "document"
        if ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".tiff"}:
            return "image"
        if ext in {".psd", ".ai", ".sketch", ".fig", ".xd", ".cdr", ".eps"}:
            return "design"
        if ext in {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"}:
            return "video"
        if ext in {".zip", ".rar", ".7z", ".tar", ".gz"}:
            return "archive"
        if ext in {".py", ".js", ".ts", ".html", ".css", ".java", ".go", ".rs", ".vue", ".react"}:
            return "code"
        return "other"


def generate_summary_json(analyzer: KnowledgeAnalyzer, files: list, style: dict,
                           timeline: dict, portrait: dict, dir_structure: dict,
                           naming: dict, toolchain: dict, templates: dict,
                           output_path: str):
    """生成结构化 JSON 摘要"""
    summary = {
        "file_snapshot": {
            "total": portrait["total_files"],
            "size_gb": portrait["total_size_gb"],
            "types": portrait["type_distribution"],
        },
        "timeline": timeline,
        "work_portrait": {
            "inferred_roles": portrait["inferred_roles"],
            "industry_clues": portrait["industry_clues"],
            "directory_logic": dir_structure["interpretation"],
            "max_depth": dir_structure["max_depth"],
        },
        "toolchain": toolchain,
        "naming": naming,
        "writing_style": style,
        "templates": templates,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary


if __name__ == "__main__":
    print("KnowledgeAnalyzer v2.0 loaded.")
（内容由AI生成，仅供参考）
