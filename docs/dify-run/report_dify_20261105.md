# 文献检索与筛选报告

## 1. 研究问题与纳入标准（PICOS）

| 要素 | 纳入标准 |
|---|---|
| P | Type 1 Diabetes Mellitus，青少年（adolescent） |
| I | Ramadan 期间禁食（fasting during Ramadan） |
| C | 未指定 |
| O | 高血糖、低血糖、糖尿病酮症酸中毒（DKA）、HbA1c 变化、体重变化 |
| S | 观察性研究，如前瞻性研究、队列研究、病例对照研究、横断面研究 |

## 2. 排除标准

- Animal studies（动物研究）
- Case reports（病例报告）
- Systematic reviews（系统综述）
- Meta analysis（Meta 分析）

## 3. 检索策略（PubMed Boolean 检索式、时间范围）

检索数据库：PubMed  
时间范围：2001/05/01 至 2024/02/13

```text
("Type 1 Diabetes Mellitus"[Title/Abstract] OR Diabetes Mellitus, Type 1[MeSH Terms] OR Type 1 Diabetes[MeSH Terms] OR Diabetes, Type 1[MeSH Terms] OR Diabetes Mellitus, Insulin-Dependent[MeSH Terms] OR adolescent[Title/Abstract]) AND (fasting[Title/Abstract] OR Ramadan[Title/Abstract]) AND ("2001/05/01"[Date - Publication] : "2024/02/13"[Date - Publication])
```

## 4. 筛选结果统计

| 项目 | 数量 | 说明 |
|---|---:|---|
| PubMed 命中总数 | 3293 | 检索式命中总量 |
| 实际逐条筛选篇数 | 44 | 当前提供的逐行筛选 JSON 记录数 |
| 建议纳入数 | 10 | LLM 建议纳入，需人工复核 |
| 建议排除数 | 34 | 44 − 10 |
| 纳入率（建议纳入/实际筛选） | 22.7% | 10/44 |
| 筛选覆盖率（实际筛选/命中总数） | 1.34% | 44/3293 |

> 注：本报告仅基于提供的 44 条逐条筛选记录汇总；未对剩余 3249 条 PubMed 命中记录逐条展示，正式综述需核查完整筛选流程。

## 5. 排除原因分布

按筛选记录中的 `exclusion_reasons` 字段归类，并结合 `included=NO` 但该字段为空的记录统计如下。

| 排除原因分类 | 数量 | 占排除数（34）比例 |
|---|---:|---:|
| no abstract（无摘要） | 12 | 35.3% |
| Animal studies（动物研究） | 2 | 5.9% |
| Case reports（病例报告） | 1 | 2.9% |
| Study design not observational（明示非观察性研究设计） | 1 | 2.9% |
| 未填写 exclusion_reasons / 其他 PICOS 不符 | 18 | 52.9% |
| **合计** | **34** | **100%** |

> 说明：未出现以“系统综述”或“Meta 分析”作为明示排除原因的记录。部分 `included=NO` 记录的 `exclusion_reasons` 为空，但其 population、intervention、outcome 或 study_design 字段显示不符合 PICOS，因此归入“未填写/其他 PICOS 不符”。

## 6. 建议纳入文献清单

| 序号 | PMID | 标题 |
|---:|---|---|
| 1 | 37244952 | Circulating miRNA expression in long-standing type 1 diabetes mellitus. |
| 2 | 20353144 | Diabetes mellitus: diagnosis and screening. |
| 3 | 36398450 | Fasting and meal-stimulated serum C-peptide in long-standing type 1 diabetes mellitus. |
| 4 | 30203124 | Impaired glucagon secretion in patients with fulminant type 1 diabetes mellitus. |
| 5 | 31050819 | Fulminant type 1 diabetes: The clinical and continuous glucose monitoring characteristics in Chinese patients. |
| 6 | 39529980 | Metabolic impact of residual C-peptide secretion in type 1 diabetes mellitus. |
| 7 | 20939000 | Diabetes and fasting during Ramadan. |
| 8 | 33321160 | Ramadan fasting in people with type 1 diabetes during COVID-19 pandemic: The DaR Global survey. |
| 9 | 32775471 | Altered Regulatory B Cell Subsets in Children with Type 1 Diabetes Mellitus. |
| 10 | 28258376 | Olfactory and gustatory functions in patients with non-complicated type 1 diabetes mellitus. |

## 7. 方法学说明

- 本报告采用 LLM 辅助筛选：基于标题和摘要逐条对照 PICOS 与排除标准，生成 `included` 判定及理由。
- 建议纳入清单为 LLM 辅助筛选结果，**不是最终定稿**；正式系统综述仍需人工复核摘要/全文，重点核验 P（青少年 1 型糖尿病）、I（Ramadan 期间禁食）和 S（观察性研究设计）。
- 部分记录在标题/摘要未明确提及时，按“未明确否定即视为满足”的规则处理，可能导致建议纳入偏宽；尤其需人工复核 Ramadan 暴露和青少年人群是否真实符合。
- `no abstract` 记录共 12 篇，本轮标记为排除。正式综述建议进一步检索全文、出版商页面或联系作者；若仍无法获取摘要/全文，应按预先设定的无摘要处理规则记录。
- 当前仅汇总 44 条逐条筛选记录，相对于 PubMed 3293 条命中总量，需补充核对检索、去重、初筛与全文筛选流程的完整性。