import logging
from collections import deque
from typing import List, Dict, Optional

logger = logging.getLogger("NeeronAi")

class ConversationManager:
    """Manages chat history and system prompts for Ollama context."""
    def __init__(self, max_history: int = 50, system_prompt: str = ""):
        self.history = deque(maxlen=max_history)
        self.system_prompt = system_prompt
        if system_prompt:
            self.history.append({"role": "system", "content": system_prompt})
    
    def add_user(self, content: str):
        self.history.append({"role": "user", "content": content})
        logger.debug(f"Added user message: {content[:50]}...")
    
    def add_assistant(self, content: str, tool_calls: Optional[List] = None):
        msg = {"role": "assistant", "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.history.append(msg)
        logger.debug(f"Added assistant message: {content[:50]}...")
    
    def add_tool_result(self, tool_call_id: str, content: str):
        self.history.append({"role": "tool", "tool_call_id": tool_call_id, "content": content})
    
    def get_history(self) -> List[Dict]:
        return list(self.history)
    
    def clear(self):
        self.history.clear()
        if self.system_prompt:
            self.history.append({"role": "system", "content": self.system_prompt})
        logger.info("Conversation cleared")
