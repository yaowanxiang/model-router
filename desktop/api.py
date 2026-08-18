# -*- coding: utf-8 -*-
"""
api.py — Model Router 桌面客户端后端 API
提供: 健康检查 / 路由分析 / 模型调用 / 配置查看(密钥脱敏)
"""
import json
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import router_core


class AnalyzeReq(BaseModel):
    task_desc: str
    content_len: int = 0
    has_image: bool = False


class CallReq(BaseModel):
    task_desc: str
    content: str = ""
    system: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.7
    has_image: bool = False
    image_url: Optional[str] = None


def mask_keys(obj):
    """递归脱敏 api_key 字段"""
    if isinstance(obj, dict):
        return {k: ("***" if any(s in k.lower() for s in ("key", "token", "secret"))
                    else mask_keys(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [mask_keys(i) for i in obj]
    return obj


def build_app(base_dir: Path) -> FastAPI:
    app = FastAPI(title="Model Router Desktop")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "name": "model-router-desktop"}

    @app.post("/api/analyze")
    def analyze(req: AnalyzeReq):
        try:
            return router_core.analyze_task(req.task_desc, req.content_len, req.has_image)
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}"}

    @app.post("/api/call")
    def call(req: CallReq):
        try:
            return router_core.route_and_call(
                task_desc=req.task_desc,
                content=req.content,
                system=req.system,
                max_tokens=req.max_tokens,
                temperature=req.temperature,
                has_image=req.has_image,
                image_url=req.image_url,
            )
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}"}

    @app.get("/api/config")
    def config():
        try:
            cfg = router_core._load_config()
            return mask_keys(cfg)
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}"}

    @app.get("/api/levels")
    def levels():
        try:
            cfg = router_core._load_config()
            return {"levels": cfg.get("levels", {})}
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}"}

    return app
