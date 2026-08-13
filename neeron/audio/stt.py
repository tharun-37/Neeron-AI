import os
import sys
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

class ANSILiveRenderer:
    """Live multi-line ANSI terminal dashboard renderer using Carriage Return (\\r), Line Erase (\\033[K), and Cursor Up (\\033[N A)."""
    def __init__(self):
        self.last_lines_count = 0
        if sys.platform == "win32":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                mode = ctypes.c_ulong()
                handle = kernel32.GetStdHandle(-11) # STD_OUTPUT_HANDLE
                kernel32.GetConsoleMode(handle, ctypes.byref(mode))
                kernel32.SetConsoleMode(handle, mode.value | 0x0004) # ENABLE_VIRTUAL_TERMINAL_PROCESSING
            except Exception:
                pass

    def render(self, lines: list):
        if self.last_lines_count > 0:
            sys.stdout.write(f"\033[{self.last_lines_count}A")
        for line in lines:
            sys.stdout.write(f"\r\033[K{line}\n")
        sys.stdout.flush()
        self.last_lines_count = len(lines)

    def clear(self):
        if self.last_lines_count > 0:
            sys.stdout.write(f"\033[{self.last_lines_count}A")
            for _ in range(self.last_lines_count):
                sys.stdout.write("\r\033[K\n")
            sys.stdout.write(f"\033[{self.last_lines_count}A")
            sys.stdout.flush()
            self.last_lines_count = 0

class STTEngine:
    """Handles speech recognition using Faster-Whisper explicitly configured for CPU."""
    _stt_model = None
    
    def __init__(self, config: NeeronConfig):
        self.config = config
        self.visualizer = AudioVisualizer(window_size=60)
        self.ansi_renderer = ANSILiveRenderer()
        self.audio_config = None
        self.pa = None
        self._init_stt()
    
    def _init_stt(self):
        try:
            import pyaudio
            sys.stdout.write("\r\033[K[INIT]: Loading Speech-to-Text (Whisper CPU)...")
            sys.stdout.flush()
            self.stt_model = self._get_whisper_cpu_model(self.config.whisper_compute)
            if not self.stt_model:
                logger.error("Whisper model failed to load")
                sys.stdout.write("\r\033[K[INIT ERROR]: Whisper STT model failed to load.\n")
                sys.stdout.flush()
                return
            
            self.pa = self._get_pyaudio()
            self.audio_config = {
                'format': pyaudio.paInt16,
                'channels': 1,
                'rate': 16000,
                'frames_per_buffer': 1024
            }
            logger.info("STT initialized on CPU successfully")
            sys.stdout.write("\r\033[K[READY]: Audio Engine Active\n")
            sys.stdout.flush()
        except ImportError as e:
            logger.error(f"Audio library missing: {e}")
            sys.stdout.write(f"\r\033[K[INIT ERROR]: Audio library missing: {e}\n")
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"STT init error: {e}")
            sys.stdout.write(f"\r\033[K[INIT ERROR]: STT init error: {e}\n")
            sys.stdout.flush()
    
    @classmethod
    def _get_whisper_cpu_model(cls, compute_type: str = "int8"):
        """Loads Faster-Whisper explicitly on CPU to avoid GPU allocation errors."""
        if cls._stt_model is not None:
            return cls._stt_model
        
        try:
            from faster_whisper import WhisperModel
            sys.stdout.write(f"\r\033[K[INIT]: Loading Whisper 'base' model on CPU ({compute_type})...")
            sys.stdout.flush()
            cls._stt_model = WhisperModel("base", device="cpu", compute_type=compute_type)
            sys.stdout.write("\r\033[K[INIT]: Whisper STT loaded successfully.")
            sys.stdout.flush()
            return cls._stt_model
        except Exception as e:
            logger.error(f"Failed to load Whisper on CPU: {e}")
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
            max_silence = int(0.4 * self.audio_config['rate'] / self.audio_config['frames_per_buffer'])
            start_time = time.time()
            
            try:
                from neeron.ui.hud_widget import notify_hud
                notify_hud(f"Listening for '{self.config.wake_word}'...", "info")
            except Exception:
                pass
            
            with AudioStream(self.pa, {**self.audio_config, 'input': True}) as stream:
                while time.time() - start_time < self.config.audio_timeout:
                    try:
                        data = stream.read(self.audio_config['frames_per_buffer'], exception_on_overflow=False)
                        energy = self._calculate_energy(data)
                        
                        self.visualizer.add_sample(energy)
                        waveform = self.visualizer.draw()
                        
                        status = "LISTENING" if not is_recording else "RECORDING"
                        
                        # Live multi-line ANSI terminal dashboard update
                        dashboard_lines = [
                            f"[ NEERON AI LIVE TERMINAL ]",
                            f"  Status:   {status} [wake word: '{self.config.wake_word}']",
                            f"  Audio:    {waveform}"
                        ]
                        self.ansi_renderer.render(dashboard_lines)
                        
                        if energy > self.config.audio_energy_threshold:
                            if not is_recording:
                                is_recording = True
                                silence_chunks = 0
                                try:
                                    from neeron.ui.hud_widget import notify_hud
                                    notify_hud("Recording speech...", "recording")
                                except Exception:
                                    pass
                            frames.append(data)
                        elif is_recording:
                            silence_chunks += 1
                            frames.append(data)
                            if silence_chunks >= max_silence:
                                break
                    except Exception as e:
                        logger.error(f"Audio read error: {e}")
                        break
            
            self.ansi_renderer.clear()
            
            if not frames:
                return None
            
            audio_data = np.frombuffer(b''.join(frames), dtype=np.int16).astype(np.float32) / 32768.0
            
            # Audio Buffer VAD Trimming: Strip leading & trailing silence padding before Whisper STT
            non_silent = np.where(np.abs(audio_data) > 0.015)[0]
            if len(non_silent) > 0:
                start_idx = max(0, non_silent[0] - 800)  # 50ms pre-padding margin
                end_idx = min(len(audio_data), non_silent[-1] + 800) # 50ms post-padding margin
                audio_data = audio_data[start_idx:end_idx]
            
            segments, _ = self.stt_model.transcribe(
                audio_data,
                beam_size=1,
                language="en"
            )
            text = " ".join([s.text for s in segments]).strip().lower()
            text = text.lstrip(",.?!;:_-'\" ").strip()
            
            if text:
                logger.info(f"Transcribed text: {text}")
                try:
                    from neeron.ui.hud_widget import notify_hud
                    notify_hud(f"Speech: '{text[:25]}'", "executing")
                except Exception:
                    pass
                
                if "stop" in text:
                    print("\n[USER VOICE STOP INTERRUPT]: Stop command detected!")
                    return "stop"
                
                if self.config.wake_word in text:
                    command = text.replace(self.config.wake_word, "").strip().lstrip(",.?!;:_-'\" ").strip()
                    if command:
                        return command
                    else:
                        return None
                else:
                    return None
            else:
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
