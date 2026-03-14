# from typing import Dict, List, Optional
# from pydantic import BaseModel, AnyHttpUrl
# import requests
# from tavily import TavilyClient
# from langchain_core.tools import tool
# import feedparser
# from datetime import date
# # Web research agent
# class ArxivPaper(BaseModel):
#     title: str
#     authors: list[str]
#     summary: str
#     link: AnyHttpUrl

# @tool
# def research_paper(search_query:str, start:int, max_results: int = 5) -> list[dict]:
#     """Search paper on Arxiv"""
#     url = "http://export.arxiv.org/api/query"
#     response =  requests.get(url, params={"search_query" : search_query, "start":start, "max_results": max_results})
#     feed = feedparser.parse(response.text)
#     result = [
#         ArxivPaper(
#                 title=entry.title, 
#                 authors=[author.name for author in entry.authors], 
#                 summary=entry.summary, 
#                 link=entry.link
#             ) 
#             for entry in feed.entries
#         ] 
      
#     return [paper.model_dump() for paper in result]

# #https://huggingface.co/spaces/huggingface/openapi#description/introduction huggingface api documents
# @tool
# def research_huggingface(search_query: str) -> list[dict]:
#     """Search trending models in huggingface"""
#     url = "https://huggingface.co/api/models"
#     response = requests.get(url, params={"search": search_query, "limit": 5, "sort": "downloads", "direction": -1})
#     if response.status_code != 200:
#         return [{"error": f"HuggingFace API error: {response.status_code}"}]
#     models = response.json()
#     return [
#         {
#             "model_id": m.get("modelId", ""),
#             "downloads": m.get("downloads", 0),
#             "likes": m.get("likes", 0),
#             "tags": m.get("tags", [])[:5],
#             "last_modified": m.get("lastModified", "")[:10]
#         }
#         for m in models
#     ]

# @tool
# def search_github_trend(topic: str = 'AI', sort: str = 'stars', order: str = 'desc', top_k: int = 5):
#     """Search trending github repositories"""
#     url = "https://api.github.com/search/repositories"
#     current = date.today()
#     q = f"created:<{current} topic:{topic}"
#     params = {"q": q, "sort": sort, "order": order, "per_page": top_k}

#     response = requests.get(url, params=params)
#     content = response.json()

#     result = []
#     for data in content.get('items', []):
#         result.append({
#             "name": data["name"],
#             "url": data["html_url"],
#             "desc": data["description"],
#             "language": data["language"]
#         })
#     return result

# tools.py
import requests
import feedparser
from datetime import date, timedelta
from langchain_core.tools import tool
from tavily import TavilyClient
import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("TAVILY_API_KEY")
tavily = TavilyClient(api_key=api_key)

# ─── research_agent tools ──────────────────────────────────────

@tool
def search_arxiv(query: str, days_back: int = 7, max_results: int = 5) -> list[dict]:
    """Search recent papers on ArXiv. Use days_back to filter recency."""
    url = "http://export.arxiv.org/api/query"
    response = requests.get(url, params={
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    })
    feed = feedparser.parse(response.text)
    cutoff = date.today() - timedelta(days=days_back)

    results = []
    for entry in feed.entries:
        published = entry.get("published", "")[:10]
        if published and published < str(cutoff):
            continue
        results.append({
            "title": entry.title,
            "authors": [a.name for a in entry.authors[:3]],  # top 3 authors
            "summary": entry.summary[:500],                   # trim dài
            "link": entry.link,
            "published": published,
        })
    return results

@tool
def get_arxiv_detail(arxiv_url: str) -> dict:
    """Get full abstract and metadata of a specific ArXiv paper by URL."""
    paper_id = arxiv_url.rstrip("/").split("/")[-1]
    url = f"http://export.arxiv.org/api/query?id_list={paper_id}"
    feed = feedparser.parse(requests.get(url).text)
    if not feed.entries:
        return {"error": "Paper not found"}
    e = feed.entries[0]
    return {
        "title": e.title,
        "authors": [a.name for a in e.authors],
        "summary": e.summary,
        "published": e.get("published", "")[:10],
        "link": e.link,
        "tags": [t.term for t in e.get("tags", [])],
    }

@tool
def search_huggingface(query: str, task: str = "", max_results: int = 5) -> list[dict]:
    """
    Search models on HuggingFace.
    task: filter by pipeline tag e.g. 'text-generation', 'image-classification'
    """
    params = {
        "search": query,
        "limit": max_results,
        "sort": "downloads",
        "direction": -1,
    }
    if task:
        params["pipeline_tag"] = task

    response = requests.get("https://huggingface.co/api/models", params=params)
    if response.status_code != 200:
        return [{"error": f"HuggingFace API error: {response.status_code}"}]

    return [
        {
            "model_id": m.get("modelId", ""),
            "downloads_month": m.get("downloads", 0),
            "likes": m.get("likes", 0),
            "pipeline_tag": m.get("pipeline_tag", ""),
            "tags": m.get("tags", [])[:5],
            "last_modified": m.get("lastModified", "")[:10],
        }
        for m in response.json()
    ]

@tool
def get_model_detail(model_id: str) -> dict:
    """Get model card and details for a specific HuggingFace model."""
    response = requests.get(f"https://huggingface.co/api/models/{model_id}")
    if response.status_code != 200:
        return {"error": f"Model not found: {model_id}"}
    m = response.json()
    return {
        "model_id": m.get("modelId", ""),
        "author": m.get("author", ""),
        "pipeline_tag": m.get("pipeline_tag", ""),
        "downloads": m.get("downloads", 0),
        "likes": m.get("likes", 0),
        "tags": m.get("tags", []),
        "card_data": m.get("cardData", {}),  # license, language, datasets
    }

@tool
def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    """
    General web search via Tavily. Use for:
    - technical blog posts and tutorials
    - product announcements and releases
    - anything not covered by specialized APIs
    """
    response = tavily.search(query=query, max_results=max_results)
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", "")[:400],
            "score": round(r.get("score", 0), 3),
        }
        for r in response.get("results", [])
    ]

# ─── discovery_agent tools ─────────────────────────────────────

@tool
def search_github(topic: str, language: str = "", days_back: int = 30, top_k: int = 5) -> list[dict]:
    """
    Search trending GitHub repos by topic.
    language: filter by e.g. 'python', 'typescript'
    days_back: only repos created/pushed within N days
    """
    cutoff = date.today() - timedelta(days=days_back)
    q = f"topic:{topic} pushed:>{cutoff}"
    if language:
        q += f" language:{language}"

    response = requests.get(
        "https://api.github.com/search/repositories",
        params={"q": q, "sort": "stars", "order": "desc", "per_page": top_k},
        headers={"Accept": "application/vnd.github+json"},
    )
    if response.status_code != 200:
        return [{"error": f"GitHub API error: {response.status_code}"}]

    return [
        {
            "name": r["full_name"],
            "url": r["html_url"],
            "description": r.get("description", ""),
            "stars": r["stargazers_count"],
            "language": r.get("language", ""),
            "pushed_at": r["pushed_at"][:10],
        }
        for r in response.json().get("items", [])
    ]

@tool
def get_repo_detail(repo_full_name: str) -> dict:
    """
    Get details of a GitHub repo: README summary, open issues, license.
    repo_full_name: format 'owner/repo', e.g. 'huggingface/transformers'
    """
    base = f"https://api.github.com/repos/{repo_full_name}"
    info = requests.get(base).json()
    readme_resp = requests.get(
        f"{base}/readme",
        headers={"Accept": "application/vnd.github.raw"}
    )
    readme = readme_resp.text[:800] if readme_resp.status_code == 200 else ""

    return {
        "name": info.get("full_name", ""),
        "description": info.get("description", ""),
        "stars": info.get("stargazers_count", 0),
        "forks": info.get("forks_count", 0),
        "open_issues": info.get("open_issues_count", 0),
        "license": info.get("license", {}).get("name", ""),
        "readme_preview": readme,
    }

@tool
def search_hackernews(query: str, top_k: int = 5) -> list[dict]:
    """Search HackerNews for AI-related discussions, Show HN, Ask HN."""
    response = requests.get(
        "https://hn.algolia.com/api/v1/search",
        params={"query": query, "tags": "story", "hitsPerPage": top_k},
    )
    if response.status_code != 200:
        return [{"error": "HN API error"}]

    return [
        {
            "title": h.get("title", ""),
            "url": h.get("url", "") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
            "points": h.get("points", 0),
            "comments": h.get("num_comments", 0),
            "created_at": h.get("created_at", "")[:10],
        }
        for h in response.json().get("hits", [])
    ]