from typing import List, Dict, TypedDict, Optional, Literal, Annotated
from pydantic import BaseModel
from langchain_core.messages import BaseMessage

#Reducer functions
def add_messages(left, right):
    """Custom reducer: giữ lại 5 messages mới nhất"""
    if not isinstance(left, list):
        left = [left]
    if not isinstance(right, list):
        right = [right]

    return left + right

def add_logs(left: list, right: list) -> list:
    return left + right

#State
class Task(BaseModel):
    id: int
    node: str
    status: Literal["done", "pending", "running", "failed", "skipped"]
    error: Optional[str]
    description: str
class AgentInfo(BaseModel):
    id: int
    name: str
    tool_names: list[str]

class State(TypedDict):
    messages: Annotated[list[BaseMessage | str], add_messages]
    plan: list[Task]
    current_task: Optional[Task]
    logs: Annotated[list[str], add_logs]
    result_storage: list  # lưu tạm kết quả worker, sẽ thay bằng DB sau
    mode: Literal["conversation", "executing"]
    direction: Optional[str]     # academic | application

class SupervisorOutput(BaseModel):
    """Schema cho output của Supervisor Node"""
    mode: Literal["conversation", "executing"]  
    assistant_message: Optional[str] = None
    plan: Optional[List[Task]] = None
    current_task: Optional[Task] = None

class WorkerOutput(BaseModel):
    """Schema cho output của Worker Node"""
    status: Literal["done", "failed"]
    result: str
    error: Optional[str] = None