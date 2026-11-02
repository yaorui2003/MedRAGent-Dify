# Dify 搭建手册（从零复现 MedRAGent-Dify 工作流）

本手册对应 `medragent-workflow.yml`（Dify DSL），覆盖**账号准备 → 工具服务部署 → 模型配置 → 知识库导入 → 自定义工具注册 → 工作流导入/搭建 → 运行验证 → 发布 API** 全流程。全程无需本地 Docker。

> 搭建完成后，建议在 Dify 画布中导出一份你自己的 DSL 覆盖本仓库的 yml，作为可复现交付物。

---

## 0. 账号与密钥准备

| 资源 | 用途 | 获取方式 |
|---|---|---|
| [Dify Cloud](https://cloud.dify.ai) | 工作流编排平台 | 注册免费 Sandbox 工作区 |
| [DeepSeek API](https://platform.deepseek.com) | 全部 LLM 节点（deepseek-chat） | 注册充值（演示级用量 < ¥10） |
| [SiliconFlow](https://siliconflow.cn) | 嵌入 bge-m3 + 重排 bge-reranker-v2-m3 | 注册送免费额度 |
| [Render](https://render.com) | 托管 PubMed 工具服务（公网 HTTPS） | 用 GitHub 账号登录，免费 Web Service |
| NCBI Entrez API key（可选） | PubMed 限速 3/s → 10/s | https://www.ncbi.nlm.nih.gov/account/ |

---

## 1. 部署 PubMed 工具服务（Render）

1. 把本仓库推到你的 GitHub。
2. Render 控制台 → **New → Blueprint**，选择仓库（自动读取 `tool-service/render.yaml`）；或手动 **New → Web Service**，Root Directory 填 `tool-service`。
3. 环境变量（可选）：`ENTREZ_EMAIL`、`ENTREZ_API_KEY`。
4. 部署完成后验证：

```bash
curl https://<your-service>.onrender.com/health
curl "https://<your-service>.onrender.com/pubmed/search?query=%22Diabetes%20Mellitus%2C%20Type%201%22%5BMeSH%20Terms%5D&max_results=2"
```

> 免费实例冷启动需 30~60 秒，首次调用慢是正常的。Dify Cloud 只能访问公网端点，所以这一步必须做（本机 localhost 跑通仅用于开发调试）。

## 2. Dify 配置模型

1. 右上角 **插件（Plugins）→ Marketplace**：
   - 安装 **DeepSeek** 官方插件 → 设置中填入 DeepSeek API Key；
   - 安装 **SiliconFlow** 插件 → 设置中填入 SiliconFlow API Key。
2. 确认模型可用：DeepSeek `deepseek-chat`（Chat）；SiliconFlow `Pro/BAAI/bge-m3`（Embedding）、`Pro/BAAI/bge-reranker-v2-m3`（Rerank）。

## 3. 构建知识库

**生成语料**（本机，一次性）：

```bash
cd data-prep
python mesh_to_kb.py --download            # 下载 desc2025.xml（约 300 MB）
python mesh_to_kb.py --xml desc2025.xml --out mesh_demo.txt --trees C E F G --max-records 30000
```

`--trees` 按研究领域裁剪树形分支（C=疾病 E=诊疗技术 F=精神障碍 G=生物科学），控制知识库规模与检索精度。演示案例（糖尿病主题）至少保留 `C`。

**导入 Dify**：知识库 → 创建 → 导入文本 → 上传 `mesh_demo.txt`：

| 配置项 | 推荐值 |
|---|---|
| 分段标识符（自定义分隔符） | `###` |
| 分段最大长度 | 1000 |
| 索引方式 | 高质量 |
| Embedding 模型 | `Pro/BAAI/bge-m3`（SiliconFlow） |
| 检索设置 | 混合检索（Hybrid）+ Rerank：`Pro/BAAI/bge-reranker-v2-m3`，Top K = 8 |

导入后在「召回测试」中输入 `type 1 diabetes adolescent fasting`，应命中 `Diabetes Mellitus, Type 1` 等条目。

> 这一步替代了原项目本地构建的 `mesh_index.faiss` + `supple_index.faiss`（bge-m3 + FAISS）：向量库与检索管线由平台托管，MeSH 词条即文档。

## 4. 注册自定义工具

工具（Tools）→ **自定义 → 创建自定义工具**：

- 名称：`medragent_tools`
- OpenAPI Schema：粘贴 `tool-service/openapi.json`（其中的 `servers.url` 改成你的 Render 地址）
- 无鉴权（服务端仅做 PubMed 代理）

保存后应出现两个工具：`pubmed_search`、`mesh_expand`，点「测试」验证调用成功。

## 5. 搭建工作流

### 方式 A：导入 DSL（推荐）

工作室 → 创建应用 → **导入 DSL 文件** → 选择 `dify/medragent-workflow.yml`。

导入后按提示修复三类引用（Dify 的 DSL 不携带密钥与团队资源，属正常机制）：

1. **模型未配置**：每个 LLM 节点把模型重选为你的 `deepseek-chat`；
2. **工具未授权**：PubMed 检索节点重新绑定你刚创建的 `medragent_tools`；
3. **知识库缺失**：MeSH 知识检索节点重新选择你刚建的知识库。

### 方式 B：手动搭建（备选/学习路径）

按 DSL 中的节点顺序在画布中搭建（开始 → 知识检索 → LLM×3 → 工具 → 代码×2 → 迭代 → 结束），**全部提示词**见 [prompts.md](prompts.md)，节点参数如下：

| 节点 | 类型 | 关键配置 |
|---|---|---|
| 开始 | Start | 输入字段：picos（段落）、exclusion（段落）、date_start、date_end、max_results（数字） |
| MeSH 知识检索 | Knowledge Retrieval | 查询变量 picos；Top K=8；混合检索+重排 |
| PICOS 解析与 MeSH 映射 | LLM | deepseek-chat，温度 0.1；上下文=知识检索结果，提示词含 `{{#context#}}` |
| Boolean 检索式组装 | LLM | deepseek-chat，温度 0.1；输入=`{{#llm-mesh.text#}}` |
| PubMed 检索 | 自定义工具 | query=`{{#llm-query.text#}}`，max_results=`{{#start.max_results#}}` |
| 解析文献列表 | Code | 输入=`tool-pubmed/text`，输出 `articles: array[object]`、`total: number` |
| 逐篇筛选（迭代） | Iteration | 输入对象=`code-parse/articles`；输出=`llm-screen/text` |
| 单篇纳入/排除判定 | LLM（迭代内） | deepseek-chat，温度 0.1；文献=`{{#iter-screen.item#}}` |
| 汇总筛选结果 | Code | 输入=`iter-screen/output` 与 `code-parse/total` |
| 生成筛查报告 | LLM | deepseek-chat，温度 0.3；引用汇总统计与 rows |
| 结束 | End | 输出 report / rows / included / analyzed / total |

## 6. 运行验证（演示案例）

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
→ 工具返回文献 → 迭代逐篇输出判定 JSON → 报告节点生成 Markdown。

## 7. 发布并开放 API

1. 右上角**发布**（更新）。
2. 左侧**访问 API** → 创建 API 密钥，记下：
   - API Base：`https://api.dify.ai/v1`
   - 端点：`POST /workflows/run`（workflow 应用）
3. 配置 `client/config` 后运行 `client/run_screening.py`，结果导出 `report_*.xlsx`。

## 8. 常见问题

| 现象 | 处理 |
|---|---|
| 工具节点报 502 | Render 免费实例冷启动或 NCBI 限速；重试，或配置 Entrez key（10 req/s） |
| 知识检索无召回 | 确认 embedding 模型已配、知识库已完成索引；召回测试验证 |
| LLM 输出 JSON 解析失败 | code-collect 已内置括号截断兜底；必要时把温度降到 0 |
| 迭代报超时 | 调小 max_results；免费版迭代节点有并发/时长限制 |
| DSL 导入失败 | 用方式 B 手动搭建（prompts.md 齐全），成功后导出你自己的 DSL |
