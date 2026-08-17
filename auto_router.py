# -*- coding: utf-8 -*-
"""
auto_router.py — 任务触发自动模型路由调度器

用法:
  单次模式:  python auto_router.py "任务描述" [-c 内容] [-s 系统提示] [--image 图片路径] [--max-tokens N]
  守护模式:  python auto_router.py --watch [--dir 目录] [--interval 秒]

守护模式任务目录结构:
  <dir>/inbox/xxx.json   任务文件: {"task": "描述", "content": "", "system": "", "image": "路径", "max_tokens": 2048}
  <dir>/inbox/xxx.txt    任务文件: 第一行为任务描述，其余为内容
  处理结果自动写入 <dir>/outbox/xxx.result.json，原任务移动到 <dir>/done/

任务触发后按难度自动路由:
  vision(图片/截图) -> qwen-vl-max
  long(>2000字/文献) -> kimi-k2.7-code
  complex(分析/代码/数据/统计) -> deepseek-v4-pro
  medium(写作/翻译/润色) -> glm-5.2
  simple(日常对话/查询) -> deepseek-v4-flash
"""
import argparse
import base64
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router_core

DEFAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks")


def image_to_data_url(path):
    """本地图片 -> data URL（OpenAI 兼容多模态格式）"""
    ext = os.path.splitext(path)[1].lower().lstrip(".") or "png"
    mime = {
        "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "gif": "image/gif", "webp": "image/webp", "bmp": "image/bmp",
    }.get(ext, "image/png")
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def run_task(task_desc, content="", system=None, image=None, max_tokens=2048):
    """任务 -> 自动路由 -> 调用模型 -> 返回完整结果"""
    image_url = image_to_data_url(image) if image else None
    return router_core.route_and_call(
        task_desc=task_desc,
        content=content,
        system=system,
        max_tokens=max_tokens,
        image_url=image_url,
    )


def process_file(path, out_dir, done_dir):
    """处理一个任务文件，返回是否成功"""
    try:
        if path.endswith(".json"):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            task_desc = data.get("task") or data.get("task_desc") or ""
            content = data.get("content", "")
            system = data.get("system")
            image = data.get("image")
            max_tokens = data.get("max_tokens", 2048)
        else:
            with open(path, encoding="utf-8") as f:
                lines = f.read().splitlines()
            task_desc = lines[0] if lines else ""
            content = "\n".join(lines[1:])
            system = None
            image = None
            max_tokens = 2048
        if not task_desc:
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ {os.path.basename(path)}: 任务描述为空，跳过")
            return False
        result = run_task(task_desc, content, system, image, max_tokens)
        result["source_file"] = os.path.basename(path)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, os.path.splitext(os.path.basename(path))[0] + ".result.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        os.makedirs(done_dir, exist_ok=True)
        os.replace(path, os.path.join(done_dir, os.path.basename(path)))
        print(
            f"[{time.strftime('%H:%M:%S')}] ✅ {os.path.basename(path)} -> "
            f"[{result['level']}] {result['provider']}/{result['model']} "
            f"({result.get('usage', {}).get('total_tokens', '?')} tokens, {result.get('elapsed_sec', '?')}s)"
        )
        return True
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ❌ {os.path.basename(path)}: {type(e).__name__}: {e}")
        return False


def watch(watch_dir, interval=2.0):
    """守护模式：轮询 inbox 目录，新任务自动路由执行"""
    inbox = os.path.join(watch_dir, "inbox")
    outbox = os.path.join(watch_dir, "outbox")
    done = os.path.join(watch_dir, "done")
    for d in (inbox, outbox, done):
        os.makedirs(d, exist_ok=True)
    print(f"🔍 自动路由守护已启动，监听: {inbox}")
    print("   将任务文件（.json 或 .txt）放入 inbox/，结果自动写入 outbox/，Ctrl+C 停止")
    while True:
        try:
            for name in sorted(os.listdir(inbox)):
                p = os.path.join(inbox, name)
                if os.path.isfile(p):
                    process_file(p, outbox, done)
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n已停止")
            break


def main():
    parser = argparse.ArgumentParser(description="任务触发自动模型路由调度器")
    parser.add_argument("task", nargs="?", help="任务描述（单次模式）")
    parser.add_argument("-c", "--content", default="", help="任务内容/数据")
    parser.add_argument("-s", "--system", default=None, help="系统提示词")
    parser.add_argument("--image", default=None, help="图片路径（自动转 base64 走视觉模型）")
    parser.add_argument("--max-tokens", type=int, default=2048, help="最大输出 tokens")
    parser.add_argument("--watch", action="store_true", help="守护模式：监听任务目录自动路由")
    parser.add_argument("--dir", default=DEFAULT_DIR, help="任务目录（watch 模式）")
    parser.add_argument("--interval", type=float, default=2.0, help="轮询间隔秒数")
    args = parser.parse_args()

    if args.watch:
        watch(args.dir, args.interval)
    elif args.task:
        result = run_task(args.task, args.content, args.system, args.image, args.max_tokens)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
