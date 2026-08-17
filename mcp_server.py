"""
mcp_server.py — Qoder 模型路由 MCP 服务器（stdio, 零第三方依赖）

暴露 3 个工具:
  smart_call    按任务难度自动路由并调用最优模型 (vision/long/complex/medium/simple)
                免费 provider 优先，失败自动回退付费 provider
  route_analyze 只分析任务难度与候选链，不调用（零成本）
  list_models   列出所有已配置 provider、模型及候选链

MCP 协议: stdio + 换行分隔 JSON-RPC 2.0
启动: python mcp_server.py
"""
import json
import os
import sys

# stdin/stdout 强制 UTF-8（避免 PowerShell 管道中文乱码导致关键词匹配失败）
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    if _stream and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router_core

SERVER_INFO = {"name": "model-router", "version": "2.0.0"}
PROTOCOL_VERSION = "2025-03-26"

TOOLS = [
    {
        "name": "smart_call",
        "description": (
            "按任务难度自动路由并调用模型（vision/long/complex/medium/simple 五级），"
            "免费 provider 优先（智谱/硅基流动/OpenRouter 免费模型），调用失败自动回退"
            "下一候选，最后兜底付费 provider（DeepSeek/Qwen/GLM/Kimi）。"
            "返回模型输出、路由级别、tier(免费/付费)、是否回退与 token 用量。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_desc": {
                    "type": "string",
                    "description": "任务描述（如：分析这份气象数据、翻译以下段落）",
                },
                "content": {
                    "type": "string",
                    "description": "任务内容/数据正文（可为空，为空时以 task_desc 作为用户消息）",
                    "default": "",
                },
                "system": {
                    "type": "string",
                    "description": "可选系统提示词（如：你是一名气象数据分析师）",
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "最大输出 tokens",
                    "default": 2048,
                },
                "has_image": {
                    "type": "boolean",
                    "description": "任务是否包含图片/截图（true 时自动走视觉路由）",
                    "default": False,
                },
                "image_url": {
                    "type": "string",
                    "description": "可选，图片地址（http(s) URL 或 data:image/png;base64,...），提供时自动走视觉路由",
                },
            },
            "required": ["task_desc"],
        },
    },
    {
        "name": "route_analyze",
        "description": (
            "只分析任务难度并返回完整候选链（含 tier 免费/付费标记，不调用模型，零成本）。"
            "用于在正式调用前确认路由决策。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_desc": {"type": "string", "description": "任务描述"},
                "content_len": {
                    "type": "integer",
                    "description": "内容长度（字符数），影响难度判定",
                    "default": 0,
                },
                "has_image": {
                    "type": "boolean",
                    "description": "任务是否包含图片",
                    "default": False,
                },
            },
            "required": ["task_desc"],
        },
    },
    {
        "name": "list_models",
        "description": "列出所有已配置的 AI provider（含 tier 免费/付费）、模型及每级路由的候选链。",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _send(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _handle_tools_list() -> dict:
    return {"tools": TOOLS}


def _handle_tools_call(params: dict) -> dict:
    name = params.get("name", "")
    args = params.get("arguments", {}) or {}
    try:
        if name == "smart_call":
            result = router_core.route_and_call(
                task_desc=args.get("task_desc", ""),
                content=args.get("content", ""),
                system=args.get("system"),
                max_tokens=args.get("max_tokens", 2048),
                has_image=args.get("has_image", False),
                image_url=args.get("image_url"),
            )
            text = json.dumps(result, ensure_ascii=False, indent=2)
            return {"content": [{"type": "text", "text": text}]}
        elif name == "route_analyze":
            result = router_core.analyze_task(
                task_desc=args.get("task_desc", ""),
                content_len=args.get("content_len", 0),
                has_image=args.get("has_image", False),
            )
            return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
        elif name == "list_models":
            cfg = router_core._load_config()
            result = {
                "routing": cfg["routing"],
                "providers": {
                    slug: {
                        "name": p["name"],
                        "base_url": p["base_url"],
                        "tier": p.get("tier", "paid"),
                        "enabled": p.get("enabled", True),
                    }
                    for slug, p in cfg["providers"].items()
                },
            }
            return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
        else:
            return {
                "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                "isError": True,
            }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error: {type(e).__name__}: {e}"}],
            "isError": True,
        }


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = msg.get("method")
        msg_id = msg.get("id")

        if method == "initialize":
            _send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": SERVER_INFO,
                },
            })
        elif method == "notifications/initialized":
            continue  # 无需响应
        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": msg_id, "result": _handle_tools_list()})
        elif method == "tools/call":
            _send({"jsonrpc": "2.0", "id": msg_id, "result": _handle_tools_call(msg.get("params", {}))})
        elif method == "ping":
            _send({"jsonrpc": "2.0", "id": msg_id, "result": {}})
        # 其他未知方法：返回错误


if __name__ == "__main__":
    main()
