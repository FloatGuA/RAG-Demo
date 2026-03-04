"""
evaluation.py 单元测试
"""

import json

import pytest

from evaluation import evaluate_cases, keyword_recall, load_eval_cases, source_metrics, token_f1


class TestEvaluation:
    def test_token_f1_basic(self):
        print("\n[TEST START] token_f1 basic | token_f1 基础行为")
        score = token_f1("hello world", "hello")
        print("[EXPECTED] score in (0, 1] | 分数在 (0,1] 区间")
        assert 0 < score <= 1
        print("[PASS] token_f1 basic ok | token_f1 基础正确\n")

    def test_keyword_recall(self):
        print("\n[TEST START] keyword_recall works | 关键词召回率可用")
        score = keyword_recall("RAG uses retrieval and generation", ["retrieval", "generation", "vector"])
        print("[EXPECTED] 2/3 hit | 命中 2/3")
        assert score == pytest.approx(2 / 3)
        print("[PASS] keyword_recall ok | 关键词召回率正确\n")

    def test_source_metrics(self):
        print("\n[TEST START] source metrics | 来源指标")
        pred = [{"source": "a.pdf", "page": 1}, {"source": "b.pdf", "page": 2}]
        exp = [{"source": "a.pdf", "page": 1}, {"source": "c.pdf", "page": 3}]
        recall, hit = source_metrics(pred, exp)
        print("[EXPECTED] recall=0.5 and hit=True | recall=0.5 且 hit=True")
        assert recall == pytest.approx(0.5)
        assert hit is True
        print("[PASS] source metrics ok | 来源指标正确\n")

    def test_load_eval_cases_valid_and_invalid(self, tmp_path):
        print("\n[TEST START] load eval cases | 加载评测集")
        file_ok = tmp_path / "eval.json"
        file_ok.write_text(json.dumps([{"query": "q1"}]), encoding="utf-8")
        cases = load_eval_cases(str(file_ok))
        assert isinstance(cases, list) and len(cases) == 1

        file_bad = tmp_path / "bad.json"
        file_bad.write_text(json.dumps({"query": "q1"}), encoding="utf-8")
        print("[EXPECTED] non-list root raises ValueError | 根对象非 list 抛错")
        with pytest.raises(ValueError, match="list"):
            load_eval_cases(str(file_bad))
        print("[PASS] load eval cases validation ok | 加载校验正确\n")

    def test_evaluate_cases_summary(self):
        print("\n[TEST START] evaluate cases summary | 汇总指标")
        cases = [
            {
                "id": "c1",
                "query": "q1",
                "expected_answer": "hello world",
                "expected_keywords": ["hello", "world"],
                "expected_sources": [{"source": "s.pdf", "page": 1}],
            },
            {
                "id": "c2",
                "query": "q2",
                "expected_keywords": ["rag"],
            },
        ]

        def fake_answer_fn(case):
            if case["id"] == "c1":
                return {
                    "answer": "hello world",
                    "sources": [{"source": "s.pdf", "page": 1}],
                }
            return {"answer": "RAG demo", "sources": []}

        report = evaluate_cases(cases, fake_answer_fn)
        summary = report["summary"]
        print("[EXPECTED] all summary keys exist | 汇总字段完整")
        assert summary["total_cases"] == 2
        assert summary["answer_exact_match_avg"] == pytest.approx(1.0)
        assert summary["source_hit_rate"] == pytest.approx(1.0)
        assert summary["keyword_recall_avg"] == pytest.approx(1.0)
        assert len(report["cases"]) == 2
        print("[PASS] evaluate cases summary ok | 汇总正确\n")
