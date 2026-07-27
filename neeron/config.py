import os
import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logging(log_file: str = "neeron_ai.log", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("NeeronAi")
    if logger.handlers:
        return logger
    logger.setLevel(level)
    fh = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    fh.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

logger = setup_logging()

@dataclass
class NeeronConfig:
    wake_word: str = "hi"           # Wake word
    model: str = "gemma4:e4b-it-qat"   # Vision + Text model
    ollama_url: str = "http://localhost:11434"
    audio_energy_threshold: int = 50
    audio_timeout: int = 25
    max_history: int = 50
    max_agent_steps: int = 10          # Max GUI steps
    log_level: str = "INFO"
    whisper_device: str = "cpu"        # Whisper explicitly on CPU
    whisper_compute: str = "int8"      # Int8 speed optimization
    ollama_device: str = "gpu"         # Ollama uses NVIDIA GPU in background
    cuda_device_id: int = 0            # NVIDIA GPU ID for Ollama while OS display runs on iGPU
    
    @classmethod
    def from_file(cls, path: Path):
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                    return cls(**data)
            except Exception as e:
                logger.warning(f"Failed to load config from {path}: {e}, using defaults")
        return cls()
    
    def save(self, path: Path):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                json.dump(asdict(self), f, indent=2)
            logger.info(f"Config saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save config to {path}: {e}")
