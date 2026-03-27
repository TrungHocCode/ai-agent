from typing import Literal, Optional
from .system_prompt import SUPERVISOR_PROMPT, WORKER_PROMPT
from .agent_state import State, SupervisorOutput, WorkerOutput
from langchain_core.messages import HumanMessage, SystemMessage

class AgentNode:
    def __init__(self, role: Literal["supervisor", "worker"], tools: Optional[list] = None, name: str = "a", agents_info: str = "", llm=None):
        self.name = name
        self.role = role
        self.system_prompt = SUPERVISOR_PROMPT if role =="supervisor" else WORKER_PROMPT
        self.llm = llm
        self.config = {"timeout":300, "max_retries":3}
        if self.role == "worker":
            self.tools = tools or []
            if self.tools:
                self.llm = llm.bind_tools(self.tools)
        if self.role == "supervisor":
            self.tools = {}
            self.agents_info = agents_info

    def _format_prompt(self, state:State):
        """Format prompt messages based on role"""
        if self.role == "supervisor":
            messages = state["messages"]
            formatted_messages = self._format_conversation_history(messages)
            system_prompt = self.system_prompt.format(
                mode=state["mode"],
                messages=formatted_messages,
                plan=state["plan"],
                current_task=state["current_task"],
                result_storage=state["result_storage"],
                available_agents=self.agents_info
            )
            prompt = [SystemMessage(content=system_prompt), HumanMessage(content="Based on the current state above, what is your next action?")]
        else:
            task = state["current_task"]
            tool_names = [t.name for t in self.tools]
            system_prompt = self.system_prompt.format(
                task_id=task.id,
                node=task.node,
                task_description=task.description,
                available_tools=", ".join(tool_names),
                result_storage = state["result_storage"]
            )
            prompt = [
                SystemMessage(content=system_prompt),
                HumanMessage(content="Execute your assigned task and return the result as JSON.")
            ]
        
        return prompt
    def _format_conversation_history(self, messages: list) -> str:
        """Convert message list to readable conversation string"""
        if not messages:
            return ""
        
        formatted = ""
        for i, msg in enumerate(messages):
            if isinstance(msg, HumanMessage):
                formatted += f"User: {msg}\n"
            else:
                formatted += f"Assistant: {msg}\n"
        
        return formatted.strip()
    def _parse_output(self, response):
        raw = response.content
        start_idx = raw.find('{')
        end_idx = raw.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            raise ValueError(f"No JSON object found in output: {raw}")
        
        clean_json = raw[start_idx:end_idx+1]
        # Strip markdown fence nếu LLM wrap trong ```json ... ```
        if clean_json.strip().startswith("```"):
            clean_json = (
                clean_json.strip()
                .removeprefix("```json")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )
        try:
            if self.role == "supervisor":
                return SupervisorOutput.model_validate_json(clean_json)
            else:
                return WorkerOutput.model_validate_json(clean_json)
        except Exception as e:
            raise ValueError(f"[{self.name}] Failed to parse LLM output: {e}\nRaw: {clean_json}")
    def _invoke(self, state:State):
        prompt = self._format_prompt(state)
        response = self.llm.invoke(prompt)
        if self.role =="worker" and response.tool_calls:
            return response
        return self._parse_output(response)