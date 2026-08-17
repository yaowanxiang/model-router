# -*- coding: utf-8 -*-
"""
demo.py — Model Router 零配置演示（无需 API key）

演示:
  1. 五级任务分类（vision/long/complex/medium/simple）
  2. 候选链解析（免费优先 + 付费兜底 + 禁用跳过）
  3. 完整路由决策报告（route_and_call 的 analyze 部分）

用法:  python demo.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import router_core

DEMO_TASKS = [
    ("看这张图片里的数据表", 0, False),
    ("帮我看看这个截图", 0, False),
    ("做一篇光伏热管耦合的文献综述", 3000, False),
    ("分析这份气象数据并做回归", 800, False),
    ("翻译以下段落成英文", 120, False),
    ("你好，今天天气不错", 0, False),
]

DEMO_CFG = {
    "providers": {
        "free_a": {"name": "Free Provider A", "tier": "free"},
        "free_b": {"name": "Free Provider B (disabled)", "tier": "free", "enabled": False},
        "paid_a": {"name": "Paid Provider A", "tier": "paid"},
    },
    "routing": {
        "complex": {"candidates": [
            {"provider": "free_a", "model": "free-model-1"},
            {"provider": "free_b", "model": "free-model-2"},
            {"provider": "paid_a", "model": "paid-model-1"},
        ]},
    },
    "levels": {"complex": "Complex tasks"},
}


def main():
    print("=" * 64)
    print("  Model Router — Zero-Config Demo (no API key needed)")
    print("=" * 64)

    # Part 1: task classification
    print("\n[1] Five-Level Task Classification\n" + "-" * 40)
    for desc, ln, img in DEMO_TASKS:
        level = router_core.classify_task(desc, ln, img)
        flag = " [image]" if img else ""
        print(f"  {level:8s} <- ({len(desc):3d} chars){flag} {desc[:36]}")

    # Part 2: candidate chain resolution (order / disabled skip / fallback)
    print("\n[2] Candidate Chain Resolution (free-first + paid fallback)\n" + "-" * 40)
    route = DEMO_CFG["routing"]["complex"]
    chain = router_core._get_candidates(route, DEMO_CFG)
    for i, (slug, p, model) in enumerate(chain):
        tag = "FREE" if p["tier"] == "free" else "PAID"
        print(f"  #{i + 1} [{tag}] {slug:8s} -> {model}")

    # Part 3: full routing decision report
    print("\n[3] Routing Decision Report (analyze)\n" + "-" * 40)
    for desc, ln, img in DEMO_TASKS[:4]:
        level = router_core.classify_task(desc, ln, img)
        report = {
            "task": desc,
            "level": level,
            "strategy": "free-first, automatic fallback to paid",
            "would_try": [c[0] for c in
                          router_core._get_candidates(DEMO_CFG["routing"]["complex"], DEMO_CFG)]
            if level == "complex" else ["(see config.json routing)"],
        }
        print(f"  {report['task'][:30]:32s} -> level={report['level']}")

    print("\n" + "=" * 64)
    print("  Next: cp config.example.json config.json, fill keys,")
    print("        then: python router_core.py call \"你的任务\"")
    print("=" * 64)


if __name__ == "__main__":
    main()
