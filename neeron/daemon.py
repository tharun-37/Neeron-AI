import time
import logging
from pathlib import Path
from typing import Optional

from neeron.config import NeeronConfig
from neeron.audio.tts import TTSEngine
from neeron.audio.stt import STTEngine
from neeron.os_world.app_manager import DesktopAppManager
from neeron.os_world.system import SystemController
from neeron.os_world.vision import ScreenPerception
from neeron.os_world.gui_controller import GUIController
from neeron.agent.tools import AgentToolRegistry
from neeron.agent.llm import OllamaAgent

logger = logging.getLogger("NeeronAi")

class NeeronDaemon:
    """Main Neeron Daemon coordinating voice STT/TTS, vision screen perception, LLM reasoning, and GUI execution."""
    def __init__(self, config: Optional[NeeronConfig] = None):
        self.config = config or NeeronConfig()
        
        model_str = f"{self.config.model} (GPU)"
        url_str = str(self.config.ollama_url)
        wake_str = f"'{self.config.wake_word}'"
        
        print("\n┌─────────────────────────────────────────────────────────────┐")
        print("│  NEERON AI  ·  Autonomous Desktop Agent                     │")
        print("├─────────────────────────────────────────────────────────────┤")
        print(f"│  Model:      {model_str:<46} │")
        print(f"│  STT:        Whisper Base (CPU int8)                        │")
        print(f"│  Wake Word:  {wake_str:<46} │")
        print(f"│  Endpoint:   {url_str:<46} │")
        print("└─────────────────────────────────────────────────────────────┘\n")
        
        self.tts = TTSEngine()
        self.stt = STTEngine(self.config)
        self.app_manager = DesktopAppManager()
        self.system_controller = SystemController()
        self.vision = ScreenPerception()
        self.gui = GUIController()
        
        self.tool_registry = AgentToolRegistry(
            app_manager=self.app_manager,
            system_controller=self.system_controller,
            vision=self.vision,
            gui=self.gui,
            stt=self.stt,
            tts=self.tts
        )
        self.agent = OllamaAgent(
            config=self.config,
            tool_registry=self.tool_registry,
            tts=self.tts,
            vision=self.vision
        )
        
        logger.info("NeeronDaemon initialized with Vision & GUI control")
    
    def run_forever(self):
        try:
            while True:
                text = self.stt.listen()
                if text:
                    cmd_clean = text.strip().lower()
                    if cmd_clean in ["stop", "cancel", "halt"]:
                        self.tts.speak("Execution stopped.")
                        time.sleep(0.5)
                        continue
                    
                    self.agent.process_request(text)
                time.sleep(0.2)
        except KeyboardInterrupt:
            print("\nShutting down Neeron AI...")
        finally:
            self.shutdown()
    
    def shutdown(self):
        logger.info("Shutting down Neeron AI subsystems...")
        self.system_controller.cleanup()
        self.vision.cleanup()
        logger.info("Shutdown complete.")

def start_daemon(config_path: str = "neeron_config.json"):
    config = NeeronConfig.from_file(Path(config_path))
    daemon = NeeronDaemon(config)
    daemon.run_forever()

if __name__ == "__main__":
    start_daemon()
