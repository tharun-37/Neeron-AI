import sys
import logging
from typing import Optional

logger = logging.getLogger("NeeronAi")

class TTSEngine:
    """Text-to-Speech engine supporting pyttsx3 with Windows SAPI5 driver fallback."""
    def __init__(self):
        self.engine = None
        self._init_tts()
    
    def _init_tts(self):
        import pyttsx3
        if sys.platform == "win32":
            try:
                self.engine = pyttsx3.init('sapi5')
            except Exception:
                try:
                    self.engine = pyttsx3.init()
                except Exception as e:
                    logger.warning(f"pyttsx3 initialization failed: {e}")
        else:
            try:
                self.engine = pyttsx3.init()
            except Exception as e:
                logger.warning(f"pyttsx3 initialization failed: {e}")
        
        if self.engine:
            try:
                self.engine.setProperty('rate', 175)
                self.engine.setProperty('volume', 0.9)
                logger.info("pyttsx3 TTS initialized successfully")
            except Exception as e:
                logger.warning(f"Could not set TTS properties: {e}")
    
    def speak(self, text: str):
        logger.info(f"[Voice]: {text}")
        print(f"\nNeeronAi: {text}\n")
        
        if self.engine:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                logger.error(f"TTS playback error: {e}")
