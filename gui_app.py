#!/usr/bin/env python3
"""
Model Router 图形化客户端 - 傻瓜式AI模型路由问答工具
自动根据任务难度选择最优免费模型，付费兜底，无需懂技术
"""
import os
import sys
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path

# 强制UTF-8 (Windows控制台兼容)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 导入路由核心
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from router_core import route_and_call, analyze_task
    ROUTER_OK = True
except Exception as e:
    ROUTER_OK = False
    _import_err = str(e)


class RouterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 AI模型路由器 v1.0.0 - 免费优先·自动选路")
        self.root.geometry("860x720")
        self.root.minsize(760, 620)

        # 主题
        self.bg = "#0f172a"
        self.bg2 = "#1e293b"
        self.fg = "#f8fafc"
        self.accent = "#38bdf8"
        self.green = "#10b981"
        self.purple = "#a78bfa"
        self.root.configure(bg=self.bg)

        self._build_header()
        self._build_task_panel()
        self._build_button_panel()
        self._build_result_panel()
        self._build_statusbar()

    def _build_header(self):
        h = tk.Frame(self.root, bg=self.bg)
        h.pack(fill=tk.X, padx=20, pady=(15, 5))
        tk.Label(h, text="🤖 AI 模型路由器", font=("Microsoft YaHei", 20, "bold"),
                 bg=self.bg, fg=self.fg).pack(side=tk.LEFT)
        tk.Label(h, text="免费优先 · 自动选路 · 付费兜底",
                 font=("Microsoft YaHei", 10), bg=self.bg2, fg=self.accent,
                 padx=10, pady=4).pack(side=tk.RIGHT)

    def _build_task_panel(self):
        p = tk.Frame(self.root, bg=self.bg2, padx=15, pady=10)
        p.pack(fill=tk.X, padx=20, pady=8)

        # 任务类型
        row1 = tk.Frame(p, bg=self.bg2)
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="🎯 任务类型:", font=("Microsoft YaHei", 11),
                 bg=self.bg2, fg=self.fg).pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="自动识别")
        modes = ["自动识别", "简单问答", "写作翻译", "分析推理", "代码开发", "长文档处理", "看图理解"]
        ttk.Combobox(row1, textvariable=self.mode_var, values=modes,
                     font=("Microsoft YaHei", 10), state="readonly", width=20).pack(side=tk.LEFT, ipady=2)

        # 系统角色 (可选)
        tk.Label(row1, text="   角色:", font=("Microsoft YaHei", 10),
                 bg=self.bg2, fg="#94a3b8").pack(side=tk.LEFT, padx=(15, 0))
        self.role_entry = tk.Entry(row1, font=("Microsoft YaHei", 10),
                                   bg=self.bg, fg=self.fg, insertbackground=self.fg,
                                   relief=tk.FLAT, highlightthickness=1,
                                   highlightbackground=self.accent, width=25)
        self.role_entry.pack(side=tk.LEFT, padx=(5, 0), ipady=4)
        self.role_entry.insert(0, "你是一名专业助手")

        # 问题输入
        tk.Label(p, text="✍️ 输入你的问题:", font=("Microsoft YaHei", 11),
                 bg=self.bg2, fg=self.fg).pack(anchor=tk.W, pady=(8, 3))
        self.question_text = tk.Text(p, height=5, font=("Microsoft YaHei", 11),
                                     bg="#0b1220", fg="#e2e8f0", insertbackground="#e2e8f0",
                                     relief=tk.FLAT, highlightthickness=1,
                                     highlightbackground="#334155", wrap=tk.WORD)
        self.question_text.pack(fill=tk.X, ipady=4)

    def _build_button_panel(self):
        p = tk.Frame(self.root, bg=self.bg)
        p.pack(fill=tk.X, padx=20, pady=6)
        self.send_btn = tk.Button(p, text="🚀 智能问答", command=self._send,
                                  bg=self.green, fg="white",
                                  font=("Microsoft YaHei", 13, "bold"),
                                  relief=tk.FLAT, padx=30, pady=8, cursor="hand2")
        self.send_btn.pack(side=tk.LEFT)
        tk.Button(p, text="🧹 清空", command=self._clear,
                  bg=self.bg2, fg=self.fg, font=("Microsoft YaHei", 11),
                  relief=tk.FLAT, padx=20, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=10)

    def _build_result_panel(self):
        p = tk.Frame(self.root, bg=self.bg2)
        p.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)
        tk.Label(p, text="💬 回答", font=("Microsoft YaHei", 12, "bold"),
                 bg=self.bg2, fg=self.fg).pack(anchor=tk.W, padx=8, pady=(6, 2))
        self.result_text = scrolledtext.ScrolledText(
            p, font=("Microsoft YaHei", 10), bg="#0b1220", fg="#e2e8f0",
            insertbackground="#e2e8f0", relief=tk.FLAT, wrap=tk.WORD,
            highlightthickness=1, highlightbackground="#334155")
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.result_text.configure(state=tk.DISABLED)
        self.result_text.tag_configure("route", foreground="#a78bfa", font=("Microsoft YaHei", 10, "bold"))
        self.result_text.tag_configure("err", foreground="#ef4444")

    def _build_statusbar(self):
        self.status = tk.Label(self.root, text="就绪 - 输入问题点击「智能问答」",
                               font=("Microsoft YaHei", 9), bg=self.bg,
                               fg="#94a3b8", anchor=tk.W)
        self.status.pack(fill=tk.X, padx=20, pady=(0, 8))

    def _send(self):
        q = self.question_text.get("1.0", tk.END).strip()
        if not q:
            messagebox.showwarning("提示", "请输入问题！")
            return
        if not ROUTER_OK:
            messagebox.showerror("初始化失败", f"路由核心加载失败:\n{_import_err}")
            return
        self.send_btn.config(state=tk.DISABLED, text="⏳ 思考中…")
        self.status.config(text="正在路由到最优模型…")
        threading.Thread(target=self._worker, args=(q,), daemon=True).start()

    def _worker(self, q):
        try:
            role = self.role_entry.get().strip() or "你是一名专业助手"
            # 自动路由：任务描述+内容交给路由核心自动分类
            result = route_and_call(q, q, system=role)
            self.root.after(0, lambda: self._show_result(result, q))
        except Exception as e:
            self.root.after(0, lambda: self._show_error(str(e)))

    def _show_result(self, result, q):
        self.result_text.configure(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        # 显示路由信息
        model = result.get("model", "未知") if isinstance(result, dict) else "未知"
        provider = result.get("provider", "") if isinstance(result, dict) else ""
        self.result_text.insert(tk.END, f"🧭 路由: {provider} / {model}\n\n", "route")
        # 显示回答
        content = result.get("content", "") if isinstance(result, dict) else str(result)
        self.result_text.insert(tk.END, content)
        self.result_text.configure(state=tk.DISABLED)
        self.send_btn.config(state=tk.NORMAL, text="🚀 智能问答")
        self.status.config(text=f"✅ 完成 (路由: {provider} / {model})")

    def _show_error(self, msg):
        self.result_text.configure(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, f"❌ 出错: {msg}", "err")
        self.result_text.configure(state=tk.DISABLED)
        self.send_btn.config(state=tk.NORMAL, text="🚀 智能问答")
        self.status.config(text=f"❌ {msg[:60]}")

    def _clear(self):
        self.question_text.delete("1.0", tk.END)
        self.result_text.configure(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.configure(state=tk.DISABLED)
        self.status.config(text="已清空")


def main():
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    RouterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
