"""
知识蒸馏工具 v2.0 - Flask Web 应用
通用个人知识提取，任何人/任何行业开箱即用
"""
import os
import sys
import json
import yaml
import threading
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory

# 项目根目录
BASE_DIR = Path(__file__).parent.absolute()

sys.path.insert(0, str(BASE_DIR))

from scanner import scan_directory, save_map
from extractor import batch_extract, generate_content_dump
from analyzer import KnowledgeAnalyzer, generate_summary_json
from report_generator import generate_knowledge_base
from discover import discover_folders

app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# 全局状态
task_status = {"running": False, "stage": "", "progress": 0, "message": "", "result": None}
task_lock = threading.Lock()


def load_config():
    """加载配置"""
    config_path = BASE_DIR / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def ensure_dirs(config):
    """确保输出目录存在"""
    od = config.get("output") or BASE_DIR / "output"
    os.makedirs(od, exist_ok=True)
    return str(od)


# ==================== API 路由 ====================

@app.route("/")
def index():
    return render_template("index.html", version="2.0.0")


@app.route("/api/discover", methods=["POST"])
def api_discover():
    """自动发现候选文件夹"""
    config = load_config()
    try:
        results = discover_folders(config)
        return jsonify({"success": True, "candidates": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/scan", methods=["POST"])
def api_scan():
    """扫描指定目录"""
    data = request.json or {}
    path = data.get("path", "")
    if not path or not os.path.isdir(path):
        return jsonify({"success": False, "error": "无效路径"})

    config = load_config()
    output_dir = ensure_dirs(config)
    file_map_path = os.path.join(output_dir, "file_map.json")

    try:
        result = scan_directory(path, config)
        save_map(result, file_map_path)

        return jsonify({
            "success": True,
            "summary": result["summary"],
            "file_map_path": file_map_path,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/extract", methods=["POST"])
def api_extract():
    """提取文件内容"""
    data = request.json or {}
    file_map_path = data.get("file_map_path", "")
    if not file_map_path or not os.path.exists(file_map_path):
        return jsonify({"success": False, "error": "file_map.json 不存在"})

    config = load_config()
    output_dir = ensure_dirs(config)
    content_dump_path = os.path.join(output_dir, "content_dump.md")

    try:
        result = batch_extract(file_map_path, config)
        generate_content_dump(result, content_dump_path)

        return jsonify({
            "success": True,
            "stats": result["stats"],
            "content_dump_path": content_dump_path,
            "corpus_size": len(result["corpus_text"]),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """分析扫描和提取结果"""
    data = request.json or {}
    file_map_path = data.get("file_map_path", "")
    content_dump_path = data.get("content_dump_path", "")

    if not file_map_path or not os.path.exists(file_map_path):
        return jsonify({"success": False, "error": "file_map.json 不存在"})

    config = load_config()
    output_dir = ensure_dirs(config)

    # 加载数据
    with open(file_map_path, "r", encoding="utf-8") as f:
        file_map = json.load(f)
    files = file_map.get("files", [])

    corpus_text = ""
    extraction_results = []
    if content_dump_path and os.path.exists(content_dump_path):
        with open(content_dump_path, "r", encoding="utf-8") as f:
            dump_content = f.read()
        corpus_text = dump_content
        # 从 content_dump 重建 extraction_results (简化)
        extraction_results = _parse_content_dump(dump_content)

    try:
        analyzer = KnowledgeAnalyzer(config)

        timeline = analyzer.analyze_timeline(files)
        portrait = analyzer.analyze_file_portrait(files)
        dir_structure = analyzer.analyze_directory_structure(files)
        naming = analyzer.analyze_naming(files)
        toolchain = analyzer.analyze_toolchain(files)
        templates = analyzer.analyze_templates(extraction_results)
        style = analyzer.analyze_writing_style(corpus_text)

        summary_path = os.path.join(output_dir, "summary.json")
        summary = generate_summary_json(
            analyzer, files, style, timeline, portrait,
            dir_structure, naming, toolchain, templates, summary_path,
        )

        return jsonify({
            "success": True,
            "summary": summary,
            "summary_path": summary_path,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """生成知识库报告"""
    data = request.json or {}
    summary_path = data.get("summary_path", "")
    content_dump_path = data.get("content_dump_path", "")

    if not summary_path or not os.path.exists(summary_path):
        return jsonify({"success": False, "error": "summary.json 不存在"})

    config = load_config()
    output_dir = ensure_dirs(config)

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    corpus_text = ""
    if content_dump_path and os.path.exists(content_dump_path):
        with open(content_dump_path, "r", encoding="utf-8") as f:
            corpus_text = f.read()

    report_filename = config.get("report", {}).get(
        "filename_template", "{person}_知识库_{date}.md"
    )
    # 从路径推断人物标识
    root_path = summary.get("file_snapshot", {}).get("root", "unknown")
    person = os.path.basename(root_path) or "unknown"
    date_str = datetime.now().strftime("%Y%m%d")
    report_filename = report_filename.replace("{person}", person).replace("{date}", date_str)
    report_path = os.path.join(output_dir, report_filename)

    try:
        kb_path = generate_knowledge_base(summary, corpus_text, report_path, config)
        return jsonify({
            "success": True,
            "report_path": kb_path,
            "report_name": report_filename,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/run-all", methods=["POST"])
def api_run_all():
    """一键执行全流程"""
    global task_status

    data = request.json or {}
    path = data.get("path", "")
    if not path or not os.path.isdir(path):
        return jsonify({"success": False, "error": "无效路径"})

    with task_lock:
        if task_status["running"]:
            return jsonify({"success": False, "error": "已有任务在运行中"})
        task_status = {"running": True, "stage": "初始化", "progress": 0, "message": "", "result": None}

    def run():
        global task_status
        config = load_config()
        output_dir = ensure_dirs(config)

        try:
            # 阶段 1: 扫描
            task_status["stage"] = "扫描"
            task_status["message"] = "正在扫描文件..."
            task_status["progress"] = 10

            file_map_path = os.path.join(output_dir, "file_map.json")
            scan_result = scan_directory(path, config)
            save_map(scan_result, file_map_path)

            # 阶段 2: 提取
            task_status["stage"] = "提取"
            task_status["message"] = "正在提取文件内容..."
            task_status["progress"] = 30

            content_dump_path = os.path.join(output_dir, "content_dump.md")
            extract_result = batch_extract(file_map_path, config)
            generate_content_dump(extract_result, content_dump_path)

            # 阶段 3: 分析
            task_status["stage"] = "分析"
            task_status["message"] = "正在分析工作模式..."
            task_status["progress"] = 60

            files = scan_result["files"]
            corpus_text = extract_result["corpus_text"]

            analyzer = KnowledgeAnalyzer(config)
            timeline = analyzer.analyze_timeline(files)
            portrait = analyzer.analyze_file_portrait(files)
            dir_structure = analyzer.analyze_directory_structure(files)
            naming = analyzer.analyze_naming(files)
            toolchain = analyzer.analyze_toolchain(files)
            templates = analyzer.analyze_templates(extract_result["extraction_results"])
            style = analyzer.analyze_writing_style(corpus_text)

            summary_path = os.path.join(output_dir, "summary.json")
            summary = generate_summary_json(
                analyzer, files, style, timeline, portrait,
                dir_structure, naming, toolchain, templates, summary_path,
            )

            # 阶段 4: 生成报告
            task_status["stage"] = "生成报告"
            task_status["message"] = "正在生成知识库..."
            task_status["progress"] = 85

            person = os.path.basename(path) or "unknown"
            report_filename = f"{person}_知识库_{datetime.now().strftime('%Y%m%d')}.md"
            report_path = os.path.join(output_dir, report_filename)
            generate_knowledge_base(summary, corpus_text, report_path, config)

            task_status["stage"] = "完成"
            task_status["message"] = "知识库生成完毕"
            task_status["progress"] = 100
            task_status["result"] = {
                "report_path": report_path,
                "report_name": report_filename,
                "file_map_path": file_map_path,
                "content_dump_path": content_dump_path,
                "summary_path": summary_path,
                "stats": {
                    "files": scan_result["summary"]["total_files"],
                    "size_gb": scan_result["summary"]["total_size_gb"],
                    "extracted": extract_result["stats"]["extracted"],
                    "total_chars": extract_result["stats"]["total_chars"],
                },
            }
        except Exception as e:
            import traceback
            task_status["stage"] = "错误"
            task_status["message"] = str(e)
            task_status["progress"] = 0
            task_status["running"] = False
            traceback.print_exc()

        task_status["running"] = False

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"success": True, "message": "任务已启动"})


@app.route("/api/status")
def api_status():
    """查询任务状态"""
    return jsonify(task_status)


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    """查看和更新配置"""
    config_path = BASE_DIR / "config.yaml"
    if request.method == "GET":
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return jsonify({"success": True, "config": yaml.safe_load(f)})
        return jsonify({"success": False, "error": "config.yaml 不存在"})

    data = request.json or {}
    new_config = data.get("config", {})
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(new_config, f, allow_unicode=True, default_flow_style=False)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ==================== 辅助函数 ====================

def _parse_content_dump(content: str) -> list:
    """从 content_dump 解析出简单的 extraction_results"""
    results = []
    for block in content.split("\n### "):
        if not block.strip():
            continue
        lines = block.strip().split("\n", 1)
        fname = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        results.append({
            "file": fname,
            "type": "text",
            "text": body,
            "category": "document",
            "extension": Path(fname).suffix.lower() if "." in fname else "",
        })
    return results


# ==================== 启动 ====================

if __name__ == "__main__":
    port = 8932
    print(f"\n{'=' * 50}")
    print(f"  知识蒸馏工具 v2.0")
    print(f"  通用个人知识提取  |  任何人/任何行业")
    print(f"  地址: http://127.0.0.1:{port}")
    print(f"{'=' * 50}\n")
    app.run(host="127.0.0.1", port=port, debug=False)
（内容由AI生成，仅供参考）
