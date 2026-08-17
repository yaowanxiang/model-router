# -*- coding: utf-8 -*-
"""单元测试: router_core 分类逻辑与候选链解析"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import router_core


class TestClassifyTask(unittest.TestCase):
    def test_vision_keyword(self):
        self.assertEqual(router_core.classify_task("看这张图片"), "vision")
        self.assertEqual(router_core.classify_task("识别截图里的文字"), "vision")
        self.assertEqual(router_core.classify_task("OCR 这个文档"), "vision")

    def test_vision_image_flag(self):
        self.assertEqual(router_core.classify_task("随便", has_image=True), "vision")

    def test_long_by_length(self):
        self.assertEqual(router_core.classify_task("总结", content_len=3000), "long")

    def test_long_keyword(self):
        self.assertEqual(router_core.classify_task("做一篇文献综述"), "long")
        self.assertEqual(router_core.classify_task("翻译论文全文"), "long")

    def test_complex_by_length(self):
        self.assertEqual(router_core.classify_task("帮我看看", content_len=800), "complex")

    def test_complex_keyword(self):
        self.assertEqual(router_core.classify_task("分析这份气象数据"), "complex")
        self.assertEqual(router_core.classify_task("写一段代码实现排序"), "complex")
        self.assertEqual(router_core.classify_task("推导这个公式"), "complex")

    def test_complex_code_fence(self):
        self.assertEqual(router_core.classify_task("看看这段 ```\ncode\n```"), "complex")

    def test_medium_keyword(self):
        self.assertEqual(router_core.classify_task("翻译这段话"), "medium")
        self.assertEqual(router_core.classify_task("帮我润色一下"), "medium")
        self.assertEqual(router_core.classify_task("写个摘要"), "medium")

    def test_simple(self):
        self.assertEqual(router_core.classify_task("你好"), "simple")
        self.assertEqual(router_core.classify_task("在吗"), "simple")
        self.assertEqual(router_core.classify_task("谢谢"), "simple")


class TestGetCandidates(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "providers": {
                "free_a": {"name": "Free A", "tier": "free"},
                "free_b": {"name": "Free B", "tier": "free", "enabled": False},
                "paid_a": {"name": "Paid A", "tier": "paid"},
            }
        }

    def test_chain_respects_order_and_disabled(self):
        route = {"candidates": [
            {"provider": "free_a", "model": "m1"},
            {"provider": "free_b", "model": "m2"},  # disabled -> skipped
            {"provider": "paid_a", "model": "m3"},
        ]}
        chain = router_core._get_candidates(route, self.cfg)
        self.assertEqual([c[0] for c in chain], ["free_a", "paid_a"])

    def test_legacy_single_format(self):
        route = {"provider": "free_a", "model": "m1"}
        chain = router_core._get_candidates(route, self.cfg)
        self.assertEqual([(c[0], c[2]) for c in chain], [("free_a", "m1")])

    def test_no_candidates_raises(self):
        route = {"candidates": [{"provider": "free_b", "model": "x"}]}
        with self.assertRaises(RuntimeError):
            router_core._get_candidates(route, self.cfg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
