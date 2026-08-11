import os
import logging
from collections import deque
from typing import List, Dict, Optional

logger = logging.getLogger("NeeronAi")

class ConversationManager:
    """Manages chat history and system prompts with Trajectory Compression (OpenClaw) and image reference sanitization."""
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
    
    def compress_trajectory_if_needed(self):
        """Compresses old tool execution turns into a compact summary block if history exceeds 15 items (OpenClaw feature)."""
        if len(self.history) <= 15:
            return
        
        logger.info("Compressing conversation trajectory to optimize context token window...")
        system_msg = None
        user_msgs = []
        recent_msgs = []
        
        items = list(self.history)
        for msg in items:
            if msg.get("role") == "system":
                system_msg = msg
            elif msg.get("role") == "user" and len(user_msgs) == 0:
                user_msgs.append(msg)
        
        # Keep latest 6 turns intact
        recent_msgs = items[-6:]
        
        compressed_summary = {
            "role": "user",
            "content": "[COMPRESSED TRAJECTORY SUMMARY]: Prior steps executed. System state verified. Continuing execution."
        }
        
        new_history = deque(maxlen=self.history.maxlen)
        if system_msg:
            new_history.append(system_msg)
        if user_msgs:
            new_history.append(user_msgs[0])
        new_history.append(compressed_summary)
        for m in recent_msgs:
            if m not in new_history:
                new_history.append(m)
        
        self.history = new_history
    
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
        """Returns trajectory-compressed and sanitized conversation history compliant with Ollama API specs."""
        self.compress_trajectory_if_needed()
        self.clean_invalid_images()
        sanitized = []
        
        image_count = 0
        reversed_history = list(reversed(self.history))
        
        for msg in reversed_history:
            msg_copy = dict(msg)
            
            if "images" in msg_copy:
                if msg_copy.get("role") != "user" or image_count >= 2:
                    msg_copy.pop("images", None)
                else:
                    valid_images = [img for img in msg_copy["images"] if os.path.exists(str(img))]
                    if valid_images:
                        msg_copy["images"] = valid_images
                        image_count += len(valid_images)
                    else:
                        msg_copy.pop("images", None)
            
            sanitized.append(msg_copy)
        
        return list(reversed(sanitized))
    
    def clear(self):
        self.history.clear()
        if self.system_prompt:
            self.history.append({"role": "system", "content": self.system_prompt})
        logger.info("Conversation cleared")
