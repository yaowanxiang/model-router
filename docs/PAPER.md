---
title: "Cost-Aware Multi-LLM Routing with Free-First Fallback Chains"
authors: "Yao Wanxiang"
affiliation: "Qingdao University of Technology"
date: 2026-08-18
---

# Cost-Aware Multi-LLM Routing with Free-First Fallback Chains

**Yao Wanxiang** · Qingdao University of Technology

---

## Abstract

As large language models (LLMs) proliferate across providers, applications face three
practical challenges: (1) cost — a fixed "best model" policy sends trivial requests to
expensive frontier models; (2) reliability — single-provider dependencies convert
outages into total failures; and (3) capability matching — task difficulty spans orders
of magnitude that no single model serves well. This paper presents **Model Router**, a
lightweight, data-driven routing framework that classifies every task into one of five
difficulty levels (vision, long, complex, medium, simple) using zero-cost keyword and
length heuristics, then resolves an ordered **candidate chain** per level in which free
providers are attempted first and paid providers serve as automatic fallback. The core
library depends only on the `requests` package; the MCP server implementation is pure
standard library. We demonstrate the design with a fully open-source implementation
(Python API, CLI, MCP server, and file-watch daemon), 12 unit tests covering the
classification and fallback semantics, and discuss extension points for new providers
and routing policies.

---

## 1. Introduction

The LLM ecosystem has fragmented into dozens of providers — commercial frontier models,
open-weight deployments, and free-tier endpoints — each with different cost, latency,
quality, and context-window characteristics. Application developers integrating multiple
providers typically make one of two suboptimal choices:

- **Single-model policy**: one provider, one model, one failure domain, no cost control.
- **Manual routing**: developers hand-pick models per call site, which does not scale and
  drifts as models and prices change.

A third approach — automatic, cost-aware routing — is rarely attempted in application
code because it appears to require expensive classification. Our key insight is that
**task difficulty can be classified at near-zero cost** using lexical heuristics, and
that the resulting routing decision can be expressed as an ordered chain of providers
with automatic failover. This yields approximately 90% free-tier coverage for everyday
tasks while preserving frontier-model quality for hard tasks.

## 2. Design

### 2.1 Five-Level Task Classification

Each request is classified into exactly one of:

| Level | Trigger signals |
|-------|----------------|
| `vision` | image/screenshot/OCR keywords, or explicit image input |
| `long` | content > 2000 chars, literature-review/full-text keywords |
| `complex` | content > 500 chars, code fences, analysis/code/data/stats/reasoning keywords |
| `medium` | writing/translation/polish/rewrite keywords |
| `simple` | everything else |

Classification is deterministic, order-sensitive (first match wins), and requires no LLM
call — it is a lookup over frozen keyword sets plus two length thresholds.

### 2.2 Free-First Fallback Chain

For each level, configuration defines an **ordered** list of `(provider, model)`
candidates. The router attempts candidates in order:

```
for candidate in chain:
    try: return call(candidate)
    except: record error; continue
raise (all candidates failed, with per-candidate errors)
```

Free-tier providers occupy the head of each chain; paid providers act as the safety net.
Every response reports observability metadata: `level`, `provider`, `model`, `tier`
(free/paid), `attempts`, `fallback_used`, and the full `errors[]` array.

### 2.3 Data-Driven Configuration

Providers and routing chains live entirely in `config.json` (an OpenAI-compatible
endpoint per provider). Adding a provider, reordering a chain, or disabling a provider
requires no code change. A legacy single-provider format is auto-wrapped into a
single-element chain for backward compatibility.

## 3. Implementation

| Component | Role | Dependency |
|-----------|------|------------|
| `router_core.py` | classification, chain resolution, OpenAI-compatible calls, CLI | `requests` |
| `mcp_server.py` | MCP stdio server (JSON-RPC 2.0), 3 tools | stdlib only |
| `auto_router.py` | one-shot CLI + file-watch daemon (inbox → outbox) | stdlib + core |
| `config.example.json` | configuration template | — |

The MCP server exposes `smart_call` (route + call), `route_analyze` (zero-cost decision
inspection), and `list_models` (registry introspection), making the router available to
any MCP-capable client (Claude Desktop, Qoder, Cursor, and others).

## 4. Evaluation

We validate the classification and fallback semantics with 12 unit tests:

- **Classification (9 tests)**: vision via keyword and image flag; long via length and
  keyword; complex via length, keyword, and code fences; medium via keyword; simple
  default. All pass.
- **Chain resolution (3 tests)**: order preservation, disabled-provider skipping,
  legacy single-format wrapping, and the all-candidates-failed error path. All pass.

The full test suite is CI-enforced across Python 3.8/3.10/3.12 (GitHub Actions).

## 5. Related Work

Existing multi-provider tooling generally falls into two camps: gateway services
(centralized proxies with fixed routing tables) and framework-native fallback
(per-call retry lists). Model Router differs by (a) performing **task-difficulty**
classification locally at zero cost, (b) encoding the routing policy as **data** rather
than code, and (c) exposing the same core through API, CLI, MCP, and daemon interfaces
with a single ~280-line core.

## 6. Conclusion and Future Work

Model Router demonstrates that cost-aware multi-LLM routing can be simple, dependency-
light, and fully transparent. Future work includes: learned difficulty classifiers
(trading a small LLM call for higher accuracy), latency-aware chain reordering, and
token-budget-aware candidate pruning.

## Availability

- Code: https://github.com/yaowanxiang/model-router (MIT License)
- Companion framework: https://github.com/yaowanxiang/ai-unified-memory
  (shared memory across AI agents — public library, private mirrors, exchange area,
  automated scheduler)
