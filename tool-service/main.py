"""
PubMed Custom Tool Service for Dify.

Exposes the retrieval layer of MedRAGent (https://github.com/czczy/MedRAGent)
as public REST endpoints with an OpenAPI schema, so they can be registered in
Dify as "custom tools" (工具 -> 自定义 -> 创建自定义工具).

Endpoints
---------
GET /health           liveness probe (also used by Render)
GET /pubmed/search    PubMed Boolean search: esearch + efetch, parsed to JSON
GET /mesh/expand      MeSH descriptor lookup + entry-term (synonym) expansion

All endpoints are GET with query parameters on purpose: Dify custom tools
handle GET + query params most reliably and pass parameters with automatic
URL encoding, which matters because Boolean queries contain quotes/brackets.

Deployed on Render (free tier) so that Dify Cloud can reach them. Dify Cloud
can only call *public* HTTP endpoints; localhost is not an option.
"""

import os
import time
import xml.etree.ElementTree as ET
from typing import List, Optional

import requests
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
MESH_LOOKUP_BASE = "https://id.nlm.nih.gov/mesh/lookup"

ENTREZ_EMAIL = os.getenv("ENTREZ_EMAIL", "")
ENTREZ_API_KEY = os.getenv("ENTREZ_API_KEY", "")

MAX_RETRIES = 4
# NCBI allows 3 req/s without an API key and 10 req/s with one.
THROTTLE_SECONDS = 0.4 if not ENTREZ_API_KEY else 0.15

app = FastAPI(
    title="MedRAGent Tool Service",
    description="PubMed retrieval and MeSH expansion tools for Dify workflows",
    version="1.0.0",
)


def _eutils(tool: str, params: dict, expect: str = "json") -> requests.Response:
    """Call one E-utility tool (esearch.fcgi / efetch.fcgi) with throttling and retries."""
    if ENTREZ_API_KEY:
        params["api_key"] = ENTREZ_API_KEY
    if ENTREZ_EMAIL:
        params["email"] = ENTREZ_EMAIL

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(f"{EUTILS_BASE}/{tool}", params=params, timeout=30,
                                headers={"Accept": f"application/{expect}"})
            resp.raise_for_status()
            time.sleep(THROTTLE_SECONDS)
            return resp
        except requests.RequestException:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(2 ** attempt)


def _itertext(elem: Optional[ET.Element]) -> str:
    """Concatenate all text under an element (titles contain <i>/<b>/... tags)."""
    if elem is None:
        return ""
    return "".join(elem.itertext()).strip()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "entrez_email_configured": bool(ENTREZ_EMAIL),
        "entrez_api_key_configured": bool(ENTREZ_API_KEY),
        "timestamp": int(time.time()),
    }


@app.get("/pubmed/search")
def pubmed_search(
    query: str = Query(..., description="PubMed Boolean query, e.g. ((\"Diabetes Mellitus, Type 1\"[MeSH Terms]) AND (\"Fasting\"[MeSH Terms]))"),
    max_results: int = Query(20, ge=1, le=100, description="Max articles to return (1-100)"),
    sort: str = Query("relevance", pattern="^(relevance|pub_date)$", description="Sort order: relevance or pub_date"),
):
    """Search PubMed with a Boolean query and return parsed articles.

    Two-step E-utilities flow, same as the original MedRAGent pipeline:
    esearch (query -> PMIDs) then efetch (PMIDs -> full records in XML),
    parsed down to the fields the literature-screening LLM needs.
    """
    try:
        # Step 1: esearch -> total count + PMID list
        search = _eutils("esearch.fcgi", {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "sort": sort,
            "retmode": "json",
            "usehistory": "n",
        }).json()

        result = search.get("esearchresult", {})
        total = int(result.get("count", 0))
        pmids: List[str] = list(dict.fromkeys(result.get("idlist", [])))
        if not pmids:
            return {"query": query, "total": total, "returned": 0, "articles": []}

        # Step 2: efetch -> PubMed XML, parse per article
        fetch = _eutils("efetch.fcgi", {
            "db": "pubmed",
            "id": ",".join(pmids),
            "rettype": "xml",
            "retmode": "xml",
        }, expect="xml")

        root = ET.fromstring(fetch.content)
        articles = [
            _parse_article(node)
            for node in root.iter("PubmedArticle")
        ]
        articles = [a for a in articles if a]

        return {"query": query, "total": total, "returned": len(articles), "articles": articles}
    except Exception as exc:  # return structured errors so the workflow can branch on them
        return JSONResponse(status_code=502, content={"error": f"pubmed search failed: {exc}"})


def _parse_article(node: ET.Element) -> Optional[dict]:
    """Extract screening-relevant fields from one PubmedArticle XML node."""
    try:
        medline = node.find("MedlineCitation")
        article = medline.find("Article")

        title = _itertext(article.find("ArticleTitle"))

        abstract_parts = []
        abstract_node = article.find("Abstract")
        if abstract_node is not None:
            for part in abstract_node.findall("AbstractText"):
                label = part.get("Label")
                text = _itertext(part)
                if text:
                    abstract_parts.append(f"{label}: {text}" if label else text)
        abstract = " ".join(abstract_parts)

        journal = article.find("Journal")
        journal_title = _itertext(journal.find("Title")) if journal is not None else ""

        pub_year = ""
        pub_date_node = journal.find("JournalIssue/PubDate") if journal is not None else None
        if pub_date_node is not None:
            pub_year = _itertext(pub_date_node.find("Year")) or _itertext(pub_date_node.find("MedlineDate"))[:4]

        authors = []
        for author in article.findall("AuthorList/Author"):
            collective = _itertext(author.find("CollectiveName"))
            if collective:
                authors.append(collective)
            else:
                last = _itertext(author.find("LastName"))
                fore = _itertext(author.find("ForeName"))
                if last:
                    authors.append(f"{fore} {last}".strip())

        return {
            "pmid": _itertext(medline.find("PMID")),
            "title": title or "no title",
            "abstract": abstract or "no abstract",
            "journal": journal_title,
            "pub_year": pub_year,
            "authors": authors[:15],
        }
    except Exception:
        return None


@app.get("/mesh/expand")
def mesh_expand(
    term: str = Query(..., description="MeSH descriptor name, e.g. Diabetes Mellitus, Type 1"),
):
    """Resolve a MeSH descriptor name to its ID and entry terms (synonyms).

    Backs the term-expansion step of MedRAGent: the chosen MeSH heading and
    its entry terms are OR-ed together in the Boolean query.
    """
    try:
        lookup = requests.get(
            f"{MESH_LOOKUP_BASE}/descriptor",
            params={"label": term, "match": "exact", "year": "current"},
            timeout=20,
        )
        lookup.raise_for_status()
        mesh_id = None
        for item in lookup.json():
            if item.get("label", "").lower() == term.lower():
                mesh_id = item.get("resource", "").split("/")[-1]
                break
        if not mesh_id:
            return {"term": term, "mesh_id": None, "synonyms": []}

        details = requests.get(
            f"{MESH_LOOKUP_BASE}/details",
            params={"descriptor": mesh_id, "includes": "terms"},
            timeout=20,
        )
        details.raise_for_status()
        synonyms = [t.get("label", "") for t in details.json().get("terms", [])]
        return {"term": term, "mesh_id": mesh_id, "synonyms": synonyms}
    except Exception as exc:
        return JSONResponse(status_code=502, content={"error": f"mesh expand failed: {exc}"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
