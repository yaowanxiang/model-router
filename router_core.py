"""
router_core.py — Qoder 模型路由核心库（免费优先 + 付费兜底回退链）

根据任务难度自动选择模型，按 candidates 链依次尝试：
  免费 provider 优先（zhipu / siliconflow / openrouter），
  全部失败时自动回退到付费 provider（deepseek / qwen / glm / kimi）。

路由级别:
  vision  -> 视觉/图片
  long    -> 长上下文 >2000 字 / 文献全文
  complex -> 分析/代码/推理/论文/统计
  medium  -> 写作/翻译/润色/改写
  simple  -> 日常对话/快捷查询

用法:
  from router_core import route_and_call, analyze_task
  result = route_and_call("分析这份气象数据", "内容...", system="你是一名气象数据分析师")
"""
import json
import os
import sys
import time
import requests

# Windows 控制台 UTF-8 输出（避免中文乱码 / UnicodeEncodeError）
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# ==================== 关键词表（与 hermes guardian 同步） ====================

VISION_KW = frozenset([
    "图片", "截图", "图像", "照片", "画面", "看图", "图里", "图中有", "图上",
    "扫描件", "识别图片", "OCR", "视觉", "看这张图", "这张图", "这张图片",
    "image", "picture", "screenshot", "photo", "ocr", "vision", "visual",
    "look at this image", "what is in this",
])

LONG_KW = frozenset([
    "文献综述", "综述", "长文本", "大段", "全文", "完整文献", "论文全文", "书籍",
    "报告全文", "历史文献", "档案", "资料", "学位论文", "毕业论文", "开题报告",
    "结题报告", "中文摘要", "整本", "全部内容", "全文翻译", "长文",
    "literature review", "full text", "full paper", "summarize paper",
    "long document", "entire document", "comprehensive review",
])

COMPLEX_KW = frozenset([
    "分析", "对比", "比较", "评估", "审查", "设计", "架构", "方案", "实现", "重构",
    "论文", "文献", "研究", "实验", "数据", "统计", "回归", "推导", "证明", "计算",
    "建模", "模拟", "仿真", "步骤", "流程", "计划", "逐步", "详细", "调试", "优化",
    "性能", "修复", "排查", "报告", "总结", "文档", "生成", "起草", "基金", "申请",
    "项目", "课题", "创新点", "科学问题", "技术路线", "逻辑重构", "导出", "演绎",
    "导出公式", "微分方程", "偏导数", "气象数据", "数据集", "清洗", "质检", "爬取",
    "解析", "提取", "批量", "转换", "下载", "脚本", "程序", "代码",
    "review", "analyze", "design", "refactor", "implement", "optimize",
    "research", "paper", "literature", "statistical", "regression",
    "simulate", "architecture", "comprehensive", "detailed",
    "step-by-step", "draft", "report", "summary",
    "derive", "proof", "equation", "differential", "calculus",
])

MEDIUM_KW = frozenset([
    "写作", "初稿", "润色", "翻译", "摘要", "缩写", "扩写", "改写", "重写", "表达",
    "语句", "段落", "格式", "排版", "中文", "表述", "描述", "陈述", "说明", "介绍",
    "解释", "政策", "规范", "格式要求", "项目申请书", "基金初稿", "通知", "邮件",
    "写", "translate", "paraphrase", "rewrite", "polish", "format",
    "draft", "abstract", "introduction", "background",
])


# ==================== 任务难度判定 ====================

def classify_task(task_desc: str, content_len: int = 0, has_image: bool = False) -> str:
    """返回: vision / long / complex / medium / simple"""
    if has_image:
        return "vision"
    text = (task_desc or "").lower()
    if any(kw in text for kw in VISION_KW):
        return "vision"
    if content_len > 2000:
        return "long"
    if content_len > 500 or "```" in text:
        return "complex"
    if any(kw in text for kw in LONG_KW):
        return "long"
    if any(kw in text for kw in COMPLEX_KW):
        return "complex"
    if any(kw in text for kw in MEDIUM_KW):
        return "medium"
    return "simple"


# ==================== 候选链解析（免费优先 + 付费兜底） ====================

def _get_candidates(route: dict, cfg: dict) -> list:
    """解析路由的 candidates 候选链，返回 [(slug, provider_cfg, model), ...]

    兼容旧格式 {"provider": "...", "model": "..."}（自动包装为单元素链），
    跳过 enabled: false 的 provider。
    """
    providers = cfg["providers"]
    candidates = route.get("candidates")
    if candidates is None:
        # 旧格式兼容：单模型路由
        candidates = [{"provider": route.get("provider"), "model": route.get("model")}]
    chain = []
    for item in candidates:
        slug = item.get("provider", "")
        provider = providers.get(slug)
        if not provider or provider.get("enabled") is False:
            continue
        chain.append((slug, provider, item.get("model", "")))
    if not chain:
        raise RuntimeError("该路由没有可用候选（所有 provider 被禁用或未配置）")
    return chain


def analyze_task(task_desc: str, content_len: int = 0, has_image: bool = False) -> dict:
    """只做路由分析，不调用模型（零成本），返回完整候选链"""
    level = classify_task(task_desc, content_len, has_image)
    cfg = _load_config()
    route = cfg["routing"][level]
    candidates = [{
        "provider": slug,
        "provider_name": p["name"],
        "tier": p.get("tier", "paid"),
        "model": m,
    } for slug, p, m in _get_candidates(route, cfg)]
    return {
        "level": level,
        "level_desc": cfg["levels"].get(level, ""),
        "primary": candidates[0],
        "candidates": candidates,
    }


# ==================== API 调用（OpenAI 兼容） ====================

def _load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def chat_completion(provider_cfg: dict, model: str, messages: list,
                    max_tokens: int = 2048, temperature: float = 0.7,
                    timeout: int = 120) -> dict:
    """调用 OpenAI 兼容 /chat/completions 接口"""
    url = provider_cfg["base_url"].rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {provider_cfg['api_key']}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"API {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def route_and_call(task_desc: str, content: str = "", system: str = None,
                   max_tokens: int = 2048, temperature: float = 0.7,
                   has_image: bool = False, image_url: str = None,
                   timeout: int = 120) -> dict:
    """自动路由 + 免费优先调用，失败自动回退下一候选（付费兜底）

    返回结果含 tier（free/paid）、attempts（尝试次数）、
    fallback_used（是否发生过回退）、errors（每次失败原因）。
    """
    t0 = time.time()
    cfg = _load_config()
    level = classify_task(task_desc, len(content or ""), has_image or bool(image_url))
    route = cfg["routing"][level]
    chain = _get_candidates(route, cfg)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    if image_url:
        # 多模态消息：图片 + 文字
        parts = [{"type": "image_url", "image_url": {"url": image_url}}]
        if content or task_desc:
            parts.append({"type": "text", "text": content if content else task_desc})
        messages.append({"role": "user", "content": parts})
    else:
        messages.append({"role": "user", "content": content if content else task_desc})

    errors = []
    for idx, (slug, provider, model) in enumerate(chain):
        try:
            raw = chat_completion(provider, model, messages,
                                  max_tokens=max_tokens, temperature=temperature, timeout=timeout)
        except Exception as e:
            errors.append({"provider": slug, "model": model, "error": f"{type(e).__name__}: {e}"})
            continue
        usage = raw.get("usage", {})
        # 兼容推理模型：content 为空时回退读取 reasoning_content
        msg = raw["choices"][0]["message"]
        text = msg.get("content") or ""
        if not text:
            text = msg.get("reasoning_content") or ""
        return {
            "level": level,
            "level_desc": cfg["levels"].get(level, ""),
            "provider": slug,
            "provider_name": provider["name"],
            "tier": provider.get("tier", "paid"),
            "model": model,
            "content": text,
            "usage": usage,
            "elapsed_sec": round(time.time() - t0, 2),
            "attempts": idx + 1,
            "fallback_used": idx > 0,
            "fallback_chain": [{"provider": s, "model": m} for s, _, m in chain],
            "errors": errors,
        }
    raise RuntimeError(
        f"路由 {level} 全部候选失败（{len(chain)} 个）: "
        + "; ".join(f"{e['provider']}/{e['model']} -> {e['error']}" for e in errors)
    )


# ==================== CLI 入口 ====================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Qoder 模型路由 CLI（免费优先 + 付费兜底）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_analyze = sub.add_parser("analyze", help="只分析任务难度与候选链，不调用模型")
    p_analyze.add_argument("task", help="任务描述")

    p_call = sub.add_parser("call", help="自动路由并调用模型（免费优先，失败回退付费）")
    p_call.add_argument("task", help="任务描述")
    p_call.add_argument("--content", "-c", default="", help="任务内容/数据")
    p_call.add_argument("--system", "-s", default=None, help="系统提示词")
    p_call.add_argument("--max-tokens", type=int, default=2048)
    p_call.add_argument("--json", action="store_true", help="输出 JSON")

    args = parser.parse_args()
    if args.cmd == "analyze":
        print(json.dumps(analyze_task(args.task), ensure_ascii=False, indent=2))
    elif args.cmd == "call":
        result = route_and_call(args.task, args.content, args.system, args.max_tokens)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            tier = result.get("tier", "")
            if tier == "free":
                flag = "（免费）"
            elif result.get("fallback_used"):
                flag = "（付费兜底）"
            else:
                flag = "（付费）"
            print(f"[{result['level']}] {result['provider']}/{result['model']} {flag}")
            print(result["content"])


if __name__ == "__main__":
    main()
