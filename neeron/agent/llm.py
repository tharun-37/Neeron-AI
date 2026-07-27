import time
import json
import logging
from typing import Optional, Dict, Any, List

from neeron.config import NeeronConfig
from neeron.agent.conversation import ConversationManager
from neeron.agent.tools import AgentToolRegistry
from neeron.audio.tts import TTSEngine
from neeron.os_world.vision import ScreenPerception

logger = logging.getLogger("NeeronAi")

SYSTEM_PROMPT = (
    "You are Neeron, an autonomous vision-enabled desktop agent running on Windows. "
    "You have full system-wide access to control the Windows desktop environment. "
    "You record the user's voice prompt ONCE, then enter an autonomous vision-action execution loop to perform desktop and GUI tasks. "
    "For step 2 and upcoming steps, you will receive a 'continue' prompt to proceed with execution. "
    "MANDATORY SELENIUM BROWSER MODE: Whenever the user command or voice prompt mentions 'browser', 'chrome', 'firefox', or explicit web URLs/domains, you MUST operate strictly in Selenium Browser Mode (using 'open_browser', 'browser_click', 'browser_type', 'browser_scroll'). Do NOT trigger Selenium Mode for general local desktop searches. "
    "CRITICAL SECURITY & LOGIN RULE: Whenever a task involves logging into an account, entering user credentials/passwords, sign-in forms, authentication pages, or security-sensitive actions, you MUST call 'ask_user_voice' to speak to the user, ask for their explicit voice confirmation/credentials, and obtain their authorization before typing or submitting sensitive actions. "
    "If at any point you require user input, confirmation, or clarification to proceed, call 'ask_user_voice' to speak your question aloud and listen for their voice response mid-task. "
    "In each step, decide what GUI/system/browser actions to take (open_browser, browser_click, browser_type, browser_scroll, open_application, gui_click, gui_type, gui_hotkey, execute_shell, inspect_screen, ask_user_voice). "
    "When you have finished executing all steps of the user command successfully, you MUST call the 'task_completed' tool (or output 'STOP') to signal task completion and allow the system to listen for the next voice command."
)

class OllamaAgent:
    """Vision-enabled Multimodal Agent executing an Autonomous Vision-Action Loop with continue/stop control flow."""
    def __init__(self, config: NeeronConfig, tool_registry: AgentToolRegistry, tts: TTSEngine, vision: ScreenPerception):
        self.config = config
        self.tool_registry = tool_registry
        self.tts = tts
        self.vision = vision
        self.conversation = ConversationManager(
            max_history=config.max_history,
            system_prompt=SYSTEM_PROMPT
        )
        self.tools = self.tool_registry.get_tool_definitions()
    
    def process_request(self, prompt: str) -> Optional[str]:
        """
        Executes an autonomous vision-action loop until the model completes the task and sends a 'STOP' / task_completed signal.
        Audio recording is strictly paused during execution and resumes only after process_request finishes.
        """
        logger.info(f"Starting autonomous GUI execution for prompt: {prompt}")
        print(f"\n" + "=" * 80)
        print(f"User Command: '{prompt}'")
        print("Entering Autonomous GUI Execution Loop (Audio recording paused)...")
        print("=" * 80 + "\n")
        
        user_msg: Dict[str, Any] = {"role": "user", "content": prompt}
        self.conversation.history.append(user_msg)
        
        try:
            import ollama
        except ImportError:
            msg = "Ollama python package is not installed. Run: pip install ollama"
            logger.error(msg)
            print(msg)
            self.tts.speak(msg)
            return msg
        
        step_count = 0
        task_done = False
        final_summary = ""
        
        while step_count < self.config.max_agent_steps and not task_done:
                step_count += 1
                print(f"\n--- [Autonomous Loop Step {step_count}/{self.config.max_agent_steps}] ---")
                
                # Send 'continue' statement before second and upcoming step executions
                if step_count > 1:
                    print("Sending 'continue' prompt to model for upcoming step execution...")
                    self.conversation.add_user("continue")
                
                print(f"Thinking with Vision Model '{self.config.model}'...")
                
                if step_count == 1:
                    print(f"  [GPU] Offloading '{self.config.model}' layers to NVIDIA GPU VRAM...")
                
                try:
                    response = ollama.chat(
                        model=self.config.model,
                        messages=self.conversation.get_history(),
                        tools=self.tools if self.tools else None,
                        options={
                            "num_gpu": 99  # Force 100% layer offloading to GPU VRAM
                        }
                    )
                except Exception as e:
                    logger.error(f"Ollama chat error on step {step_count}: {e}")
                    print(f"Ollama execution error: {e}")
                    break
                
                msg = response.message
                
                # Check if model invoked tools
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    logger.info(f"Step {step_count}: Model requested {len(msg.tool_calls)} tool call(s)")
                    print(f"Executing {len(msg.tool_calls)} GUI action(s)...")
                    
                    self.conversation.add_assistant(msg.content or "", msg.tool_calls)
                    
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
                        if func_name in ["inspect_screen", "browser_click", "open_browser"]:
                            screenshot = self.vision.capture_screenshot()
                            if screenshot:
                                tool_msg["images"] = [screenshot]
                        self.conversation.history.append(tool_msg)
                        
                        if func_name == "task_completed":
                            task_done = True
                            final_summary = parsed_args.get("summary", tool_result)
                            print("  [Signal] Model called task_completed (STOP signal received).")
                    
                    time.sleep(0.5)
                
                else:
                    # No tool calls made; model provided text response
                    response_text = msg.content or ""
                    self.conversation.add_assistant(response_text)
                    final_summary = response_text
                    
                    if "STOP" in response_text.upper() or "COMPLETED" in response_text.upper():
                        print("  [Signal] STOP signal detected in model output.")
                        task_done = True
                    else:
                        task_done = True
        
        print("\n" + "=" * 80)
        print("AUTONOMOUS GUI EXECUTION FINISHED (STOP Signal Processed)")
        print("=" * 80)
        if final_summary:
            print(f"Summary: {final_summary}")
            self.tts.speak(final_summary)
        else:
            self.tts.speak("Task execution finished.")
        print("=" * 80 + "\n")
        
        return final_summary
