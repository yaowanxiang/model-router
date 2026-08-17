# Model Router — Design Document

## 1. Problem Statement

Integrating multiple LLM providers in a single application raises three practical problems:

1. **Cost**: A fixed "best model" policy sends trivial requests to expensive frontier models.
2. **Reliability**: A single provider dependency means outages are total failures.
3. **Matching**: Task difficulty spans orders of magnitude; one model cannot serve all well.

## 2. Design Goals

| Goal | Implementation |
|------|----------------|
| Zero-cost routing decision | Keyword + length heuristics — no LLM in the routing loop |
| Cost minimization | Free tier providers first, paid as last-resort fallback |
| Resilience | Ordered candidate chains with automatic failover |
| Observability | Every call returns `tier`, `attempts`, `fallback_used`, `errors[]` |
| Portability | OpenAI-compatible `/chat/completions` only; zero third-party deps (MCP server) |

## 3. Core Concepts

### 3.1 Task Difficulty Levels

```
vision   → images, screenshots, OCR
long     → content > 2000 chars, full documents, literature reviews
complex  → analysis, code, data, statistics, reasoning, papers
medium   → writing, translation, polishing, rewriting
simple   → daily chat, quick queries
```

Classification order matters (first match wins):
`has_image → vision → content_len > 2000 → long → content_len > 500 or code fence → complex → keyword match (long/complex/medium) → simple`

### 3.2 Candidate Chain & Fallback

Each level defines an **ordered** list of `(provider, model)` candidates.
`route_and_call()` iterates the chain:

```
for candidate in chain:
    try: return call(candidate)
    except: record error, continue
raise RuntimeError("all candidates failed", errors)
```

Free providers appear early in each chain; paid providers are the safety net.
This yields ~90% free-tier coverage for everyday tasks while guaranteeing quality on hard tasks.

### 3.3 Observability

Response schema:

```json
{
  "level": "complex",
  "provider": "siliconflow",
  "model": "deepseek-ai/DeepSeek-V3.2",
  "tier": "free",
  "content": "...",
  "usage": {"total_tokens": 1234},
  "elapsed_sec": 3.2,
  "attempts": 1,
  "fallback_used": false,
  "fallback_chain": [{"provider": "...", "model": "..."}],
  "errors": []
}
```

## 4. Components

| File | Role | Lines |
|------|------|-------|
| `router_core.py` | Classification, candidate resolution, OpenAI-compatible calls, CLI | ~280 |
| `mcp_server.py` | MCP stdio server exposing 3 tools (JSON-RPC 2.0) | ~200 |
| `auto_router.py` | One-shot CLI + file-watch daemon (inbox → outbox) | ~140 |
| `config.example.json` | Data-driven provider/routing configuration template | — |

## 5. Configuration Schema

```json
{
  "providers": {
    "<slug>": {
      "name": "Display name",
      "base_url": "OpenAI-compatible base URL",
      "api_key": "key (env var override recommended)",
      "tier": "free | paid",
      "enabled": true
    }
  },
  "routing": {
    "<level>": { "candidates": [ {"provider": "<slug>", "model": "<model>"} ] }
  },
  "levels": { "<level>": "description" }
}
```

## 6. Extension Points

- **New provider**: add an entry under `providers` (any OpenAI-compatible endpoint).
- **New routing policy**: adjust keyword tables in `router_core.py` or chain order in config.
- **Vision support**: pass `image_url` (http or `data:image/...;base64,...`); router auto-selects vision level.
- **Reasoning models**: empty `content` falls back to `reasoning_content` automatically.

## 7. Security Notes

- API keys live only in local `config.json` (git-ignored); prefer env-var override in production.
- Never commit `*.key` / `*.bin` credential artifacts.
- MCP server uses stdio transport — safe for local use.
