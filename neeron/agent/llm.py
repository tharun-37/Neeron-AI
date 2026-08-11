import os
import json
import time
import logging
from typing import List, Dict, Any, Optional

import ollama
from neeron.config import NeeronConfig
from neeron.agent.conversation import ConversationManager
from neeron.agent.tools import AgentToolRegistry
from neeron.audio.tts import TTSEngine
from neeron.os_world.vision import ScreenPerception

logger = logging.getLogger("NeeronAi")

SYSTEM_PROMPT = (
    "You are Neeron, an autonomous vision-enabled desktop agent running on Windows OS.\n\n"
    "<ROLE>\n"
    "You have full system-wide administrative access to control the Windows desktop environment. "
    "Execute user commands directly, methodically, and safely based strictly on what the user asks.\n"
    "</ROLE>\n\n"
    "<PROBLEM_SOLVING_WORKFLOW>\n"
    "1. EXPLORATION: Use 'inspect_uia_tree' or 'read_window_text' to extract native window controls and text lines before taking actions.\n"
    "2. ANALYSIS: Choose the optimal UI automation tool, native UIA click, browser driver, or shell command.\n"
    "3. IMPLEMENTATION: Execute precise tool calls (open_application, click_uia_element, open_browser, browser_click, read_file, write_file).\n"
    "4. VERIFICATION: Inspect window text or attached screenshots to verify action completion before invoking 'task_completed'.\n"
    "</PROBLEM_SOLVING_WORKFLOW>\n\n"
    "<SPECIALIZED_TOOL_MAPPINGS>\n"
    "• CALCULATOR: To open Calculator, use 'open_application' with 'calc'. Click UIA buttons directly using 'click_uia_element' ('Zero'...'Nine', 'Plus', 'Minus', 'Multiply by', 'Divide by', 'Equals', 'Clear'). Read results via 'read_window_text'.\n"
    "• TASK MANAGER & ANOMALIES: Call 'analyze_task_manager' (or 'taskmgr') to scan RAM/CPU usage and flag resource-heavy or suspicious executables.\n"
    "• FILE SYSTEM & UTILITIES: Use 'read_file' to read files, 'write_file' to create/append files, 'inspect_system_services' for Windows services, and 'manage_virtual_desktops' to switch or create virtual desktops.\n"
    "• BROWSER AUTOMATION: Use 'open_browser' to open URLs, 'browser_click' for links/buttons, 'browser_type' for typing text, and 'browser_scroll' to scroll.\n"
    "• LONG-TERM MEMORY: Use 'store_memory' to permanently remember user facts/preferences, and 'query_memory' to retrieve past facts.\n"
    "</SPECIALIZED_TOOL_MAPPINGS>\n\n"
    "<TROUBLESHOOTING>\n"
    "• If a UI button click fails twice, switch to fuzzy string click or fallback to 'gui_click' / 'gui_hotkey'.\n"
    "• If clarification or user credentials are required, call 'ask_user_voice' to speak your prompt aloud and listen for spoken reply.\n"
    "</TROUBLESHOOTING>\n\n"
    "When the task is verified complete, call 'task_completed'."
)

class OllamaAgent:
    """Vision-enabled Multimodal Agent executing sequential multi-step tool calls dynamically until task completion."""
    def __init__(self, config: NeeronConfig, tool_registry: AgentToolRegistry, tts: TTSEngine, vision: ScreenPerception):
        self.config = config
        self.tool_registry = tool_registry
        self.tts = tts
        self.vision = vision
        self.conversation = ConversationManager(
            max_history=config.max_history,
            system_prompt=SYSTEM_PROMPT
        )
    
    def process_request(self, user_prompt: str):
        print(f"\nUser Command: '{user_prompt}'")
        print("Executing GUI Command (Audio recording paused)...")
        
        self.conversation.clean_invalid_images()
        self.conversation.add_user(user_prompt)
        
        step_count = 0
        task_done = False
        final_summary = ""
        
        while not task_done and step_count < self.config.max_agent_steps:
            step_count += 1
            print(f"\nThinking with Vision Model '{self.config.model}'...")
            print(f"  [GPU] Offloading '{self.config.model}' layers to NVIDIA GPU VRAM...")
            
            try:
                response = ollama.chat(
                    model=self.config.model,
                    messages=self.conversation.get_history(),
                    tools=self.tool_registry.get_tool_definitions(),
                    options={"num_gpu": 99}
                )
            except Exception as e:
                logger.error(f"Ollama chat error: {e}")
                print(f"Ollama execution error: {e}")
                break
            
            msg = response.message
            
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                print(f"Executing {len(msg.tool_calls)} GUI action(s)...")
                tool_calls_list = []
                for tc in msg.tool_calls:
                    raw_tc_args = tc.function.arguments
                    if isinstance(raw_tc_args, str):
                        try:
                            args_dict = json.loads(raw_tc_args)
                        except Exception:
                            args_dict = {}
                    else:
                        args_dict = raw_tc_args or {}
                    
                    tc_dict = {
                        "id": getattr(tc, 'id', tc.function.name),
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": args_dict
                        }
                    }
                    tool_calls_list.append(tc_dict)
                
                self.conversation.add_assistant(msg.content or "", tool_calls=tool_calls_list)
                
                for tool_call in msg.tool_calls:
                    func_name = tool_call.function.name
                    raw_args = tool_call.function.arguments
                    
                    if isinstance(raw_args, str):
                        try:
                            parsed_args = json.loads(raw_args)
                        except json.JSONDecodeError:
                            parsed_args = {}
                    else:
                        parsed_args = raw_args or {}
                    
                    print(f"  -> Action: {func_name}({parsed_args})")
                    tool_result = self.tool_registry.dispatch(func_name, parsed_args)
                    print(f"  <- Result: {tool_result}")
                    
                    tool_id = getattr(tool_call, 'id', func_name)
                    tool_msg = {"role": "tool", "tool_call_id": tool_id, "content": str(tool_result)}
                    self.conversation.history.append(tool_msg)
                    
                    if func_name not in ["task_completed", "ask_user_voice"]:
                        time.sleep(0.5)
                        screenshot = self.vision.capture_screenshot()
                        if screenshot:
                            user_img_msg = {
                                "role": "user",
                                "content": "Current application screen state after action:",
                                "images": [screenshot]
                            }
                            self.conversation.history.append(user_img_msg)
                    
                    if func_name == "task_completed":
                        task_done = True
                        final_summary = parsed_args.get("summary", tool_result)
                        break
                
                time.sleep(0.5)
            else:
                final_summary = msg.content or "Task completed."
                self.conversation.add_assistant(final_summary)
                task_done = True
        
        print("\n" + "=" * 80)
        print("GUI EXECUTION FINISHED")
        print("=" * 80)
        if final_summary:
            print(f"Summary: {final_summary}")
            self.tts.speak(final_summary)
        else:
            self.tts.speak("Task execution finished.")
        print("=" * 80 + "\n")
