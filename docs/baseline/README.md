# 基线运行记录（原版 MedRAGent 管线复现）

本目录保存两份同一演示案例（Ramadan 禁食 × 青少年 1 型糖尿病，doi:10.1186/s12902-025-01835-1）的原版管线筛选报告，用于：

1. **验证 Dify 版重构的有效性**（Dify 版 vs 本基线的逐篇判定一致率）
2. **量化模型换代的影响**（V3 → V4.1-Flash 的判定一致性）

| 文件 | 说明 |
|---|---|
| `report_repo_original_deepseek_v3.xlsx` | 原作者以 DeepSeek-V3（deepseek-chat）运行的结果（随原仓库发布） |
| `report_baseline_v4.1flash.xlsx` | 本地复现：原版管线 + DeepSeek-V4.1-Flash（deepseek-flash），2026-11-04 运行 |

## 复现结果

| 指标 | 数值 |
|---|---|
| 检索命中（同日期范围 2001/05/01–2024/02/13） | 44 篇，**与原作者报告 PMID 集合 100% 重合**（44/44），检索管线完全可复现 |
| 筛选判定一致率（V3 vs V4.1-Flash，仅实际分析的有摘要文献） | **33/37 = 89.2%** |
| 筛选判定一致率（计入双方均跳过的无摘要文献） | 40/44 = 90.9% |
| 纳入数 | V3：22 篇 → V4.1-Flash：26 篇 |
| 判定差异方向 | 4 篇全部为 V3 排除 → V4.1-Flash 纳入（边界案例上 Flash 档更宽松，如 "Management of diabetes during Ramadan fasting in children and adolescents" 这类相关性明显的综述型观察研究） |

## 本地复现的环境与修改（相对原仓库）

- Python 3.12 venv；依赖：faiss-cpu、langchain 0.3.x（原代码基于 0.x API）、langchain-openai、biopython、pandas、json-repair
- 模型：`deepseek-chat` → **`deepseek-flash`**（原 README 明示允许按所用 LLM 修改）
- **传输层加固**（原仓库未修改的本地补丁）：Biopython 的 E-utilities 传输在该网络路径下对长查询间歇性返回 HTTP 400（esearch POST、efetch 均复现），`pubmed_tools.py` 的 `fetch_pmids` / `fetch_articles` 改为 requests 直连 GET（esearch 用 JSON 端点、efetch 用 XML 端点 + ElementTree 构造与 `Entrez.read` 等价的字典结构），修复后全链路稳定
- MeSH 索引：按原 README 从 HuggingFace（nyczy34/MedRAGent）下载 mesh_index.faiss + supple_index.faiss 及元数据

## 后续

Dify 版跑通后，将 `client/run_screening.py` 输出的报告与本目录 `report_baseline_v4.1flash.xlsx` 做逐篇对比，得到「Dify 重构版 vs 自研管线」的一致率，回填 README 与简历。
