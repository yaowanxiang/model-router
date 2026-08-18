# -*- coding: utf-8 -*-
"""
desktop.py — Model Router 桌面客户端入口
架构: pywebview 原生窗口 + 内嵌 FastAPI (threading 线程, localhost 随机端口)
打包: PyInstaller --onefile --windowed
"""
import os
import sys
import socket
import threading
import time
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    BASE_DIR = Path(sys._MEIPASS)          # PyInstaller 解包目录(只读)
    DATA_DIR = Path.home() / ".model-router"
else:
    BASE_DIR = Path(__file__).resolve().parent
    DATA_DIR = BASE_DIR / "data"

APP_TITLE = "Model Router — 免费优先多模型路由"
DEFAULT_SIZE = (1100, 760)


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _run_api(port: int) -> None:
    """内嵌 FastAPI 服务（必须 threading，不能用 multiprocessing！）"""
    sys.path.insert(0, str(BASE_DIR))
    import uvicorn
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from api import build_app

    # 打包环境: config.json 使用用户可写目录，避免写入只读 _MEIPASS
    if FROZEN:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        cfg_file = DATA_DIR / "config.json"
        if not cfg_file.exists():
            example = Path(sys._MEIPASS) / "config.example.json"
            if example.exists():
                import shutil
                shutil.copy(example, cfg_file)
        import router_core
        router_core.CONFIG_PATH = str(cfg_file)

    app = build_app(BASE_DIR)
    # 移除根路由避免抢占 StaticFiles
    app.routes[:] = [r for r in app.routes
                     if not (getattr(r, "path", None) == "/"
                             and getattr(r, "methods", None) == {"GET"})]
    web_dir = BASE_DIR / "web"
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True))
    config = uvicorn.Config(app, host="127.0.0.1", port=port,
                            log_level="warning", access_log=False)
    uvicorn.Server(config).run()


def _wait_ready(port: int, timeout: float = 12.0) -> bool:
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def main() -> None:
    if FROZEN:
        import multiprocessing
        multiprocessing.freeze_support()   # 防御性
    port = find_free_port()
    threading.Thread(target=_run_api, args=(port,), daemon=True).start()
    _wait_ready(port)
    import webview
    webview.create_window(APP_TITLE, f"http://127.0.0.1:{port}/",
                          width=DEFAULT_SIZE[0], height=DEFAULT_SIZE[1],
                          min_size=(880, 600))
    webview.start()


if __name__ == "__main__":
    main()
