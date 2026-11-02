"""
MedRAGent-Dify client.

Calls the published Dify workflow app (Service API) end-to-end with a PICOS
definition, waits for the run to finish, and exports the screening results to
an xlsx report whose columns mirror the original MedRAGent report
(report (deepseek).xlsx): PMID / Title / Included / PICOS match reasons /
Exclusion reasons, plus the LLM-generated markdown report.

Usage
-----
    pip install requests openpyxl
    python run_screening.py --config config.json
    # or set env vars: DIFY_API_KEY (+ optional DIFY_BASE_URL)

config.json example:
{
    "api_key": "app-xxxxxxxx",
    "base_url": "https://api.dify.ai/v1",
    "inputs": {
        "picos": "P: Type 1 Diabetes Mellitus, adolescent; I: fasting during Ramadan; C: ; O: hyperglycemia, hypoglycemia, diabetic ketoacidosis, changes in HbA1c, and weight changes; S: observational studies (e.g., prospective study, cohort studies, case-control studies, cross-sectional studies)",
        "exclusion": "Animal studies\nCase reports\nSystematic reviews\nmeta analysis",
        "date_start": "2001/05/01",
        "date_end": "2024/02/13",
        "max_results": 20
    },
    "timeout_minutes": 30,
    "user": "medragent-demo"
}
"""

import argparse
import datetime as dt
import json
import os
import sys
import time

import requests

DEFAULT_BASE_URL = "https://api.dify.ai/v1"
WORKFLOWS_RUN = "/workflows/run"
WORKFLOW_STOP = "/workflows/run/{execution_id}/stop"


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg.setdefault("base_url", os.environ.get("DIFY_BASE_URL", DEFAULT_BASE_URL))
    cfg.setdefault("api_key", os.environ.get("DIFY_API_KEY", ""))
    cfg.setdefault("timeout_minutes", 30)
    cfg.setdefault("user", "medragent-client")
    if not cfg["api_key"]:
        sys.exit("error: api_key missing (config.json or DIFY_API_KEY env)")
    return cfg


def run_workflow(cfg: dict) -> dict:
    """Streaming workflow run (SSE).

    Streaming is used instead of blocking mode because long runs (the
    per-article screening iteration can take minutes) exceed the platform's
    blocking HTTP timeout. We consume events until `workflow_finished` and
    return its data payload (End-node outputs included).
    """
    url = cfg["base_url"] + WORKFLOWS_RUN
    headers = {"Authorization": f"Bearer {cfg['api_key']}"}
    payload = {
        "inputs": cfg["inputs"],
        "response_mode": "streaming",
        "user": cfg["user"],
    }

    deadline = time.time() + cfg["timeout_minutes"] * 60
    result = None
    finished_events = ("workflow_finished", "workflow_failed")

    with requests.post(url, headers=headers, json=payload, stream=True, timeout=300) as resp:
        if resp.status_code != 200:
            sys.exit(f"error: workflow run failed: HTTP {resp.status_code} {resp.text[:500]}")
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            try:
                event = json.loads(line[len("data:"):].strip())
            except json.JSONDecodeError:
                continue
            etype = event.get("event")
            if etype in finished_events:
                result = event
                break
            if etype == "node_finished":
                node = event.get("data", {})
                title = node.get("title", node.get("node_type", "?"))
                elapsed = node.get("elapsed", 0)
                print(f"  [node done] {title} ({elapsed:.1f}s)")
            elif etype == "error":
                print(f"  [error] {event.get('message', '')[:300]}")
            if time.time() > deadline:
                sys.exit("error: client-side timeout reached before workflow_finished")

    if result is None:
        sys.exit("error: stream ended without workflow_finished")
    if result["event"] == "workflow_failed":
        print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])
        sys.exit("error: workflow failed")
    return result


def save_outputs(result: dict, prefix: str = "report") -> None:
    """Persist End-node outputs: screening rows -> xlsx, markdown -> .md."""
    from openpyxl import Workbook

    data = result.get("data", {})
    outputs = data.get("outputs", {})
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")

    rows = outputs.get("rows") or []
    if isinstance(rows, str):
        rows = json.loads(rows)

    xlsx_path = f"{prefix}_{stamp}.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "screening"
    header = ["PMID", "Title", "Included", "Population Match", "Intervention Match",
              "Comparison Match", "Outcome Match", "Study Design", "Exclusion Reasons"]
    ws.append(header)
    for row in rows:
        ws.append([row.get(col.lower().replace(" ", "_"), "") for col in header])
    wb.save(xlsx_path)

    md_path = f"{prefix}_{stamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(outputs.get("report", ""))

    print(f"run_id:   {data.get('id')}")
    print(f"total / analyzed / included: {outputs.get('total')} / {outputs.get('analyzed')} / {outputs.get('included')}")
    print(f"saved:    {xlsx_path}")
    print(f"saved:    {md_path}")


def main():
    parser = argparse.ArgumentParser(description="Run MedRAGent-Dify workflow via Service API")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--prefix", default="report_dify")
    args = parser.parse_args()

    cfg = load_config(args.config)
    print(f"POST {cfg['base_url']}{WORKFLOWS_RUN} (blocking, timeout {cfg['timeout_minutes']} min)")
    result = run_workflow(cfg)

    if result.get("data", {}).get("status") != "succeeded":
        print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])
        sys.exit("error: workflow did not succeed")

    save_outputs(result, prefix=args.prefix)


if __name__ == "__main__":
    main()
