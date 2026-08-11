import os
import time
import struct
import math
import logging
import warnings
import numpy as np

# Suppress HuggingFace Hub Windows symlink & unauthenticated warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")
from typing import Optional, Dict, Any

from neeron.config import NeeronConfig
from neeron.audio.visualizer import AudioVisualizer

logger = logging.getLogger("NeeronAi")

class AudioStream:
    def __init__(self, pa, config: Dict[str, Any]):
        self.pa = pa
        self.config = config
        self.stream = None
    
    def __enter__(self):
        self.stream = self.pa.open(**self.config)
        return self.stream
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error closing audio stream: {e}")

class STTEngine:
    """Handles speech recognition using Faster-Whisper explicitly configured for CPU."""
    _stt_model = None
    
    def __init__(self, config: NeeronConfig):
        self.config = config
        self.visualizer = AudioVisualizer(window_size=60)
        self.audio_config = None
        self.pa = None
        self._init_stt()
    
    def _init_stt(self):
        try:
            import pyaudio
            print("\nInitializing Speech-to-Text (Whisper on CPU)...")
            self.stt_model = self._get_whisper_cpu_model(self.config.whisper_compute)
            if not self.stt_model:
                logger.error("Whisper model failed to load")
                print("Whisper STT model failed to load.")
                return
            
            self.pa = self._get_pyaudio()
            self.audio_config = {
                'format': pyaudio.paInt16,
                'channels': 1,
                'rate': 16000,
                'frames_per_buffer': 1024
            }
            logger.info("STT initialized on CPU successfully")
            print("Audio engine ready (Whisper CPU) - listening for wake word\n")
        except ImportError as e:
            logger.error(f"Audio library missing: {e}")
            print(f"Audio library missing: {e}")
        except Exception as e:
            logger.error(f"STT init error: {e}")
            print(f"STT init error: {e}")
    
    @classmethod
    def _get_whisper_cpu_model(cls, compute_type: str = "int8"):
        """Loads Faster-Whisper explicitly on CPU to avoid GPU allocation errors."""
        if cls._stt_model is not None:
            return cls._stt_model
        
        try:
            from faster_whisper import WhisperModel
            print(f"  Loading Whisper 'base' model on CPU (compute_type: {compute_type})...")
            cls._stt_model = WhisperModel("base", device="cpu", compute_type=compute_type)
            print("  Whisper successfully loaded on CPU!")
            return cls._stt_model
        except Exception as e:
            logger.error(f"Failed to load Whisper on CPU: {e}")
            print(f"  Whisper CPU load error: {e}")
            return None
    
    @staticmethod
    def _get_pyaudio():
        import pyaudio
        if os.name == 'nt':
            return pyaudio.PyAudio()
        try:
            null_fd = os.open(os.devnull, os.O_RDWR)
            old_stderr = os.dup2(null_fd, 2)
            try:
                pa = pyaudio.PyAudio()
            finally:
                os.dup2(old_stderr, 2)
                os.close(null_fd)
            return pa
        except Exception:
            return pyaudio.PyAudio()
    
    def listen(self) -> Optional[str]:
        if not self.stt_model or not self.audio_config or not self.pa:
            logger.error("Audio engine not initialized")
            return None
        
        try:
            frames = []
            is_recording = False
            silence_chunks = 0
            max_silence = 20
            start_time = time.time()
            
            print("=" * 80)
            print(f"LISTENING FOR WAKE WORD: '{self.config.wake_word}'")
            print("=" * 80 + "\n")
            
            with AudioStream(self.pa, {**self.audio_config, 'input': True}) as stream:
                while time.time() - start_time < self.config.audio_timeout:
                    try:
                        data = stream.read(self.audio_config['frames_per_buffer'], exception_on_overflow=False)
                        energy = self._calculate_energy(data)
                        
                        self.visualizer.add_sample(energy)
                        waveform = self.visualizer.draw()
                        
                        status = "LISTENING" if not is_recording else "RECORDING"
                        print(f"\r{status}: {waveform}", end="", flush=True)
                        
                        if energy > self.config.audio_energy_threshold:
                            if not is_recording:
                                is_recording = True
                                silence_chunks = 0
                                print("")
                            frames.append(data)
                        elif is_recording:
                            silence_chunks += 1
                            frames.append(data)
                            if silence_chunks > max_silence:
                                print("\nRecording stopped (silence detected)")
                                break
                    except Exception as e:
                        logger.error(f"Audio read error: {e}")
                        break
            
            if not frames:
                print("\nNo audio captured")
                return None
            
            print("\nTranscribing audio on CPU...")
            audio_data = np.frombuffer(b''.join(frames), dtype=np.int16).astype(np.float32) / 32768.0
            
            segments, _ = self.stt_model.transcribe(
                audio_data,
                beam_size=1,
                language="en"
            )
            text = " ".join([s.text for s in segments]).strip().lower()
            
            if text:
                print(f"\nTranscribed: '{text}'")
                logger.info(f"Transcribed text: {text}")
                
                if "stop" in text:
                    print("User spoken STOP command detected!")
                    return "stop"
                
                if self.config.wake_word in text:
                    command = text.replace(self.config.wake_word, "").strip()
                    if command:
                        print(f"Wake word detected! Command: '{command}'")
                        return command
                    else:
                        print(f"Wake word detected, but no command provided.")
                        return None
                else:
                    print(f"Wake word '{self.config.wake_word}' not heard in '{text}'")
                    return None
            else:
                print("No speech detected.")
                return None
        except Exception as e:
            logger.error(f"Listen loop error: {e}")
            return None
    
    @staticmethod
    def _calculate_energy(data: bytes) -> float:
        count = len(data) / 2
        if count == 0:
            return 0.0
        fmt = f"{int(count)}h"
        shorts = struct.unpack(fmt, data)
        sum_squares = sum(s**2 for s in shorts)
        return math.sqrt(sum_squares / count)
