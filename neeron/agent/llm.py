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
    "You are Neeron, an autonomous vision-enabled desktop agent inspired by Agent-S running on Windows. "
    "You have full system-wide access to control the Windows desktop environment. "
    "You record the user's voice prompt ONCE, then enter an autonomous vision-action execution loop to perform desktop and GUI tasks. "
    "In each step of the loop, you receive a desktop screenshot of the current screen. "
    "You must inspect the screenshot, decide what GUI/system actions to take (open_application, gui_click, gui_type, gui_hotkey, execute_shell, open_browser), "
    "and once you verify from the screenshot or action output that the task is completed successfully, call the task_completed tool."
)

class OllamaAgent:
    """Vision-enabled Multimodal Agent executing an Autonomous Vision-Action Loop."""
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
        Executes an autonomous vision-action loop until the model completes the task and visually verifies it.
        Does NOT re-record audio during the execution loop.
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
        
        try:
            while step_count < self.config.max_agent_steps and not task_done:
                step_count += 1
                print(f"\n--- [Autonomous Loop Step {step_count}/{self.config.max_agent_steps}] ---")
                print(f"Thinking with Vision Model '{self.config.model}'...")
                
                if step_count == 1:
                    print(f"  [GPU] Offloading '{self.config.model}' layers to NVIDIA GPU VRAM (first run cold-start takes ~10-20s)...")
                
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
                        if func_name == "inspect_screen" and self.vision.latest_screenshot_path:
                            tool_msg["images"] = [self.vision.latest_screenshot_path]
                        self.conversation.history.append(tool_msg)
                        
                        if func_name == "task_completed":
                            task_done = True
                            final_summary = parsed_args.get("summary", tool_result)
                    
                    # Brief pause for GUI window updates if screenshot captured
                    time.sleep(0.5)
                
                else:
                    # No tool calls made; model provided final text output
                    response_text = msg.content or ""
                    self.conversation.add_assistant(response_text)
                    final_summary = response_text
                    task_done = True
        finally:
            # Delete temporary screenshots when model process finishes
            self.vision.cleanup()
        
        print("\n" + "=" * 80)
        print("AUTONOMOUS GUI EXECUTION FINISHED")
        print("=" * 80)
        if final_summary:
            print(f"Summary: {final_summary}")
            self.tts.speak(final_summary)
        else:
            self.tts.speak("Task execution finished.")
        print("=" * 80 + "\n")
        
        return final_summary
