#!/usr/bin/env python3
"""
NeeronAi - Wrapper entry point delegating to modular neeron package.
Optimized for Windows with CPU Whisper STT and GPU Ollama LLM.
"""
import os
import warnings

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore")

from neeron.daemon import start_daemon

if __name__ == "__main__":
    start_daemon("neeron_config.json")
