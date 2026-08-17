# Model Router — Cost-Aware Multi-LLM Routing with Free-First Fallback Chain

> **Route every task to the best model automatically — free providers first, paid providers as fallback.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-12%2F12%20passing-brightgreen.svg)](tests/)
[![CI](https://github.com/yaowanxiang/model-router/actions/workflows/ci.yml/badge.svg)](https://github.com/yaowanxiang/model-router/actions)

## 🎯 Why Model Router?

Most LLM integration code hard-codes a single model or uses a single API provider. This means:
- ❌ **Expensive**: every request (even trivial ones) goes to a paid frontier model
- ❌ **Fragile**: one provider outage = total failure
- ❌ **Inflexible**: no way to match model capability to task difficulty

**Model Router** solves all three with a simple, dependency-light design:

- ✅ **Task Difficulty Classification**: 5 levels (`vision` / `long` / `complex` / `medium` / `simple`) via keyword + content-length heuristics (zero cost, no LLM involved)
- ✅ **Free-First Fallback Chain**: each route level defines an ordered candidate chain — free providers (Zhipu, SiliconFlow, OpenRouter free models) are tried first; on any failure, the next candidate (eventually paid DeepSeek/Qwen/GLM/Kimi) is tried automatically
- ✅ **Zero Third-Party Dependencies**: core library only needs `requests`; the MCP server is pure stdlib (JSON-RPC 2.0 over stdio)
- ✅ **Multiple Interfaces**: Python API · CLI · MCP server (any MCP client: Claude, Qoder, Cursor…) · File-watch daemon

## 🏗 Architecture

```
                ┌─────────────────────────────────────────────┐
                │              router_core.py                 │
                │                                             │
   task_desc ──▶│  classify_task()  →  5 difficulty levels   │
   content   ──▶│  _get_candidates() → ordered provider chain│
   image ──────▶│  route_and_call()  → free-first, fallback  │
                │                                             │
                └──────────────┬──────────────────────────────┘
                               │
              ┌────────────────┼───────────────────┐
              ▼                ▼                   ▼
        auto_router.py    mcp_server.py       Python API
        (CLI + daemon)    (MCP tools)         (import router_core)
```

**Routing Levels**

| Level | Trigger | Typical Models |
|-------|---------|----------------|
| `vision` | image/screenshot/OCR | Qwen-VL, GLM-4V |
| `long` | content > 2000 chars, full documents | 128K-context models |
| `complex` | analysis/code/data/stats/reasoning | DeepSeek, Qwen3-32B |
| `medium` | writing/translation/polish | GLM, Qwen |
| `simple` | daily chat / quick queries | small free models |

**Fallback semantics**: candidates are tried in order; the response reports `tier` (free/paid), `attempts`, `fallback_used`, and per-provider `errors` for full observability.

## 🚀 Quick Start

```bash
# 1. Install (only requests is required)
pip install requests

# 2. Configure
cp config.example.json config.json
#    → fill in your API keys

# 3. CLI — analyze only (zero cost, no model call)
python router_core.py analyze "分析这份气象数据"

# 4. CLI — route and call
python router_core.py call "翻译以下段落" --content "Hello world" --system "你是专业翻译"

# 5. Python API
from router_core import route_and_call, analyze_task
result = analyze_task("写一份论文摘要", content_len=300)
print(result["primary"])           # first candidate
print(result["candidates"])        # full fallback chain
text = route_and_call("总结要点", "long text...")["content"]
```

## 🖥 MCP Server (for any MCP client)

```bash
python mcp_server.py
```

| Tool | Description |
|------|-------------|
| `smart_call` | Auto-route + call (free-first, fallback on failure) |
| `route_analyze` | Analyze difficulty + return candidate chain (zero cost) |
| `list_models` | List all configured providers, models and chains |

Register in your MCP client (e.g. Claude Desktop `claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "model-router": {
      "command": "python",
      "args": ["/path/to/model-router/mcp_server.py"],
      "env": {"PYTHONIOENCODING": "utf-8"}
    }
  }
}
```

## ⏱ Task-Triggered Daemon (file-watch mode)

```bash
# One-shot
python auto_router.py "任务描述" -c "内容" --image photo.png

# Daemon: drop task files into inbox/, results appear in outbox/
python auto_router.py --watch --dir ./tasks
```

## 🔧 Configuration

`config.json` structure (see `config.example.json`):
- **providers**: OpenAI-compatible endpoints with `tier` (`free` / `paid`) and optional `enabled: false`
- **routing**: per-level ordered `candidates` chains — free first, paid as safety net
- **levels**: human-readable descriptions per level

Add or remove providers freely — the router is fully data-driven.

## 📄 License

MIT — free for personal and commercial use. See [LICENSE](LICENSE).

---

*Inspired by real-world cost optimization: ~90% of everyday tasks can be served by free tier models, while hard tasks still get frontier-model quality through automatic fallback.*
