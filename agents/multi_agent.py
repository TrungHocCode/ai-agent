from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from .agent_state import State, Task
from .agent import AgentNode
from typing import Dict, Optional
from logger import get_logger
from .agent_registry import AGENT_REGISTRY
from langgraph.types import Command
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage, AIMessage
from dotenv import load_dotenv
load_dotenv()
import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
logger = get_logger("app")

class MultiAgentGraph:
    @staticmethod
    def _default_config() -> Dict:
        """Default config for llm và agent"""
        return {
            "max_retries": 3,        # Số lần thử lại khi gọi LLM
            "temperature": 0.5,      # Độ "sáng tạo" của LLM (0-1)
            "timeout": 200,          # Timeout cho mỗi request (giây)
            "debug": False            # Bật/tắt debug mode
        }
    
    def __init__(self, llm = None, registry:Dict = None, config: Dict=None):
        self.config = config or self._default_config()
        self.registry = registry or  {}
        self.workers = {}
        # Tạo LLM nếu không truyền vào, áp dụng config
        if llm is None:
            self.llm = ChatOllama(
                model="qwen3:8b", 
                base_url=OLLAMA_BASE_URL,
                temperature=self.config.get("temperature", 0.5),
                top_k=40,      # Top-K sampling
                top_p=0.9      # Nucleus sampling
            )
        else:
            self.llm = llm
        self.workers: Dict[str, AgentNode] = {}   # ✅ init trước khi _create_workers gọi
        self._create_workers()
        self.tool_nodes = self._build_tool_node()
        self.agents_info = self._build_agents_info()
        # supervisor should know about available tools/workers
        self.supervisor = AgentNode(
            role="supervisor",
            name="supervisor",
            llm=self.llm,
            agents_info = self.agents_info
        )
        
        self.graph: Optional[StateGraph] = None
        self.compiled_graph = self._create_graph()
        self.current_state = None
        if self.config.get("debug"):
            logger.info(f"Config: {self.config}")

    def _create_workers(self):
        if not self.registry:
            logger.warning("No tools found! Still create workers!")
        for name, info in self.registry.items():
            worker_agent = AgentNode(
                role="worker",
                tools=info["tools"],
                name=name,
                llm=self.llm
            )
            self.workers[name] = worker_agent
            logger.info(f"Create worker: {name} successfully")
    
    def _build_agents_info(self) -> str:
        """Format thông tin agents cho supervisor prompt"""
        lines = []
        for name, info in self.registry.items():
            tool_names = [t.name for t in info["tools"]]
            lines.append(
                f"- {name}: {info['description']} | tools: {tool_names}"
            )
        return "\n".join(lines)
    
    def _build_tool_node(self) -> dict:
        tool_node_dict = {}
        for name, info in self.registry.items():
            tool_node_dict[name] = ToolNode(info["tools"])
            logger.info(f"Tools: Created tool for {name} successfully")
        return tool_node_dict
    
    def _advance_task(self, plan):
        if plan:
            return next((t for t in plan if t.status == "pending"), None)
        return None
    
    def _supervisor_node(self, state: State) -> Dict:
        """Supervisor node - quyết định mode tiếp theo"""
        try:
            response = self.supervisor._invoke(state)
            logger.info(f"Supervisor: mode={response.mode}, messages:{response.assistant_message}")
            logger.info(f"Plan: {response.plan}")
            next_task = self._advance_task(response.plan if response.plan else None)
            update_data = {
                "mode":response.mode,
                "current_task": next_task,
                "messages": [response.assistant_message] if response.assistant_message else []
            }
            if response.plan:
                update_data["plan"] = response.plan
            return update_data
        except Exception as e :
            logger.error(f"Error in supervisor node: {str(e)}", exc_info=True)
            return {
                "mode": "conversation",
                "messages": state.get("messages", []) + [f"Error: {str(e)}"],
                "logs": state.get("logs", []) + [f"[ERROR] {str(e)}"]
            }
        
    def _worker_node(self, state: State, worker_name: str) -> Dict:
        """Worker node - thực hiện task với retry logic"""
        try:
            if worker_name not in self.workers.keys():
                logger.error(f"Not found this {worker_name} worker agent!")
            worker = self.workers[worker_name]
            current_task: Optional[Task] = state.get("current_task")
            msg = state.get("messages")
            last_msg = msg[-1] if msg else None
            logger.info(f"{worker_name} is doing task: {current_task}")
            if isinstance(last_msg, ToolMessage):
                response = worker.llm.invoke(msg)
            else:
                response = worker._invoke(state)
            if isinstance(response, AIMessage):
                if response.tool_calls:
                    return {"messages": [response], "current_task": current_task}
            
            current_task.status = "done"
            logger.info(f"Worker {worker_name} complete it's tasks.")
            plan = state.get("plan", [])
            for t in plan: 
                if t.id == current_task.id:
                    t.status = "done"
            next_task = self._advance_task(plan)
            if next_task is None:
                return Command(
                    goto = "supervisor",
                    update={
                        "current_task": None,
                        "result_storage":state.get("result_storage", []) + [
                            {"worker":worker_name, "task_id": current_task.id, "result": response.content}
                        ]
                    }
                )
            return Command(
                goto = f"{next_task.node}",
                update = {
                    "current_task": next_task,
                    "result_storage":state.get("result_storage", []) + [
                            {"worker":worker_name, "task_id": current_task.id, "result": response.content}
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Error in woker node: {str(e)}", exc_info=True)
            return {
                "mode": "conversation",
                "messages": state.get("messages", []) + [f"Error: {str(e)}"]
            }
        
    def _tool_node(self, state:State, agent_name:str):
        """Tool node thực hiện task bằng tool đã được định nghĩa"""
        node = self.tool_nodes[agent_name]
        result = node.invoke(state)
        tool_messages = result.get("messages", [])
        storage = state.get("result_storage")
        logger.info(f"{agent_name} is using this tool")
        for msg in tool_messages:
            if hasattr(msg, "content") and isinstance(msg.content, list):
                storage.extend(msg.content)
        return {"messages": tool_messages, "result_storage": storage}
    
    @staticmethod   
    def _router(state: State):
        mode = state["mode"]
        
        if mode == "conversation":
            return END 
        
        elif mode == "executing":
            task = state.get("current_task")
            if task and task.status == "pending":
                return task.node 
            return END    
        return END  
    def _worker_router(self, state: State, worker_name:str):
        messages = state.get("messages", [])
        if not messages:
            return END

        last_msg = messages[-1]

        # Có tool_calls → sang tool_node
        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            return f"{worker_name}_tools"
        return END
    def _create_graph(self):
        """Build and compile the multi-agent graph"""
        graph = StateGraph(State)
        graph.add_node("supervisor", self._supervisor_node)
        
        for worker_name in self.workers.keys():
            graph.add_node(
                worker_name, 
                lambda state, wn=worker_name: self._worker_node(state, wn)
            )
            graph.add_node(
                f"{worker_name}_tools",
                lambda state, wn=worker_name: self._tool_node(state, wn)
            )
            graph.add_edge(f"{worker_name}_tools", f"{worker_name}")
            graph.add_conditional_edges(
                worker_name,
                lambda state, wn=worker_name: self._worker_router(state, wn),
                {f"{worker_name}_tools": f"{worker_name}_tools", END: END}
            )
        graph.set_entry_point("supervisor")
        
        path_map = {"supervisor": "supervisor", END: END}
        path_map.update({name: name for name in self.workers.keys()})
        
        # Add conditional edges to supervisor và worker nodes
        graph.add_conditional_edges("supervisor", self._router, path_map)
        
        self.compiled_graph = graph.compile()
        logger.info("Graph created and compiled successfully")

        return self.compiled_graph
    
    def invoke(self, user_query: str):
        """Public invoke method - execute graph until END node"""
        if not self.compiled_graph:
            return {"status": "error", "error": "Graph not compiled", "messages": []}
        
        if self.current_state is None:
            self.current_state: State = {
                "messages": [user_query],
                "plan": [],
                "current_task": None,
                "logs": [],
                "result_storage": [],
                "mode": "conversation",
                "direction": None    
            }
        else:
            self.current_state["messages"].append(user_query)
        try:
            # Use invoke which automatically stops at END
            result = self.compiled_graph.invoke(self.current_state)
            self.current_state = result
            return {
                "status": "success",
                "result": result,
                "messages": result.get("messages", []),
                "plan": result.get("plan", [])
            }
        except Exception as e:
            logger.error(f"Invoke error: {str(e)}", exc_info=True)
            return {"status": "error", "error": str(e), "messages": []}

    def get_messages(self):
        if self.current_state.get("messages") == None:
            return
        messages = self.current_state.get('messages')
        print(f"All messages: {messages}")


