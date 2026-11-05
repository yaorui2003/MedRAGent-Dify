# Dify 搭建手册（从零复现 MedRAGent-Dify 工作流）

本手册对应 `medragent-workflow.yml`（Dify DSL），覆盖**账号准备 → 模型配置 → 知识库导入 → 工作流导入/搭建 → 运行验证 → 发布 API** 全流程。全程无需本地 Docker、无需部署任何服务。

> 工作流通过 **HTTP 请求节点直连 NCBI E-utilities 公网 API**（检索用 JSON 端点、文献详情用 MEDLINE 纯文本端点，全部字符串/JSON 解析）。`tool-service/`（FastAPI 封装）保留在仓库中作为可选升级：部署到公网后可注册为 Dify 自定义工具，见文末「可选升级」。
>
> 搭建完成后，建议在 Dify 画布中导出一份你自己的 DSL 覆盖本仓库的 yml，作为可复现交付物。

---

## 0. 账号与密钥准备

| 资源 | 用途 | 获取方式 |
|---|---|---|
| [Dify Cloud](https://cloud.dify.ai) | 工作流编排平台 | 注册免费 Sandbox 工作区 |
| [DeepSeek API](https://platform.deepseek.com) | 全部 LLM 节点（deepseek-flash，即 V4.1-Flash） | 注册充值（演示级用量 < ¥10） |
| [SiliconFlow](https://siliconflow.cn) | 嵌入 `BAAI/bge-large-en-v1.5` + 重排 `Pro/BAAI/bge-reranker-v2-m3` | 注册送免费额度 |

## 1. Dify 配置模型

1. 右上角 **插件（Plugins）→ Marketplace**：
   - 安装 **DeepSeek** 官方插件 → 设置中填入 DeepSeek API Key；
   - 安装 **SiliconFlow** 插件 → 设置中填入 SiliconFlow API Key。
2. 确认模型可用：DeepSeek `deepseek-flash`（Chat，即 DeepSeek-V4.1-Flash；如插件模型列表里没有它，先把 DeepSeek 插件升级到最新版本）；SiliconFlow `BAAI/bge-large-en-v1.5`（Embedding）、`Pro/BAAI/bge-reranker-v2-m3`（Rerank）。

> **嵌入模型为什么不用 bge-m3**：`Pro/BAAI/bge-m3` 是多向量模型（dense + sparse + ColBERT），Dify 会为同一分段写入多份向量，Sandbox 套餐的 50 MB 向量存储配额很快被击穿（实测约 3,000 分段即估算到 150 MB+）。改用纯稠密输出的 `BAAI/bge-large-en-v1.5` 后向量量约为原来的 1/3，再配合 Dify 平台级「混合检索（向量+全文）+ 重排」补回关键词召回，这是本项目在配额约束下的实际取舍。

## 2. 构建知识库

**生成语料**（本机，一次性）：

```bash
cd data-prep
python mesh_to_kb.py --download            # 下载 desc2026.xml（约 300 MB）
python mesh_to_kb.py --xml desc2026.xml --out mesh_demo.txt --trees C18 C19 C20 C23 E01 F01
```

`--trees` 按树形分支裁剪：`C18`（内分泌/代谢/营养）、`C19`（糖尿病等内分泌疾病）、`C20`（免疫）、`C23`（症状/病理状态）、`E01`（诊断技术）、`F01`（行为/心理）。这一组合产出 **2,977 条 MeSH 词条**，分段后约 3,700 个 chunk；演示案例（青少年 T1D × Ramadan 禁食）所需词条全部在范围内，同时把向量量压进 Sandbox 50 MB 配额。若换研究主题，按对应分支调整前缀即可。

**导入 Dify**：知识库 → 创建 → 导入文本 → 上传 `mesh_demo.txt`：

| 配置项 | 推荐值 |
|---|---|
| 分段标识符（自定义分隔符） | `###` |
| 分段最大长度 | 1000 |
| 索引方式 | 高质量 |
| Embedding 模型 | `BAAI/bge-large-en-v1.5`（SiliconFlow，纯稠密，1024 维） |
| 检索设置 | 混合检索（Hybrid，向量 0.7 / 关键词 0.3）+ Rerank：`Pro/BAAI/bge-reranker-v2-m3`，Top K = 8 |

导入后在「召回测试」中输入 `type 1 diabetes adolescent fasting`，应命中 `Diabetes Mellitus, Type 1` 等条目。

> 这一步替代了原项目本地构建的 `mesh_index.faiss` + `supple_index.faiss`（bge-m3 + FAISS）：向量库与检索管线由平台托管，MeSH 词条即文档。

## 3. 搭建工作流

### 方式 A：导入 DSL（推荐）

工作室 → 创建应用 → **导入 DSL 文件** → 选择 `dify/medragent-workflow.yml`。

导入后按提示修复引用（Dify 的 DSL 不携带密钥与团队资源，属正常机制）：

1. **模型未配置**：4 个 LLM 节点把模型重选为你的 `deepseek-flash`；
2. **知识库缺失**：MeSH 知识检索节点重新选择你刚建的知识库；
3. **迭代输入对象**：打开「逐篇筛选（迭代）」节点，输入对象选择 `解析文献列表 / articles`。

HTTP 请求节点（PubMed esearch/efetch）无需任何配置——NCBI E-utilities 是公开 API，无需鉴权。

工作流共 **14 个节点**：开始 → MeSH 知识检索 → LLM① PICOS 解析与 MeSH 映射 → LLM② Boolean 检索式组装 → **Code 清洗检索式** → **HTTP esearch** → **Code 解析检索结果** → **HTTP efetch** → **Code 解析文献列表** → 迭代（LLM③ 单篇纳入/排除判定，4 路并行）→ Code 汇总 → LLM④ 生成筛查报告 → **Code 清洗报告** → 结束。

> **手写 DSL 的两个硬约束**：① 节点 id 只能包含字母、数字、下划线（不要用连字符 `-`）——Dify 的变量模板正则不认连字符，`{{#code-esearch.total#}}` 这类引用会原样留给 LLM，导致 HTTP 节点发出空检索式；② 迭代节点的起始节点 id 必须是 `<迭代节点id>start0`、类型 `custom-iteration-start`，否则后端会再补一个起始节点、画布直接崩溃。

### 方式 B：手动搭建（备选/学习路径）

按 DSL 中的节点顺序在画布中搭建，**全部提示词**见 [prompts.md](prompts.md)，节点参数如下：

| 节点 | 类型 | 关键配置 |
|---|---|---|
| 开始 | Start | 输入字段：picos（段落）、exclusion（段落）、date_start、date_end、max_results（数字） |
| MeSH 知识检索 | Knowledge Retrieval | 查询变量 picos；Top K=8；混合检索+重排 |
| PICOS 解析与 MeSH 映射 | LLM | deepseek-flash，温度 0.1；上下文=知识检索结果，提示词含 `{{#context#}}` |
| Boolean 检索式组装 | LLM | deepseek-flash，温度 0.1；输入=`{{#llmmesh.text#}}` |
| 清洗检索式 | Code | 输入=`{{#llmquery.text#}}`；剥离 `<think>` 推理标签/代码围栏，输出 query(string) |
| PubMed esearch | HTTP 请求 | GET `esearch.fcgi`，参数：db=pubmed、term=`{{#codequery.query#}}`、retmode=json、retmax=`{{#start.max_results#}}`、sort=relevance（参数值**不要加引号**） |
| 解析检索结果 | Code | 输入=esearch/body、start/max_results；输出 total(number)、ids(string) |
| PubMed efetch | HTTP 请求 | GET `efetch.fcgi`，参数：db=pubmed、id=`{{#codeesearch.ids#}}`、rettype=medline、retmode=text |
| 解析文献列表 | Code | 输入=efetch/body；输出 articles(array[object])、total(number) |
| 逐篇筛选（迭代） | Iteration | 并行模式 4 路、单篇失败继续；输入对象=`codemedline/articles`；输出=`llmscreen/text` |
| 单篇纳入/排除判定 | LLM（迭代内） | deepseek-flash，温度 0.1；文献=`{{#iterscreen.item#}}` |
| 汇总筛选结果 | Code | 输入=`iterscreen/output` 与 `codeesearch/total`；解析前同样剥离推理标签 |
| 生成筛查报告 | LLM | deepseek-flash，温度 0.3；引用 PICOS/排除标准/汇总统计/rows |
| 清洗报告 | Code | 输入=`{{#llmreport.text#}}`；剥离推理标签，输出 text(string) |
| 结束 | End | 输出 report / rows / included / analyzed / total |

> 为什么 efetch 用 MEDLINE 纯文本而不是 XML：Dify 代码沙箱对第三方包有白名单限制，MEDLINE 标签文本用纯字符串状态机解析（4 字符标签 + 缩进续行），零依赖、最稳。

## 4. 运行验证（演示案例）

来自原项目 README 的真实研究案例（doi:10.1186/s12902-025-01835-1，Ramadan 禁食与青少年 1 型糖尿病）：

- **PICOS**：
  - P：Type 1 Diabetes Mellitus, adolescent
  - I：fasting during Ramadan
  - C：（空）
  - O：hyperglycemia, hypoglycemia, diabetic ketoacidosis, changes in HbA1c, and weight changes
  - S：observational studies (e.g., prospective study, cohort studies, case-control studies, cross-sectional studies)
- **排除标准**（每行一条）：
  - Animal studies
  - Case reports
  - Systematic reviews
  - meta analysis
- **date_start**：`2001/05/01`，**date_end**：`2024/02/13`
- **max_results**：`20`（Sandbox 免费额度内；迭代次数 = 筛选篇数）

预期：LLM1 输出名词与 MeSH 映射 JSON → LLM2 输出形如
`("Diabetes Mellitus, Type 1"[MeSH Terms] OR "T1DM"[Title/Abstract] ...) AND ("Fasting"[MeSH Terms] ...) AND ("2001/05/01"[Date - Publication] : "2024/02/13"[Date - Publication])`
→ esearch 返回 PMID 列表 → efetch 返回文献 → 迭代逐篇输出判定 JSON → 报告节点生成 Markdown。

参考基线：同案例的原版管线（本地复现，V4.1-Flash）筛选 44 篇、纳入 26 篇，见 [docs/baseline](../docs/baseline/)。

Dify 版实跑（2026-11-05，`max_results=44`，Service API 调用）：PubMed 命中 3,293 → 逐篇筛选 44 → 建议纳入 10（同参数两次运行分别为 15 / 10，LLM 判定有波动）。与原基线 PMID 重合 7 篇，重合文献判定 **7/7 一致**；两版检索式口径不同（Dify 更宽），纳入总数不可直接比较。完整记录与边界说明见 [docs/dify-run](../docs/dify-run/)。

## 5. 发布并开放 API

1. 右上角**发布**（更新）。
2. 左侧**访问 API** → 创建 API 密钥，记下：
   - API Base：`https://api.dify.ai/v1`
   - 端点：`POST /workflows/run`（workflow 应用）
3. 复制 `client/config.example.json` 为 `client/config.json`，填入 api_key 后运行：

```bash
pip install requests openpyxl
python client/run_screening.py --config config.json
```

结果导出 `report_dify_*.xlsx` + `.md`。

## 6. 常见问题

| 现象 | 处理 |
|---|---|
| esearch/efetch 偶发 429/超时 | NCBI 限速 3 req/s：HTTP 节点已配 3 次重试；仍频繁则申请 Entrez key 并在 HTTP 节点加 `api_key` 参数 |
| 知识检索无召回 | 确认 embedding 模型已配、知识库已完成索引；用召回测试验证 |
| LLM 输出 JSON 解析失败 | code-collect 已内置括号截断兜底；必要时把温度降到 0 |
| 迭代报超时 | 调小 max_results；免费版迭代节点有并发/时长限制 |
| DSL 导入失败 | 用方式 B 手动搭建（prompts.md 齐全），成功后导出你自己的 DSL |
| 知识库文档「索引失败」，错误仅显示 `[SiliconFlow] Error:` | 先确认 SiliconFlow 余额/额度，再用 curl 直接验证 `/v1/embeddings`；确认模型名与知识库设置一致后点「重试」。3,700 个分段逐个送嵌入需要数分钟，状态 `indexing` 期间不要重复点重试 |
| 工作流能跑但检索式里没有 MeSH 词 | 知识库索引未完成（分段全部「已禁用」）→ 等索引完成或重试；另外确认知识检索节点重新绑定了知识库 |
| 迭代节点画布报「渲染此组件时发生了意外错误」 | 迭代节点必须有规范起始节点：id = `<迭代节点id>start0`、节点 `type: custom-iteration-start`、迭代节点 `data.start_node_id` 指向它，且连线从起始节点出发（见 DSL 示例） |

## 7. 可选升级：自定义 API 工具（恢复原架构）

`tool-service/`（FastAPI 封装 E-utilities：esearch/efetch + MeSH 同义词扩展，带限速/重试/指数退避）可部署到任意公网托管（Render Blueprint 已配好 / HF Spaces Docker 文件已备好，均免费），然后在 Dify「工具 → 自定义 → 创建自定义工具」粘贴 `tool-service/openapi.json` 注册，把两个 HTTP 节点替换为一个工具节点——这也是原版 MedRAGent-Dify 的架构。部署细节见 `tool-service/render.yaml`、`tool-service/hf-space/README.md`。
