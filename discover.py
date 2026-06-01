"""
知识蒸馏 v2.0 - 通用文件夹自动发现
纯结构特征评分，零硬编码假设，任何行业开箱即用
"""
import os
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict


def discover_folders(config: dict) -> list:
    """
    自动发现可能包含工作产出的文件夹候选列表

    评分维度（满分 100）：
    - 文件多样性 (25): 是否包含文档/图片/设计等多种类型
    - 文件总量 (20): 是否达到一定文件数
    - 近期活跃 (20): 最近 30 天是否有修改
    - 目录深度 (15): 是否有合理的组织层级
    - 文档占比 (10): 可提取知识的文件占比
    - 图文混合 (10): 图片+文档混合（运营/设计特征）
    """
    cfg = config.get("discovery", {})
    weights = cfg.get("weights", {
        "file_variety": 25,
        "total_files": 20,
        "recent_activity": 20,
        "directory_depth": 15,
        "document_ratio": 10,
        "image_document_mix": 10,
    })

    search_roots = cfg.get("search_roots", ["~\\Desktop", "~\\Documents", "D:\\", "E:\\"])
    exclude_patterns = set(cfg.get("exclude_patterns", [
        "$Recycle.Bin", "System Volume Information", "Windows",
        "Program Files", "Program Files (x86)", "ProgramData",
        "AppData", "node_modules", ".git", "__pycache__", "Temp", "cache",
    ]))
    hints = cfg.get("search_hints", [])

    # 扩展根目录
    user_home = str(Path.home())
    expanded_roots = [p.replace("~", user_home) for p in search_roots]

    # 文档/设计扩展名
    valuable_exts = {
        ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".pdf",
        ".txt", ".md", ".csv", ".psd", ".ai", ".sketch", ".fig", ".xd",
        ".py", ".js", ".ts", ".html", ".css", ".java", ".go", ".rs",
        ".mp4", ".avi", ".mov", ".mkv",
    }

    image_exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".tiff"}

    candidates = []

    for root_path in expanded_roots:
        root = Path(root_path)
        if not root.exists():
            continue

        # 第一层子目录
        try:
            subdirs = [d for d in root.iterdir() if d.is_dir()]
        except PermissionError:
            continue

        for subdir in subdirs:
            dir_name = subdir.name
            if dir_name in exclude_patterns or dir_name.startswith("."):
                continue
            if subdir.is_symlink():
                continue

            score = _score_folder(subdir, weights, valuable_exts, image_exts, exclude_patterns, hints)
            if score["total"] >= 25:  # 最低阈值
                candidates.append(score)

    # 按总分降序
    candidates.sort(key=lambda x: x["total"], reverse=True)
    return candidates[:20]


def _score_folder(folder: Path, weights: dict, valuable_exts: set,
                  image_exts: set, exclude_patterns: set, hints: list) -> dict:
    """对单个文件夹评分"""
    try:
        all_files = list(folder.rglob("*"))
    except PermissionError:
        return {"path": str(folder), "total": 0, "error": "权限不足"}

    files = [f for f in all_files if f.is_file()]
    total = len(files)

    if total < 3:
        return {"path": str(folder), "total": 0, "name": folder.name, "files": total}

    # 统计
    ext_counter = defaultdict(int)
    valuable_count = 0
    image_count = 0
    recent_count = 0
    now = datetime.now()
    cutoff = now - timedelta(days=30)
    dirs_set = set()

    for f in files:
        ext = f.suffix.lower()
        ext_counter[ext] += 1
        if ext in valuable_exts:
            valuable_count += 1
        if ext in image_exts:
            image_count += 1

        # 排除目录
        dirs_set.add(f.parent)
        try:
            fstat = f.stat()
            mtime = datetime.fromtimestamp(fstat.st_mtime)
            if mtime > cutoff:
                recent_count += 1
        except OSError:
            pass

    # ---- 打分 ----
    score = 0
    details = {}

    # 1. 文件多样性 (max 25)
    variety = len(ext_counter)
    if variety >= 10:
        details["variety"] = 25
    elif variety >= 5:
        details["variety"] = 18
    elif variety >= 3:
        details["variety"] = 10
    else:
        details["variety"] = 3

    # 2. 文件总量 (max 20)
    if total >= 500:
        details["volume"] = 20
    elif total >= 100:
        details["volume"] = 15
    elif total >= 20:
        details["volume"] = 10
    elif total >= 5:
        details["volume"] = 5
    else:
        details["volume"] = 2

    # 3. 近期活跃 (max 20)
    recent_ratio = recent_count / max(total, 1)
    if recent_ratio > 0.3:
        details["recent"] = 20
    elif recent_ratio > 0.1:
        details["recent"] = 12
    elif recent_count > 0:
        details["recent"] = 5
    else:
        details["recent"] = 0

    # 4. 目录深度 (max 15)
    max_depth = max(len(f.relative_to(folder).parts) for f in files) if total > 0 else 1
    if max_depth >= 5:
        details["depth"] = 15
    elif max_depth >= 3:
        details["depth"] = 10
    elif max_depth >= 2:
        details["depth"] = 5
    else:
        details["depth"] = 2

    # 5. 文档占比 (max 10)
    doc_ratio = valuable_count / max(total, 1)
    if doc_ratio > 0.2:
        details["doc_ratio"] = 10
    elif doc_ratio > 0.05:
        details["doc_ratio"] = 6
    elif doc_ratio > 0:
        details["doc_ratio"] = 3
    else:
        details["doc_ratio"] = 0

    # 6. 图文混合 (max 10)
    has_docs = valuable_count > 0
    has_images = image_count > 3
    if has_docs and has_images and image_count > valuable_count:
        details["mixed"] = 10
    elif has_docs and has_images:
        details["mixed"] = 5
    elif has_docs:
        details["mixed"] = 2
    else:
        details["mixed"] = 0

    # 提示词加分
    hint_bonus = 0
    if hints:
        for hint in hints:
            if hint.lower() in folder.name.lower():
                hint_bonus += 10
                break

    # 汇总
    weighted = {
        "variety": details["variety"] * weights.get("file_variety", 25) / 25,
        "volume": details["volume"] * weights.get("total_files", 20) / 20,
        "recent": details["recent"] * weights.get("recent_activity", 20) / 20,
        "depth": details["depth"] * weights.get("directory_depth", 15) / 15,
        "doc_ratio": details["doc_ratio"] * weights.get("document_ratio", 10) / 10,
        "mixed": details["mixed"] * weights.get("image_document_mix", 10) / 10,
    }
    total_score = sum(weighted.values()) + hint_bonus

    return {
        "path": str(folder),
        "name": folder.name,
        "files": total,
        "subdirs": len(dirs_set),
        "max_depth": max_depth,
        "extensions": len(ext_counter),
        "ext_types": dict(sorted(ext_counter.items(), key=lambda x: x[1], reverse=True)[:10]),
        "recent_30d": recent_count,
        "score_breakdown": weighted,
        "hint_bonus": hint_bonus,
        "total": round(total_score, 1),
    }


if __name__ == "__main__":
    import yaml
    import sys

    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    results = discover_folders(config)
    for r in results:
        print(f"  [{r['total']:.0f}] {r['name']} - {r['files']} files, {r['extensions']} types")
（内容由AI生成，仅供参考）
