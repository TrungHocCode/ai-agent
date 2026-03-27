# 🤖 Multi-Agent AI Research System

This is a multi-agent system designed to automate the process of researching, retrieving, and analyzing academic and technological information. Built on **LangGraph**, **LangChain**, and **Ollama** (for local LLMs), the system leverages a strict Supervisor-Worker architecture to plan and execute complex research queries.

## ✨ Key Features

* **Supervisor-Worker Architecture**: A dedicated `Supervisor` agent analyzes user intent, creates a step-by-step execution plan, and delegates tasks to specialized `Worker` agents.
* **Local LLM Integration**: Powered natively by **Ollama** (defaulting to the `qwen3:8b` model), allowing the system to run entirely locally for cost efficiency and data privacy.
* **Powerful Toolset**: Integrated with multiple APIs to fetch real-time data:
  * 🎓 **ArXiv API**: Search and retrieve metadata and abstracts for academic papers.
  * 🤗 **HuggingFace API**: Discover trending AI models and filter by specific tasks.
  * 🐙 **GitHub API**: Explore trending open-source repositories.
  * 📰 **HackerNews API**: Catch up on the latest tech discussions and news.
  * 🌐 **Tavily Search**: Perform general web searches for information outside specialized APIs.
* **Automated Markdown Reporting**: A dedicated `reporter_agent` is always scheduled as the final step to synthesize all gathered data into a clean, well-formatted Markdown report.

## 🧠 System Agents

* **`arxiv_researcher`**: Expert in finding and analyzing academic papers on ArXiv.
* **`model_researcher`**: Specialist in discovering and analyzing AI models on HuggingFace.
* **`discovery_agent`**: Explores GitHub repositories, HackerNews discussions, and general AI product news.
* **`reporter_agent`**: Data analyst expert that synthesizes previous findings into a detailed Markdown report.

## 📂 Project Structure

* `agent.py`: Defines the `AgentNode` class, handling prompt formatting, LLM invocation, and JSON output parsing for both Supervisor and Worker roles.
* `agent_registry.py`: Registers the available agents and maps them to their specific tools.
* `agent_state.py`: Defines the LangGraph State, including Pydantic models for tasks and custom reducers for message and log management.
* `multi_agent.py`: The core LangGraph setup. It initializes the LLM, builds the graph nodes and edges, routes tasks, and provides the CLI interface.
* `system_prompt.py`: Contains the strict system prompts dictating the behavior of the Supervisor and Worker agents.
* `tools.py`: Houses all the integrated API functions (ArXiv, HuggingFace, GitHub, HackerNews, Tavily) wrapped as LangChain `@tool`s.

## 🚀 Installation Guide

**1. Prerequisites**
* Python 3.9 or higher.
* [Ollama](https://ollama.com/) installed and running locally on the default port (`http://127.0.0.1:11434`).

**2. Install Dependencies**
Clone the repository and install the required Python packages using the provided `requirements.txt`:

```bash
pip install -r requirements.txt