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
    "You are a GUI-first automation agent with full system-wide administrative access to control the Windows desktop environment. "
    "You have real, working tools for: opening & closing any desktop applications ('open_application', 'close_application'), native Windows Settings ('open_application' with 'settings'), Windows Calculator ('open_application' with 'calc'), GUI mouse clicking ('gui_click', 'click_uia_element'), typing ('gui_type'), hotkeys ('gui_hotkey'), window snapping & layout ('manage_window_layout'), OS Theme & Brightness ('set_windows_theme', 'set_screen_brightness'), Selenium Chrome & DevTools Protocol ('open_browser', 'browser_click', 'execute_cdp_command', 'cdp_evaluate_js'), Task Manager process scanning ('analyze_task_manager'), Win32 Registry & Services ('manage_registry', 'manage_system_services', 'manage_firewall_rule'), Kernel Event Auditing ('inspect_kernel_drivers', 'audit_security_events', 'audit_network_sockets', 'audit_scheduled_persistence'), and Long-Term Vector Memory ('store_memory', 'query_memory').\n"
    "NEVER refuse user requests claiming you lack tools or capabilities. Call your available tools directly to complete the task.\n"
    "NEVER use emojis in any text output, voice responses, or summaries. Maintain a strictly professional, plain-text tone at all times.\n"
    "</ROLE>\n\n"
    "<PROBLEM_SOLVING_WORKFLOW>\n"
    "1. EXPLORATION: Inspect active screen context, attached screenshot, and UIA control tree to locate target UI elements.\n"
    "2. ANALYSIS: Identify exact application names, button labels, input fields, or pixel coordinates (x, y).\n"
    "3. IMPLEMENTATION: Execute precise tool calls: 'open_application' or 'close_application' for apps, 'click_uia_element' or 'gui_click(x, y)' to click, 'gui_type(text)' to type, and 'gui_hotkey(keys)' for key shortcuts.\n"
    "4. VERIFICATION: Inspect window text or updated screenshots to verify action completion before invoking 'task_completed'.\n"
    "</PROBLEM_SOLVING_WORKFLOW>\n\n"
    "<SPECIALIZED_TOOL_MAPPINGS>\n"
    "• OPENING & CLOSING APPS: Call 'open_application' to launch any app (e.g. 'calc', 'settings', 'chrome', 'notepad'). Call 'close_application' to terminate any app process (e.g. 'calculator', 'chrome', 'settings', 'notepad').\n"
    "• WINDOWS SETTINGS: Call 'open_application' with 'settings' to open official Windows Settings directly via 'ms-settings:'.\n"
    "• GUI CLICKING & TYPING: Use 'click_uia_element' to click named buttons/controls by UIA Name/ID. Use 'gui_click(x, y)' to click pixel coordinates directly on screen. Use 'gui_type(text)' to type into input fields, and 'gui_hotkey(keys)' for hotkeys (e.g. ['ctrl', 'c'], ['alt', 'tab'], ['enter']).\n"
    "• CALCULATOR: To open Calculator, call 'open_application' with 'calc'. Click buttons using 'click_uia_element' ('0'...'9', 'Plus', 'Minus', 'Multiply by', 'Divide by', 'Equals', 'Clear') or 'gui_click(x, y)'. Read output using 'read_window_text'. To close Calculator, call 'close_application' with 'calculator'.\n"
    "• WINDOW LAYOUT & OS CONTROLS: Use 'manage_window_layout' for window snapping (50/50 left/right split, maximize, minimize). Use 'set_windows_theme' ('dark'/'light') and 'set_screen_brightness' (0-100).\n"
    "• BROWSER & CHROME DEVTOOLS: Use 'open_browser' to open URLs, 'browser_click' for links/buttons, 'browser_type' for typing, 'execute_cdp_command' for raw CDP commands, and 'cdp_evaluate_js' for JavaScript evaluation.\n"
    "• KERNEL PROCESS AUDIT: For process and RAM/CPU analysis, rely on kernel-level CIM queries ('audit_kernel_processes', 'audit_network_sockets', 'inspect_kernel_drivers', 'audit_security_events') rather than Task Manager, and provide a concise, high-level summary.\n"
    "• LONG-TERM MEMORY: Use 'store_memory' to remember user facts permanently, and 'query_memory' to retrieve past facts.\n"
    "</SPECIALIZED_TOOL_MAPPINGS>\n\n"
    "<TROUBLESHOOTING>\n"
    "• If a UI button click fails twice, switch to fuzzy string click or fallback to 'gui_click(x, y)' / 'inject_hardware_click(x, y)'.\n"
    "• If clarification or user input is needed, call 'ask_user_voice'.\n"
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
        user_prompt = str(user_prompt or "").strip().lstrip(",.?!;:_-'\" ").strip()
        if not user_prompt:
            return
        
        try:
            from neeron.ui.hud_widget import notify_hud
            notify_hud(f"Executing: {user_prompt[:30]}...", "executing")
        except Exception:
            pass
        
        try:
            from neeron.audio.stt import ANSILiveRenderer
            renderer = ANSILiveRenderer()
        except Exception:
            renderer = None
        
        self.conversation.clean_invalid_images()
        
        # Attach initial screen state perception (screenshot + active window UIA controls) for multimodal reasoning
        screenshot = self.vision.capture_screenshot()
        win_info = ""
        try:
            if hasattr(self.tool_registry, 'uia') and self.tool_registry.uia:
                win_info = self.tool_registry.uia.inspect_active_window_elements()
        except Exception:
            pass
        
        initial_content = user_prompt
        if win_info:
            initial_content = f"{user_prompt}\n\n[Active Window Context]:\n{win_info[:250]}"
            
        self.conversation.add_user(initial_content, images=[screenshot] if screenshot else [])
        
        step_count = 0
        task_done = False
        final_summary = ""
        
        while not task_done and step_count < self.config.max_agent_steps:
            step_count += 1
            if renderer:
                renderer.render([
                    f"● EXECUTING COMMAND: '{user_prompt}'",
                    f"  [AI Reasoning]: Thinking with {self.config.model} (GPU Step {step_count})..."
                ])
            
            try:
                response = ollama.chat(
                    model=self.config.model,
                    messages=self.conversation.get_history(),
                    tools=self.tool_registry.get_tool_definitions(),
                    options={"num_gpu": 99, "num_ctx": 16384}
                )
            except Exception as e:
                logger.error(f"Ollama chat error: {e}")
                if renderer:
                    renderer.clear()
                print(f"Ollama execution error: {e}")
                break
            
            msg = response.message
            
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                if renderer:
                    renderer.render([
                        f"● EXECUTING COMMAND: '{user_prompt}'",
                        f"  [GUI Action]: Executing {len(msg.tool_calls)} action(s)..."
                    ])
                
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
                
                self.conversation.add_assistant("", tool_calls=tool_calls_list)
                
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
                    
                    try:
                        from neeron.ui.hud_widget import notify_hud
                        action_title = func_name.replace("_", " ").title()
                        notify_hud(f"task: {action_title}", "executing")
                    except Exception:
                        pass
                    
                    tool_result = self.tool_registry.dispatch(func_name, parsed_args)
                    
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
        
        if renderer:
            renderer.clear()
        
        def _clean_spoken_text(text: str) -> str:
            if not text:
                return ""
            import re
            # Strip 4-byte Unicode emoji characters
            text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
            if "<channel|>" in text:
                text = text.split("<channel|>")[-1]
            lines = []
            for line in text.splitlines():
                line_str = line.strip()
                if line_str.startswith("Plan:") or line_str.startswith("Summary:") or line_str.startswith("The user is asking") or line_str.startswith("This does not require") or line_str.startswith("I should fulfill"):
                    continue
                lines.append(line)
            cleaned = " ".join(lines).strip()
            return cleaned if cleaned else text

        clean_text = _clean_spoken_text(final_summary)
        if clean_text:
            self.tts.speak(clean_text)
        else:
            self.tts.speak("Task execution finished.")
