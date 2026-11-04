---
title: MedRAGent Tool Service
emoji: 🔎
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# MedRAGent Tool Service (Hugging Face Space)

将本目录的 4 个文件（`README.md`、`main.py`、`requirements.txt`、`Dockerfile`）上传到一个
**Docker 类型** 的 Hugging Face Space（Public），即可获得免费公网 HTTPS 端点：

```
https://<你的用户名>-<space名>.hf.space
```

- HF 会注入 `PORT=7860`，`main.py` 已按环境变量监听，无需改动；
- `app_port: 7860` 与之对应；
- 上传方式：Space 页面 Files → Add file → Upload files（或 git push）；
- 部署完成后用 `/health` 验证，再把域名填入 `tool-service/openapi.json` 的 `servers.url`，
  按 `dify/SETUP.md` §7 注册为 Dify 自定义工具。

可选环境变量（Space → Settings → Variables and secrets）：
`ENTREZ_EMAIL`、`ENTREZ_API_KEY`（提升 NCBI 限速 3 -> 10 req/s）。
