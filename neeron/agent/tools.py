import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from neeron.os_world.app_manager import DesktopAppManager
from neeron.os_world.system import SystemController
from neeron.os_world.vision import ScreenPerception
from neeron.os_world.gui_controller import GUIController

logger = logging.getLogger("NeeronAi")

class AgentToolRegistry:
    """Tool definition registry and execution dispatcher including GUI, Vision, Selenium Web Automation, Voice Input, and Task Completion tools."""
    def __init__(self, app_manager: DesktopAppManager, system_controller: SystemController, vision: ScreenPerception, gui: GUIController, stt=None, tts=None):
        self.app_manager = app_manager
        self.system_controller = system_controller
        self.vision = vision
        self.gui = gui
        self.stt = stt
        self.tts = tts
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "task_completed",
                    "description": "Call this tool when you have visually verified from the screenshot that the requested task/GUI action is fully completed.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "Brief description of what was completed and verified visually."
                            }
                        },
                        "required": ["summary"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "ask_user_voice",
                    "description": "Ask the user a clarification question, request login credentials/confirmation, or request voice input mid-task via TTS. ALWAYS use this tool when encountering login screens, authentication prompts, passwords, or security-sensitive tasks.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The question or prompt to speak to the user to request voice clarification."
                            }
                        },
                        "required": ["question"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_browser",
                    "description": "Open a website URL in Selenium Firefox/Chrome browser.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to open (e.g. 'google.com', 'github.com')"}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "browser_click",
                    "description": "Click a link, button, or element on the active Selenium webpage by visible text, ID, placeholder, CSS selector, or XPath.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Visible text, ID, name, placeholder, CSS, or XPath of the element to click (e.g. 'Search', 'Sign In', '#submit-btn')"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "browser_type",
                    "description": "Type text into a search bar or input field on the active Selenium webpage.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Placeholder, name, ID, CSS, or XPath of input field (e.g. 'q', 'search', 'email', 'username')"},
                            "text": {"type": "string", "description": "Text content to type into the webpage input field"},
                            "press_enter": {"type": "boolean", "description": "Whether to press Enter key after typing", "default": True}
                        },
                        "required": ["query", "text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "browser_scroll",
                    "description": "Scroll the active webpage up or down.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "direction": {"type": "string", "description": "Scroll direction: 'down' or 'up'", "default": "down"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "inspect_screen",
                    "description": "Capture current desktop screenshot to inspect visual state of open application windows.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "gui_click",
                    "description": "Click the mouse at specific pixel coordinates (x, y) on screen.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer", "description": "X coordinate in pixels"},
                            "y": {"type": "integer", "description": "Y coordinate in pixels"},
                            "button": {"type": "string", "description": "Mouse button: 'left', 'right', 'middle'", "default": "left"},
                            "clicks": {"type": "integer", "description": "Number of clicks", "default": 1}
                        },
                        "required": ["x", "y"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "gui_type",
                    "description": "Type text into currently focused application or input field.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Text content to type"},
                            "press_enter": {"type": "boolean", "description": "Whether to press Enter key after typing", "default": True}
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "gui_hotkey",
                    "description": "Press a key or key combination (e.g. ['ctrl', 's'], ['alt', 'tab'], ['enter'], ['tab'], ['f2'], ['escape']).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keys": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of key names to press together"
                            }
                        },
                        "required": ["keys"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_application",
                    "description": "Open or launch a desktop application (e.g. 'code', 'firefox', 'calc', 'excel', 'terminal', 'chrome').",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_name": {"type": "string", "description": "Name or binary of application"}
                        },
                        "required": ["app_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "close_application",
                    "description": "Close or terminate an application process by name.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_name": {"type": "string", "description": "Name of process to close"}
                        },
                        "required": ["app_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_shell",
                    "description": "Execute a Windows PowerShell or CMD shell command with full system access.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Shell command to run"}
                        },
                        "required": ["command"]
                    }
                }
            }
        ]
    
    def dispatch(self, name: str, args: Dict[str, Any]) -> str:
        logger.info(f"Dispatching tool: {name} with args {args}")
        try:
            if name == "task_completed":
                summary = args.get("summary", "Task completed and visually verified.")
                return f"TASK_COMPLETED: {summary}"
            
            elif name == "ask_user_voice":
                question = args.get("question", "Could you please clarify your request?")
                print(f"\n[Mid-Task Voice Request]: Neeron asks: '{question}'")
                if self.tts:
                    self.tts.speak(question)
                if self.stt:
                    print("[Voice Input]: Listening for your spoken answer...")
                    user_reply = self.stt.listen()
                    if user_reply:
                        print(f"[Voice Input Received]: '{user_reply}'")
                        return f"User spoken response: {user_reply}"
                    return "User did not provide a voice response."
                return f"Voice interaction unavailable. Question asked was: {question}"
            
            elif name == "open_browser":
                url = args.get("url", "")
                return self.system_controller.open_browser(url)
            
            elif name == "browser_click":
                query = args.get("query", "")
                return self.system_controller.browser_click(query)
            
            elif name == "browser_type":
                query = args.get("query", "")
                text = args.get("text", "")
                press_enter = bool(args.get("press_enter", True))
                return self.system_controller.browser_type(query, text, press_enter=press_enter)
            
            elif name == "browser_scroll":
                direction = args.get("direction", "down")
                return self.system_controller.browser_scroll(direction)
            
            elif name == "inspect_screen":
                screenshot = self.vision.capture_screenshot()
                if screenshot:
                    return f"Screen captured: {screenshot}"
                return "Failed to capture desktop screen"
            
            elif name == "gui_click":
                x = int(args.get("x", 0))
                y = int(args.get("y", 0))
                button = args.get("button", "left")
                clicks = int(args.get("clicks", 1))
                return self.gui.click(x, y, button=button, clicks=clicks)
            
            elif name == "gui_type":
                text = args.get("text", "")
                press_enter = bool(args.get("press_enter", True))
                return self.gui.type_text(text, press_enter=press_enter)
            
            elif name == "gui_hotkey":
                keys = args.get("keys", [])
                if isinstance(keys, str):
                    keys = [keys]
                return self.gui.press_hotkey(keys)
            
            elif name == "open_application":
                app_name = args.get("app_name", "")
                success, msg = self.app_manager.open_app(app_name)
                return msg
            
            elif name == "close_application":
                app_name = args.get("app_name", "")
                success, msg = self.app_manager.close_app(app_name)
                return msg
            
            elif name == "execute_shell":
                cmd = args.get("command", "")
                res = self.system_controller.execute_shell(cmd)
                return res.output if res.success else f"Error: {res.error}"
            
            else:
                return f"Unknown tool: {name}"
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            return f"Error executing tool {name}: {str(e)}"
