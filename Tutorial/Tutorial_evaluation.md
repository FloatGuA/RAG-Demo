# Tutorial_evaluation

## 1. 模块作用（What）

`evaluation.py` 用于批量评估 RAG 问答结果，回答“系统是否真的有用”。

## 2. 设计思路（Why）

- 将“感觉好不好”变成“指标是否提升”
- 评测与在线服务解耦，可离线稳定复现
- 输出 JSON 报告，便于版本对比与持续优化

## 3. 核心实现（How）

- `load_eval_cases(path)`：加载评测集 JSON（根结构必须是 list）
- `evaluate_cases(cases, answer_fn)`：批量执行并汇总指标
- 指标函数：
  - `token_f1(prediction, reference)`
  - `keyword_recall(answer, keywords)`
  - `source_metrics(predicted_sources, expected_sources)`
- CLI 入口：
  - `python evaluation.py --eval-set ... --output ...`
  - 可选阈值：`--min-relevance-score 0.2`（过滤低相关检索结果）

## 4. 支持的样本字段

- `id`：样本 ID（可选）
- `query`：问题（必填）
- `expected_answer`：参考答案（可选）
- `expected_keywords`：关键词列表（可选）
- `expected_sources`：期望来源列表（可选）
- `top_k`：该样本覆盖默认 top-k（可选）

## 5. 输出指标说明

- `answer_exact_match_avg`：答案精确匹配均值
- `answer_token_f1_avg`：答案 token F1 均值
- `keyword_recall_avg`：关键词召回均值
- `source_recall_avg`：来源召回均值
- `source_hit_rate`：来源命中率（至少命中一个来源）

## 6. 推荐评估实践（含 I don't know 对照）

- 使用混合评测集：可回答问题 + 明显越界问题
- 参考样本：`eval/eval_set.20_questions.json`（当前为 30 题混合集）
- 对越界问题设置：`expected_answer = "I don't know"`，`expected_sources = []`
- 评估时尝试 `--min-relevance-score`（如 `0.15 ~ 0.30`）比较前后指标差异
## 7. 模块关系（上下游）

- 上游：`pipeline.query.answer_with_store`（复用核心问答链路，支持低相关过滤）
- 下游：`artifacts/eval/*.json` 报告（用于对比与验收）
## 8. 测试映射

- 对应：`tests/test_evaluation.py`
- 覆盖点：
  - 指标函数正确性
  - 评测集加载与格式校验
  - 批量评估汇总行为

## 9. 技术栈

- `Python 3`：评估逻辑与报告聚合
- `json`：评测集读取与报告落盘
- 项目复用：`pipeline.answer_with_store()` 复用线上问答链路
- 指标计算：EM、Token F1、关键词召回、来源命中

## 10. 端到端流程（这一部分如何工作）

1. 读取评测集 `eval/*.json`  
2. 对每条样本调用 `answer_with_store()` 获取模型输出  
3. 逐条计算指标并保存 case 级结果  
4. 聚合 summary 指标均值  
5. 写入 `artifacts/eval/*.json` 报告

## 11. 核心函数在做什么，为什么这样做

- `load_eval_cases()`：
  - **做什么**：读取并校验评测集格式
  - **为什么**：先保证输入质量，避免评估结果失真
- `evaluate_cases()`：
  - **做什么**：评估主循环（逐样本 + 汇总）
  - **为什么**：统一评估入口，便于后续扩展更多指标
- `token_f1()/keyword_recall()/source_metrics()`：
  - **做什么**：不同维度衡量回答质量与引用质量
  - **为什么**：单一指标不足以评估 RAG，需多维观察
