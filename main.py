#!/usr/bin/env python3
"""
Neeron AI - Entry point
"""
import os
import sys
import warnings
from pathlib import Path

# Suppress HuggingFace Hub Windows symlink & unauthenticated warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore")

from neeron.daemon import start_daemon

if __name__ == "__main__":
    config_path = "neeron_config.json"
    start_daemon(config_path)
