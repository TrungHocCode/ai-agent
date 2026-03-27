from .tools import (
    search_arxiv, get_arxiv_detail,
    search_huggingface, get_model_detail,
    search_github, get_repo_detail,
    search_hackernews, tavily_search,
)

AGENT_REGISTRY = {
    "arxiv_researcher": {
        "tools": [search_arxiv, get_arxiv_detail, tavily_search],
        "description": "Chuyên gia tìm kiếm, đọc và phân tích các bài báo học thuật trên ArXiv."
    },
    "model_researcher": {
        "tools": [search_huggingface, get_model_detail, tavily_search],
        "description": "Chuyên gia tìm kiếm và phân tích các mô hình AI trên HuggingFace."
    },
    "discovery_agent": {
        "tools": [search_github, get_repo_detail, search_hackernews, tavily_search],
        "description": "Khám phá GitHub repos, HackerNews discussions và AI product news."
    },
    "reporter_agent": {
        "tools": [],
        "description": "Chuyên gia phân tích dữ liệu và viết báo cáo Markdown chi tiết. Luôn được sử dụng ở bước cuối cùng của mọi kế hoạch."
    },
}