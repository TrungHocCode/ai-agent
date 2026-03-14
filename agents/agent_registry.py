from .tools import (
    search_arxiv, get_arxiv_detail,
    search_huggingface, get_model_detail,
    search_github, get_repo_detail,
    search_hackernews, tavily_search,
)

AGENT_REGISTRY = {
    "research_agent": {
        "tools": [search_arxiv, get_arxiv_detail, search_huggingface, get_model_detail, tavily_search],
        "description": "Tìm kiếm papers ArXiv, models HuggingFace và technical content"
    },
    "discovery_agent": {
        "tools": [search_github, get_repo_detail, search_hackernews, tavily_search],
        "description": "Khám phá GitHub repos, HackerNews discussions và AI product news"
    },
}