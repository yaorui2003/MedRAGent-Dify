# Dify 版端到端运行记录（2026-11-05）

本目录保存**在 Dify Cloud 上实际跑通**的工作流输出，作为「平台化重构可运行」的证据。

## 运行信息

| 项 | 值 |
|---|---|
| 应用 | MedRAGent 文献检索与筛选（Workflow） |
| Dify 工作流版本 | DSL 0.7.0，15 个业务节点（含 2 个 Code 清洗节点；另有迭代起始节点，共 16 个图节点） |
| 调用方式 | 已发布 Service API（`POST /v1/workflows/run`，SSE 流式），客户端 `client/run_screening.py` |
| run_id | `b75f3509-0724-40fd-a60e-b91d08f13d7a` |
| 案例 | Ramadan 禁食 × 青少年 1 型糖尿病（doi:10.1186/s12902-025-01835-1） |
| 时间范围 | 2001/05/01 – 2024/02/13 |
| max_results | 44 |
| 结果 | PubMed 命中 3,293；逐篇筛选 44；建议纳入 10；排除 34* |

\* 报告按 exclusion_reasons 归类为 29 条 + 部分空原因按 PICOS 字段归类，具体分布见 `.md`。

产出文件：

- `report_dify_20261105.xlsx`：结构化逐篇结果（PMID / Title / Included / PICOS 各元素理由 / Exclusion Reasons）
- `report_dify_20261105.md`：LLM 生成的 Markdown 筛查报告（已由 `清洗报告` 节点剥离推理标签）

## 与基线的一致性对比

基线：[`docs/baseline/report_baseline_v4.1flash.xlsx`](../baseline/report_baseline_v4.1flash.xlsx)（原自研管线，V4.1-Flash，44 篇 / 纳入 26）。

| 指标 | 基线（自研管线） | Dify 版 |
|---|---|---|
| 检索式口径 | 窄检索式（MeSH 为主，原作者可复现口径） | LLM 生成（P/I 概念组 + 自由词），更宽 |
| PubMed 命中 | 44 | 3,293 |
| 实际筛选 | 44 | 44（`retmax` 前 44，按 relevance） |
| 建议纳入 | 26 | 10（同参数两次运行分别为 15 / 10，LLM 判定存在波动） |
| PMID 交集 | — | **7 篇** |
| 交集内判定一致 | — | **7 / 7 = 100%** |

**结论与边界**：

1. 两版**检索集合不同**（3,293 vs 44），因此纳入总数不可直接比较；差异主要来自 Dify 版检索式更宽（`adolescent[TiAb] OR ...`、`fasting[TiAb] OR Ramadan[TiAb]`），把大量“仅 T1D、未涉及 Ramadan”的文献也纳入初筛。
2. 在 7 篇重合文献上，两版逐篇纳入/排除判定**完全一致**，说明筛选提示词与规则移植是有效的。
3. Dify 版两次同参数运行纳入数 15 / 10，体现 LLM 初筛的非确定性；报告与简历中应表述为“LLM 辅助初筛”，最终需人工复核。
4. 若要与基线做严格 44/44 对比，需要把基线的 PMID 列表作为输入直接复筛（当前工作流以检索式驱动）；这属于后续可扩展项，不影响“平台化重构跑通”的结论。

## 复现

见仓库根目录 `README.md` 与 `dify/SETUP.md`；API Key 与 `client/config.json` 不入库。