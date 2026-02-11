from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: List[str] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)


@dataclass
class SubTask:
    id: str
    description: str
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None


class WorkingMemory:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.conversation: List[Message] = []
        self.subtasks: Dict[str, SubTask] = {}
        self.artifacts: Dict[str, Any] = {}
        self.reflection_notes: str = ""
        self.current_goal: str = ""
        self.execution_trace: List[Dict] = []

    def add_message(self, role: str, content: str):
        self.conversation.append(Message(role=role, content=content))

    def add_observation(self, tool_name: str, observation: str):
        if self.conversation:
            self.conversation[-1].observations.append(f"{tool_name}: {observation}")
        self.execution_trace.append(
            {
                "tool": tool_name,
                "observation": str(observation)[:500],
                "timestamp": datetime.now().isoformat(),
            }
        )

    def add_artifact(self, key: str, value: Any):
        self.artifacts[key] = value

    def get_artifact(self, key: str) -> Any:
        return self.artifacts.get(key)

    def create_subtask(self, task_id: str, description: str) -> SubTask:
        subtask = SubTask(id=task_id, description=description, status="pending")
        self.subtasks[task_id] = subtask
        return subtask

    def update_subtask(
        self, task_id: str, status: str = None, result: Any = None, error: str = None
    ):
        if task_id in self.subtasks:
            subtask = self.subtasks[task_id]
            if status:
                subtask.status = status
            if result:
                subtask.result = result
            if error:
                subtask.error = error

    def get_subtask(self, task_id: str) -> Optional[SubTask]:
        return self.subtasks.get(task_id)

    def get_pending_subtasks(self) -> List[SubTask]:
        return [st for st in self.subtasks.values() if st.status == "pending"]

    def get_context_for_llm(self) -> str:
        messages = [f"{m.role}: {m.content}" for m in self.conversation[-10:]]
        artifacts = [f"{k}: {str(v)[:200]}" for k, v in self.artifacts.items()]
        return "\n".join(messages + artifacts)

    def get_execution_summary(self) -> Dict:
        return {
            "total_steps": len(self.execution_trace),
            "artifacts_count": len(self.artifacts),
            "subtasks_count": len(self.subtasks),
            "conversation_turns": len(self.conversation),
        }

    def clear(self):
        self.conversation.clear()
        self.subtasks.clear()
        self.artifacts.clear()
        self.reflection_notes = ""
        self.execution_trace.clear()
        self.current_goal = ""

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "current_goal": self.current_goal,
            "execution_trace": self.execution_trace,
            "artifacts_keys": list(self.artifacts.keys()),
            "subtasks_ids": list(self.subtasks.keys()),
            "conversation_turns": len(self.conversation),
        }
