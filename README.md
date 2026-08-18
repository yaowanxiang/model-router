# Model Router — Cost-Aware Multi-LLM Routing with Free-First Fallback Chain

> **Route every task to the best model automatically — free providers first, paid providers as fallback.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-12%2F12%20passing-brightgreen.svg)](tests/)
[![CI](https://github.com/yaowanxiang/model-router/actions/workflows/ci.yml/badge.svg)](https://github.com/yaowanxiang/model-router/actions)

## English Introduction

### What it is

**Model Router** is a cost-aware multi-LLM router that automatically sends every task to the best model for it — **free providers first, paid providers only as a fallback**. It comes with a no-code graphical client (download, double-click, done), plus a CLI, a Python API, an MCP server, and a file-watch daemon.

Most LLM integration code hard-codes a single model or a single API provider, which means:
- ❌ **Expensive**: every request (even trivial ones) goes to a paid frontier model
- ❌ **Fragile**: one provider outage = total failure
- ❌ **Inflexible**: no way to match model capability to task difficulty

Model Router solves all three with a simple, dependency-light design: roughly **90% of everyday tasks can be served by free-tier models**, while hard tasks still get frontier-model quality through automatic fallback.

### Key Features

- ✅ **Task Difficulty Classification**: 5 levels (`vision` / `long` / `complex` / `medium` / `simple`) via keyword + content-length heuristics — zero cost, no LLM involved
- ✅ **Free-First Fallback Chain**: each route level defines an ordered candidate chain — free providers (Zhipu, SiliconFlow, OpenRouter free models) are tried first; on any failure, the next candidate (eventually paid DeepSeek/Qwen/GLM/Kimi) is tried automatically
- ✅ **Zero Third-Party Dependencies**: core library only needs `requests`; the MCP server is pure stdlib (JSON-RPC 2.0 over stdio)
- ✅ **Multiple Interfaces**: Python API · CLI · MCP server (any MCP client: Claude, Qoder, Cursor…) · File-watch daemon
- ✅ **No-Code GUI Client**: desktop app for Windows / macOS / Linux — type a question, click Answer, routing happens automatically in the background

### Installers

**No programming needed — download the installer and double-click:**

| Platform | Download |
|----------|----------|
| 🪟 Windows | `Model-Router-Windows.exe` (download and run) |
| 🍎 macOS | `Model-Router-macOS` (App) |
| 🐧 Linux | `Model-Router-Linux.AppImage` |

**GUI features:**
- 🎯 Type a question → difficulty is detected automatically → the best free model is chosen automatically
- 🧭 Live routing info (which model is answering)
- 💬 Dark professional theme, chat-style interface
- ⚙️ Configurable role / system prompt

> All the routing logic runs automatically in the background. The user only needs to **type a question and click Answer**.

**Developer mode:**
```bash
pip install -r requirements.txt
python gui_app.py        # launch the GUI
python auto_router.py    # or use the CLI
```

### Quick Start

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

### Architecture

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

### MCP Server (for any MCP client)

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

### Task-Triggered Daemon (file-watch mode)

```bash
# One-shot
python auto_router.py "任务描述" -c "内容" --image photo.png

# Daemon: drop task files into inbox/, results appear in outbox/
python auto_router.py --watch --dir ./tasks
```

### Configuration

`config.json` structure (see `config.example.json`):
- **providers**: OpenAI-compatible endpoints with `tier` (`free` / `paid`) and optional `enabled: false`
- **routing**: per-level ordered `candidates` chains — free first, paid as safety net
- **levels**: human-readable descriptions per level

Add or remove providers freely — the router is fully data-driven.

### License

MIT — free for personal and commercial use. See [LICENSE](LICENSE).

---

# 🇨🇳 中文版介绍

## 这是什么？

**Model Router（模型路由器）** 是一个「按任务难度自动路由到最优免费模型」的开源工具：**免费模型优先，付费模型兜底**。它附带一个**无需编程、双击即用**的图形化客户端，同时提供命令行（CLI）、Python API、MCP 服务器和文件监听守护进程。

大多数 LLM 集成代码都写死单一模型或单一 API 供应商，导致：
- ❌ **贵**：每次请求（哪怕是最简单的问题）都打到付费的顶级模型上
- ❌ **脆弱**：一家供应商宕机 = 全线瘫痪
- ❌ **不灵活**：无法让模型能力匹配任务难度

Model Router 用一套轻量、无依赖的设计同时解决这三个问题：**日常任务中约 90% 都可以由免费模型完成**，而困难任务通过自动降级链依然能获得顶级模型的质量。

## 🎯 为什么做这个项目？

因为市面上大多数方案都在「杀鸡用牛刀」：
1. 简单问答也调用付费大模型，成本浪费严重；
2. 单一供应商一旦故障，整个服务就不可用；
3. 模型能力与任务难度完全不匹配，体验和成本双输。

Model Router 的答案是：**先分类、再路由、免费优先、失败自动降级**——让每一分钱都花在刀刃上，同时保证服务的稳定性。

## ✨ 核心特性

- ✅ **任务难度五级分类**：`vision`（图像）/ `long`（长文）/ `complex`（复杂）/ `medium`（中等）/ `simple`（简单），通过关键词 + 内容长度启发式判断——**零成本，不调用任何 LLM**
- ✅ **免费优先的降级链（Free-First Fallback Chain）**：每个路由级别定义一条有序候选链——先尝试免费供应商（智谱、SiliconFlow、OpenRouter 免费模型），任一环节失败自动尝试下一个候选（最终兜底为付费的 DeepSeek / Qwen / GLM / Kimi）
- ✅ **零第三方依赖**：核心库只需 `requests`；MCP 服务器纯标准库实现（stdio 上的 JSON-RPC 2.0）
- ✅ **多接口**：Python API · CLI · MCP 服务器（可接入任意 MCP 客户端：Claude、Qoder、Cursor……）· 文件监听守护进程
- ✅ **免编程图形化客户端**：Windows / macOS / Linux 桌面应用——输入问题、点击回答，路由全部在后台自动完成

## 💻 图形化客户端（傻瓜式，拿来就用）

**无需编程，下载安装包双击即用：**

| 平台 | 下载 |
|------|------|
| 🪟 Windows | `Model-Router-Windows.exe`（下载即运行） |
| 🍎 macOS | `Model-Router-macOS`（App） |
| 🐧 Linux | `Model-Router-Linux.AppImage` |

**界面功能：**
- 🎯 输入问题 → 自动识别任务难度 → 自动选择最优免费模型
- 🧭 实时显示路由信息（哪个模型在回答）
- 💬 深色专业主题，对话式界面
- ⚙️ 可设置角色提示词

> 专业的路由逻辑全部在后台自动完成，用户只需**输入问题、点击回答**。

### 开发者模式

```bash
pip install -r requirements.txt
python gui_app.py        # 启动图形界面
python auto_router.py    # 或命令行
```

## 🏗 架构

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

**路由级别**

| 级别 | 触发条件 | 典型模型 |
|------|----------|----------|
| `vision` | 图片 / 截图 / OCR | Qwen-VL、GLM-4V |
| `long` | 内容超过 2000 字符、整篇文档 | 128K 上下文模型 |
| `complex` | 分析 / 代码 / 数据 / 统计 / 推理 | DeepSeek、Qwen3-32B |
| `medium` | 写作 / 翻译 / 润色 | GLM、Qwen |
| `simple` | 日常聊天 / 快速问答 | 小型免费模型 |

**降级语义**：按顺序依次尝试候选；响应中会报告 `tier`（free/paid）、`attempts`、`fallback_used` 以及每个供应商的 `errors`，实现全程可观测。

## 🚀 快速开始

```bash
# 1. 安装（只需 requests）
pip install requests

# 2. 配置
cp config.example.json config.json
#    → 填入你的 API Key

# 3. 命令行 —— 仅分析（零成本，不调用模型）
python router_core.py analyze "分析这份气象数据"

# 4. 命令行 —— 路由并调用
python router_core.py call "翻译以下段落" --content "Hello world" --system "你是专业翻译"

# 5. Python API
from router_core import route_and_call, analyze_task
result = analyze_task("写一份论文摘要", content_len=300)
print(result["primary"])           # 第一个候选
print(result["candidates"])        # 完整降级链
text = route_and_call("总结要点", "long text...")["content"]
```

## 🖥 MCP 服务器（供任意 MCP 客户端使用）

```bash
python mcp_server.py
```

| 工具 | 说明 |
|------|------|
| `smart_call` | 自动路由 + 调用（免费优先，失败自动降级） |
| `route_analyze` | 分析难度 + 返回候选链（零成本） |
| `list_models` | 列出所有已配置的供应商、模型与路由链 |

在 MCP 客户端中注册（例如 Claude Desktop 的 `claude_desktop_config.json`）：
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

## ⏱ 任务触发守护进程（文件监听模式）

```bash
# 单次执行
python auto_router.py "任务描述" -c "内容" --image photo.png

# 守护进程：把任务文件丢进 inbox/，结果自动出现在 outbox/
python auto_router.py --watch --dir ./tasks
```

## 🔧 配置说明

`config.json` 结构（参见 `config.example.json`）：
- **providers**：OpenAI 兼容端点，含 `tier`（`free` / `paid`）和可选的 `enabled: false`
- **routing**：每个级别按顺序排列的 `candidates` 候选链——免费在前，付费兜底
- **levels**：每个级别的人类可读描述

可以自由增删供应商——路由器完全由数据驱动。

## 📄 许可证

MIT —— 个人与商业使用均免费。详见 [LICENSE](LICENSE)。

---

*灵感来自真实世界的成本优化：日常任务中约 90% 可以由免费模型完成，而困难任务通过自动降级依然能获得顶级模型的质量。*
