import os
import logging
from collections import deque
from typing import List, Dict, Optional

logger = logging.getLogger("NeeronAi")

class ConversationManager:
    """Manages chat history and system prompts for Ollama context with image reference sanitization."""
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
    
    def clean_invalid_images(self):
        """Removes image references from past messages if the image file no longer exists on disk."""
        for msg in self.history:
            if "images" in msg:
                valid_images = [img for img in msg["images"] if os.path.exists(str(img))]
                if valid_images:
                    msg["images"] = valid_images
                else:
                    msg.pop("images", None)
    
    def get_history(self) -> List[Dict]:
        """Returns sanitized conversation history, stripping missing image file references."""
        self.clean_invalid_images()
        sanitized = []
        for msg in self.history:
            msg_copy = dict(msg)
            if "images" in msg_copy:
                valid_images = [img for img in msg_copy["images"] if os.path.exists(str(img))]
                if valid_images:
                    msg_copy["images"] = valid_images
                else:
                    msg_copy.pop("images", None)
            sanitized.append(msg_copy)
        return sanitized
    
    def clear(self):
        self.history.clear()
        if self.system_prompt:
            self.history.append({"role": "system", "content": self.system_prompt})
        logger.info("Conversation cleared")
