"""Generate docs/architecture.png for MedRAGent-Dify (one-off script)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

fig, ax = plt.subplots(figsize=(15.5, 8.2), dpi=150)
ax.set_xlim(0, 100)
ax.set_ylim(0, 56)
ax.axis("off")

C_NODE = "#DBEAFE"; C_NODE_E = "#2563EB"
C_LLM = "#EDE9FE"; C_LLM_E = "#7C3AED"
C_KB = "#FFEDD5"; C_KB_E = "#EA580C"
C_TOOL = "#DCFCE7"; C_TOOL_E = "#16A34A"
C_EXT = "#F1F5F9"; C_EXT_E = "#64748B"
C_CLIENT = "#FEE2E2"; C_CLIENT_E = "#DC2626"


def box(x, y, w, h, text, fc, ec, fs=9.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.35",
                                fc=fc, ec=ec, lw=1.4, zorder=3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, zorder=4)


def arrow(x1, y1, x2, y2, color="#334155", dashed=False):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=13, lw=1.3, color=color,
                                 linestyle="--" if dashed else "-",
                                 shrinkA=1, shrinkB=1, zorder=2))


def conn(points, color="#334155", label=None, label_at=None):
    """Polyline connection with an arrowhead on the last segment."""
    xs, ys = zip(*points)
    ax.plot(xs[:-1] + (xs[-1],), ys[:-1] + (ys[-1],), color=color, lw=1.3, zorder=2)
    arrow(points[-2][0], points[-2][1], points[-1][0], points[-1][1], color=color)
    if label and label_at:
        ax.text(label_at[0], label_at[1], label, fontsize=8, color=color, zorder=4)


# ---- containers ----
ax.add_patch(FancyBboxPatch((14, 18.5), 71, 27.5, boxstyle="round,pad=0.5",
                            fc="#F8FAFC", ec="#94A3B8", lw=1.6, zorder=1))
ax.text(16.5, 44.6, "Dify Cloud - Workflow 应用「MedRAGent 文献检索与筛选」", fontsize=11,
        fontweight="bold", color="#334155")

ax.add_patch(FancyBboxPatch((69.5, 4.5), 24, 9.5, boxstyle="round,pad=0.4",
                            fc="#F0FDF4", ec="#16A34A", lw=1.4, linestyle="--", zorder=1))
ax.text(70.3, 5.2, "Render 免费托管（公网 HTTPS）", fontsize=8.5, color="#15803D", ha="left")

# ---- workflow nodes: row1 left-to-right, row2 snake (right-to-left) ----
y1, y2 = 33.5, 22.5
H = 6.5

box(16.5, y1, 12.2, H, "开始\nPICOS / 排除标准\n时间范围 / max_results", C_NODE, C_NODE_E, 8.2)
box(31.0, y1, 12.2, H, "MeSH 知识检索\nTopK=8 混合检索\n+ bge-reranker 重排", C_KB, C_KB_E, 8.2)
box(45.5, y1, 12.2, H, "LLM① PICOS 解析\n名词抽取\nMeSH 主题词映射", C_LLM, C_LLM_E, 8.2)
box(60.0, y1, 12.2, H, "LLM② Boolean 检索式\n组内OR 组间AND\n[MeSH]/[TiAb] 后缀", C_LLM, C_LLM_E, 8.2)
box(74.5, y1, 8.9, H, "PubMed\n检索工具\n(自定义API)", C_TOOL, C_TOOL_E, 8.2)

box(72.5, y2, 12.2, H, "Code 解析\n文献列表\narray[object]", C_NODE, C_NODE_E, 8.2)
box(51.5, y2 - 0.3, 17.5, 7.1, "迭代节点 逐篇筛选\nLLM③ 纳入/排除判定\nPICOS+排除标准+理由JSON", C_LLM, C_LLM_E, 8.4)
box(36.6, y2, 12.2, H, "Code 汇总\nrows / included\n/ analyzed", C_NODE, C_NODE_E, 8.2)
box(22.2, y2, 12.2, H, "LLM④\n生成筛查报告\nMarkdown", C_LLM, C_LLM_E, 8.2)
box(16.6, y2, 4.6, H, "结束\n5 个\n输出", C_NODE, C_NODE_E, 7.6)

yc1 = y1 + H / 2
yc2 = y2 + H / 2
# row1 arrows
arrow(28.7, yc1, 31.0, yc1)
arrow(43.2, yc1, 45.5, yc1)
arrow(57.7, yc1, 60.0, yc1)
arrow(72.2, yc1, 74.5, yc1)
# wrap: PubMed tool -> Code 解析 (snake down)
arrow(78.9, y1 - 0.1, 78.6, y2 + H + 0.1)
# row2 arrows (right-to-left)
arrow(72.5, yc2, 69.2, yc2)
arrow(51.5, yc2, 48.8, yc2)
arrow(36.6, yc2, 34.4, yc2)
arrow(22.2, yc2, 21.4, yc2)

# ---- client ----
box(16.5, 6.5, 18.0, 7.5, "客户端 run_screening.py\nSSE 流式调\nDify Service API\n导出 xlsx + md", C_CLIENT, C_CLIENT_E, 8.2)
arrow(25.5, 14.0, 25.5, 18.4)
ax.text(26.8, 15.6, "workflow / run", fontsize=8, color="#334155")

# ---- knowledge base, routed through the gap column at x=50.15 ----
box(44.0, 6.0, 21.0, 8.0, "Dify 知识库「MeSH 2025」\ndesc2025.xml -> mesh_kb.txt\nbge-m3 嵌入 + 混合检索 + 重排", C_KB, C_KB_E, 8.0)
conn([(50.15, 14.0), (50.15, 32.2), (37.1, y1 - 0.1)], color=C_KB_E,
     label="知识检索", label_at=(51.0, 20.2))

# ---- tool service + NCBI ----
box(71.5, 6.5, 21.5, 6.5, "tool-service (FastAPI)\n/pubmed/search  /mesh/expand\n封装 NCBI E-utilities", C_TOOL, C_TOOL_E, 8.0)
arrow(83.4, yc1, 89.0, 13.0, color=C_TOOL_E)
ax.text(88.6, 26.0, "HTTPS", fontsize=8, color=C_TOOL_E)
arrow(93.2, 10.0, 93.9, 10.0, color=C_EXT_E, dashed=True)
box(94.0, 7.5, 5.6, 5.4, "NCBI\nPubMed\nNLM MeSH", C_EXT, C_EXT_E, 7.4)

# title
ax.text(2, 53.5, "MedRAGent-Dify：医学文献自动检索与筛选系统（Dify 平台化重构）", fontsize=14,
        fontweight="bold", color="#0F172A")
ax.text(2, 50.6, "原版 FAISS+LangChain 脚本管线 -> Dify 工作流 + 知识库 + 自定义工具 + Service API", fontsize=10, color="#475569")

plt.tight_layout()
plt.savefig("docs/architecture.png", bbox_inches="tight", facecolor="white")
print("saved docs/architecture.png")
