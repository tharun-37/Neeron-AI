import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from neeron.os_world.app_manager import DesktopAppManager
from neeron.os_world.system import SystemController
from neeron.os_world.vision import ScreenPerception
from neeron.os_world.gui_controller import GUIController
from neeron.os_world.uia_controller import UIAController
from neeron.agent.memory_db import PersistentMemoryDB
from neeron.os_world.kernel_controller import KernelServiceController

logger = logging.getLogger("NeeronAi")

class AgentToolRegistry:
    """Tool definition registry and execution dispatcher including GUI, UIA, Memory, Kernel, Vision, Selenium, Voice Input, and Task Completion tools."""
    def __init__(self, app_manager: DesktopAppManager, system_controller: SystemController, vision: ScreenPerception, gui: GUIController, stt=None, tts=None, uia: Optional[UIAController] = None, memory_db: Optional[PersistentMemoryDB] = None, kernel: Optional[KernelServiceController] = None):
        self.app_manager = app_manager
        self.system_controller = system_controller
        self.vision = vision
        self.gui = gui
        self.stt = stt
        self.tts = tts
        self.uia = uia or UIAController()
        self.memory_db = memory_db or PersistentMemoryDB()
        self.kernel = kernel or KernelServiceController()
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "task_completed",
                    "description": "Call this tool when you have visually verified from the screenshot or window state that the requested task/GUI action is fully completed.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "Brief description of what was completed and verified."
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
                    "description": "Ask the user a clarification question or request voice input mid-task via TTS.",
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
                    "name": "store_memory",
                    "description": "Store a user fact, preference, habit, or instruction permanently in ChromaDB long-term memory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "memory_id": {"type": "string", "description": "Unique key identifier for memory"},
                            "text": {"type": "string", "description": "Text content or fact to store permanently"}
                        },
                        "required": ["memory_id", "text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_memory",
                    "description": "Query long-term vector memory (ChromaDB) for stored user facts, preferences, or past instructions.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query or topic to query memory for"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_kernel_events",
                    "description": "Query Windows Event Logs & ETW Kernel Process/File event providers for system audit status.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "inject_hardware_click",
                    "description": "Inject a hardware-level mouse click directly via Win32 SendInput API below application event filters.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer", "description": "X pixel coordinate"},
                            "y": {"type": "integer", "description": "Y pixel coordinate"}
                        },
                        "required": ["x", "y"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_registry",
                    "description": "Inspect, create, or update Windows Registry keys (HKLM, HKCU).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "description": "Action: 'read' or 'write'"},
                            "key_path": {"type": "string", "description": "Registry path (e.g. 'HKCU\\Software\\MyConfig')"},
                            "value_name": {"type": "string", "description": "Name of registry value"},
                            "value_data": {"type": "string", "description": "Data to write to registry value"}
                        },
                        "required": ["action", "key_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_system_services",
                    "description": "Start, stop, restart, or query Windows System Services (SCM).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "service_name": {"type": "string", "description": "Name of Windows system service"},
                            "action": {"type": "string", "description": "Action: 'status', 'start', 'stop', 'restart'", "default": "status"}
                        },
                        "required": ["service_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_firewall_rule",
                    "description": "Add, remove, or query Windows Firewall rules (netsh advfirewall).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "rule_name": {"type": "string", "description": "Name of firewall rule"},
                            "action": {"type": "string", "description": "Action: 'block', 'allow', 'delete', 'show'", "default": "block"},
                            "program_path": {"type": "string", "description": "Executable program path to apply rule to"}
                        },
                        "required": ["rule_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_admin_command",
                    "description": "Execute a PowerShell command with elevated administrative privilege tokens.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "PowerShell command to run as Administrator"}
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_task_manager",
                    "description": "Open Windows Task Manager (taskmgr), scan all active processes for CPU & Memory/RAM usage, and analyze for resource-heavy apps or potential malware.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read file text content from local disk safely.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Absolute or relative file path to read"}
                        },
                        "required": ["filepath"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Create, write, or append text content to a local file on disk.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "File path on disk"},
                            "content": {"type": "string", "description": "Text content to write"},
                            "append": {"type": "boolean", "description": "Whether to append instead of overwrite", "default": False}
                        },
                        "required": ["filepath", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "inspect_system_services",
                    "description": "Query running administrative Windows Services and system status.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_virtual_desktops",
                    "description": "Manage Windows Virtual Desktops (action: 'list', 'create', 'next', 'prev').",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "description": "Virtual desktop action: 'list', 'create', 'next', 'prev'", "default": "list"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "inspect_uia_tree",
                    "description": "Parse the native Windows UI Automation (UIA) accessibility control tree of the active window to get exact button names, text fields, control types, AutomationIds, and bounding rectangles.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_window_text",
                    "description": "Read all document text content, input field values, and text controls directly from the active window using native Windows UI Automation API.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "click_uia_element",
                    "description": "Click or invoke a GUI button/control in the active window by its exact Windows UIA Name or AutomationId.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Name or AutomationId of the Windows control to click"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_gmail_and_read_first_email",
                    "description": "Open Chrome in Incognito mode, go to Gmail, sign in with email 'guessmymail0@gmail.com' and password 'blahblahblahzero', open the first email in the inbox, and inspect screenshot content.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string", "description": "Email address", "default": "guessmymail0@gmail.com"},
                            "password": {"type": "string", "description": "Password", "default": "blahblahblahzero"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_browser",
                    "description": "Open a website URL in Selenium Chrome Incognito browser.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to open (e.g. 'google.com', 'gmail.com')"}
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
                    "description": "Open or launch a desktop application (e.g. 'notepad', 'code', 'chrome', 'calc', 'excel', 'terminal').",
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
                summary = args.get("summary", "Task completed and verified.")
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
            
            elif name == "store_memory":
                mem_id = args.get("memory_id", "fact_1")
                text = args.get("text", "")
                return self.memory_db.store_memory(mem_id, text)
            
            elif name == "query_memory":
                query = args.get("query", "")
                return self.memory_db.query_memory(query)
            
            elif name == "check_kernel_events":
                return self.kernel.check_kernel_events()
            
            elif name == "inject_hardware_click":
                x = int(args.get("x", 0))
                y = int(args.get("y", 0))
                return self.kernel.inject_hardware_click(x, y)
            
            elif name == "manage_registry":
                action = args.get("action", "read")
                key_path = args.get("key_path", "")
                val_name = args.get("value_name", None)
                val_data = args.get("value_data", None)
                return self.kernel.manage_registry(action, key_path, value_name=val_name, value_data=val_data)
            
            elif name == "manage_system_services":
                service_name = args.get("service_name", "")
                action = args.get("action", "status")
                return self.kernel.manage_system_services(service_name, action=action)
            
            elif name == "manage_firewall_rule":
                rule_name = args.get("rule_name", "")
                action = args.get("action", "block")
                prog_path = args.get("program_path", None)
                return self.kernel.manage_firewall_rule(rule_name, action=action, program_path=prog_path)
            
            elif name == "execute_admin_command":
                cmd = args.get("command", "")
                return self.kernel.execute_admin_command(cmd)
            
            elif name == "inspect_uia_tree":
                return self.uia.inspect_active_window_elements()
            
            elif name == "read_window_text":
                return self.uia.read_active_window_text()
            
            elif name == "click_uia_element":
                query = args.get("query", "")
                return self.uia.click_uia_element(query)
            
            elif name == "open_gmail_and_read_first_email":
                email = args.get("email", "guessmymail0@gmail.com")
                password = args.get("password", "blahblahblahzero")
                use_real = bool(args.get("use_real_gmail", False))
                return self.system_controller.open_gmail_and_read_first_email(email=email, password=password, use_real_gmail=use_real)
            
            elif name == "open_browser":
                url = args.get("url", "")
                if not url:
                    url = "https://www.google.com"
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
                if "task" in app_name.lower() or "taskmgr" in app_name.lower():
                    return self.system_controller.analyze_task_manager()
                elif "chrome" in app_name.lower() or "browser" in app_name.lower():
                    return self.system_controller.open_browser("https://www.google.com")
                success, msg = self.app_manager.open_app(app_name)
                return msg
            
            elif name == "analyze_task_manager":
                return self.system_controller.analyze_task_manager()
            
            elif name == "close_application":
                app_name = args.get("app_name", "")
                success, msg = self.app_manager.close_app(app_name)
                return msg
            
            elif name == "read_file":
                filepath = args.get("filepath", "")
                return self.system_controller.read_file(filepath)
            
            elif name == "write_file":
                filepath = args.get("filepath", "")
                content = args.get("content", "")
                append = bool(args.get("append", False))
                return self.system_controller.write_file(filepath, content, append=append)
            
            elif name == "inspect_system_services":
                return self.system_controller.inspect_system_services()
            
            elif name == "manage_virtual_desktops":
                action = args.get("action", "list")
                return self.system_controller.manage_virtual_desktops(action)
            
            elif name == "execute_shell":
                cmd = args.get("command", "")
                res = self.system_controller.execute_shell(cmd)
                return res.output if res.success else f"Error: {res.error}"
            
            else:
                return f"Unknown tool: {name}"
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            return f"Error executing tool {name}: {str(e)}"
