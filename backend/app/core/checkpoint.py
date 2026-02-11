import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from app.config import get_settings


class CheckpointManager:
    def __init__(self, session_id: str):
        self.session_id = session_id
        settings = get_settings()
        self.checkpoints_dir = settings.checkpoints_path
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path = self.checkpoints_dir / f"{session_id}.json"

    def save(
        self,
        step_id: str,
        thought: str,
        working_memory: Dict[str, Any],
        completed_steps: list,
        agent_mode: str,
    ):
        checkpoint = {
            "session_id": self.session_id,
            "step_id": step_id,
            "thought": thought,
            "working_memory": working_memory,
            "completed_steps": completed_steps,
            "agent_mode": agent_mode,
            "timestamp": datetime.now().isoformat(),
        }
        self.checkpoint_path.write_text(json.dumps(checkpoint))

    def load(self) -> Optional[Dict[str, Any]]:
        if self.checkpoint_path.exists():
            try:
                return json.loads(self.checkpoint_path.read_text())
            except:
                return None
        return None

    def clear(self):
        if self.checkpoint_path.exists():
            self.checkpoint_path.unlink()

    def exists(self) -> bool:
        return self.checkpoint_path.exists()

    def get_timestamp(self) -> Optional[str]:
        if self.exists():
            checkpoint = self.load()
            return checkpoint.get("timestamp")
        return None


def create_checkpoint_manager(session_id: str) -> CheckpointManager:
    return CheckpointManager(session_id)
