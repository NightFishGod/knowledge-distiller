"""
知识蒸馏 v2.0 - 文件扫描器
递归扫描目录，生成结构化 file_map.json
"""
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def scan_directory(root_path: str, config: dict = None, progress_callback=None) -> dict:
    """
    递归扫描目录，返回结构化文件地图

    返回:
    {
        "root": str,
        "scan_time": str,
        "summary": {...},
        "files": [{name, path, size_mb, modified, extension, category, md5}, ...],
        "directory_tree": {...}
    }
    """
    root = Path(root_path).resolve()
    if not root.exists():
        return {"error": f"路径不存在: {root_path}"}
    if not root.is_dir():
        return {"error": f"不是目录: {root_path}"}

    cfg = config or {}
    sc = cfg.get("scanner", {})
    ignore_names = set(sc.get("ignore_names", [".DS_Store", "Thumbs.db", "~$", ".WeDrive"]))
    max_size_mb = sc.get("max_file_mb", 500)

    # 扩展名分类
    doc_exts = set(sc.get("document_exts", [".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".pdf", ".txt", ".md", ".csv"]))
    img_exts = set(sc.get("image_exts", [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".tiff"]))
    design_exts = set(sc.get("design_exts", [".psd", ".ai", ".sketch", ".fig", ".xd", ".cdr", ".eps"]))
    video_exts = set(sc.get("video_exts", [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"]))
    archive_exts = set(sc.get("archive_exts", [".zip", ".rar", ".7z", ".tar", ".gz"]))
    code_exts = set(sc.get("code_exts", [".py", ".js", ".ts", ".html", ".css", ".java", ".go", ".rs"]))

    files = []
    total_size = 0
    type_counter = defaultdict(int)
    scanned = 0

    for entry in root.rglob("*"):
        if entry.is_file():
            name = entry.name
            if any(name.startswith(ig) for ig in ignore_names if ig):
                continue

            try:
                stat = entry.stat()
                size_mb = stat.st_size / (1024 * 1024)
                if size_mb > max_size_mb:
                    continue

                ext = entry.suffix.lower()
                if ext in doc_exts:
                    cat = "document"
                elif ext in img_exts:
                    cat = "image"
                elif ext in design_exts:
                    cat = "design"
                elif ext in video_exts:
                    cat = "video"
                elif ext in archive_exts:
                    cat = "archive"
                elif ext in code_exts:
                    cat = "code"
                else:
                    cat = "other"

                mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

                files.append({
                    "name": name,
                    "path": str(entry),
                    "relative_path": str(entry.relative_to(root)),
                    "size_mb": round(size_mb, 3),
                    "size_bytes": stat.st_size,
                    "modified": mtime,
                    "extension": ext,
                    "category": cat,
                })

                total_size += size_mb
                type_counter[cat] += 1
                scanned += 1

                if progress_callback and scanned % 100 == 0:
                    progress_callback(scanned, 0, f"扫描中: {scanned} 个文件...")

            except (PermissionError, OSError):
                continue

    # 构建目录树
    dir_tree = _build_tree(files, root)

    return {
        "root": str(root),
        "scan_time": datetime.now().isoformat(),
        "summary": {
            "total_files": len(files),
            "total_size_mb": round(total_size, 2),
            "total_size_gb": round(total_size / 1024, 2),
            "type_distribution": dict(type_counter),
        },
        "files": files,
        "directory_tree": dir_tree,
    }


def _build_tree(files: list, root: Path) -> dict:
    """构建目录树结构"""
    tree = {}
    root_str = str(root)

    for f in files:
        rel = f.get("relative_path", "")
        parts = Path(rel).parts
        current = tree
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        # 叶子节点
        leaf_name = parts[-1] if parts else f["name"]
        current[leaf_name] = {
            "size_mb": f["size_mb"],
            "category": f["category"],
            "modified": f["modified"],
        }

    return tree


def save_map(scan_result: dict, output_path: str):
    """保存 file_map.json"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scan_result, f, ensure_ascii=False, indent=2)
    return output_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        target = sys.argv[1]
        output = sys.argv[2] if len(sys.argv) > 2 else "file_map.json"
        print(f"扫描: {target}")
        result = scan_directory(target)
        save_map(result, output)
        print(f"完成: {result['summary']['total_files']} 文件, {result['summary']['total_size_mb']:.1f} MB")
        print(f"输出: {output}")
（内容由AI生成，仅供参考）
