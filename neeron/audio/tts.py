import os
import sys
import asyncio
import tempfile
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger("NeeronAi")

class TTSEngine:
    """High-quality Text-to-Speech engine supporting Microsoft Edge Neural Voice (edge-tts) with pyttsx3 fallback."""
    def __init__(self, voice: str = "en-US-ChristopherNeural"):
        self.voice = voice
        self.pyttsx_engine = None
        self._init_pyttsx()
    
    def _init_pyttsx(self):
        import pyttsx3
        if sys.platform == "win32":
            try:
                self.pyttsx_engine = pyttsx3.init('sapi5')
            except Exception:
                try:
                    self.pyttsx_engine = pyttsx3.init()
                except Exception as e:
                    logger.warning(f"pyttsx3 initialization failed: {e}")
        else:
            try:
                self.pyttsx_engine = pyttsx3.init()
            except Exception as e:
                logger.warning(f"pyttsx3 initialization failed: {e}")
        
        if self.pyttsx_engine:
            try:
                self.pyttsx_engine.setProperty('rate', 175)
                self.pyttsx_engine.setProperty('volume', 0.9)
            except Exception:
                pass
    
    def _speak_edge_tts(self, text: str) -> bool:
        try:
            import edge_tts
            tmp_mp3 = Path(tempfile.gettempdir()) / "neeron_voice.mp3"
            
            async def generate():
                communicate = edge_tts.Communicate(text, self.voice)
                await communicate.save(str(tmp_mp3))
            
            asyncio.run(generate())
            
            if tmp_mp3.exists():
                if sys.platform == "win32":
                    ps_cmd = (
                        f'$m = New-Object -ComObject MediaPlayer.MediaPlayer; '
                        f'$m.Open("{tmp_mp3.as_posix()}"); $m.Play(); '
                        f'Start-Sleep -Milliseconds 1200'
                    )
                    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
        except Exception as e:
            logger.debug(f"edge-tts playback error: {e}")
        return False
    
    def speak(self, text: str):
        logger.info(f"[Voice]: {text}")
        print(f"\nNeeronAi: {text}\n")
        
        success = False
        try:
            success = self._speak_edge_tts(text)
        except Exception:
            success = False
        
        if not success and self.pyttsx_engine:
            try:
                self.pyttsx_engine.say(text)
                self.pyttsx_engine.runAndWait()
            except Exception as e:
                logger.error(f"pyttsx3 TTS playback error: {e}")
