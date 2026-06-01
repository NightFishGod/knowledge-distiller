"""
知识蒸馏 v2.0 打包为 .exe
使用: python build_exe.py
"""
import subprocess
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.absolute()
OUTPUT_DIR = BASE_DIR.parent

def build():
    print("安装 PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])

    print("开始打包...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "知识蒸馏工具-v2.0",
        "--add-data", f"{BASE_DIR / 'templates'};templates",
        "--add-data", f"{BASE_DIR / 'static'};static",
        "--add-data", f"{BASE_DIR / 'config.yaml'};.",
        "--hidden-import", "docx",
        "--hidden-import", "pptx",
        "--hidden-import", "openpyxl",
        "--hidden-import", "yaml",
        "--hidden-import", "flask",
        "--distpath", str(OUTPUT_DIR),
        "--workpath", str(BASE_DIR / "build"),
        "--specpath", str(BASE_DIR / "build"),
        str(BASE_DIR / "app.py"),
    ]

    subprocess.check_call(cmd, cwd=str(BASE_DIR))
    print(f"\n打包完成: {OUTPUT_DIR / '知识蒸馏工具-v2.0.exe'}")

if __name__ == "__main__":
    build()
（内容由AI生成，仅供参考）
