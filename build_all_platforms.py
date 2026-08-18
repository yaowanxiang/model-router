#!/usr/bin/env python3
"""
Model Router - 跨平台构建脚本 (Windows/macOS/Linux)
用法: python build_all_platforms.py
"""
import os
import sys
import subprocess
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
APP_NAME = "Model-Router"

# 需要打包进exe的模块/数据
DATA_ITEMS = ["config.example.json", "README.md"]

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def add_data_args():
    sep = ";" if os.name == "nt" else ":"
    args = []
    for item in DATA_ITEMS:
        args.extend(["--add-data", f"{ROOT / item}{sep}{item}"])
    # 核心模块
    for mod in ["router_core.py", "auto_router.py", "mcp_server.py"]:
        args.extend(["--add-data", f"{ROOT / mod}{sep}{mod}"])
    return args


def detect_os():
    s = platform.system().lower()
    return {"darwin": "macos", "windows": "windows", "linux": "linux"}.get(s, s)


def build():
    system = detect_os()
    print(f"当前系统: {system}")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--windowed",
        "--name", APP_NAME,
        "--hidden-import=router_core",
        "--hidden-import=auto_router",
        *add_data_args(),
        str(ROOT / "gui_app.py"),
    ]
    print("构建中...")
    subprocess.run(cmd, cwd=str(ROOT), check=True)

    # 平台化产物名
    if system == "windows":
        src = DIST / f"{APP_NAME}.exe"
        out = DIST / f"{APP_NAME}-Windows.exe"
        src.rename(out)
    elif system == "macos":
        src = DIST / f"{APP_NAME}.app"
        out = DIST / f"{APP_NAME}-macOS.app"
        if src.exists():
            src.rename(out)
        out = DIST / APP_NAME
        if out.exists():
            out.rename(DIST / f"{APP_NAME}-macOS")
    else:
        src = DIST / APP_NAME
        out = DIST / f"{APP_NAME}-Linux.AppImage"
        src.rename(out)

    print(f"✅ 构建完成!")
    for f in sorted(DIST.iterdir()):
        if f.is_file() or f.is_dir():
            print(f"   📦 {f.name}")


if __name__ == "__main__":
    build()
