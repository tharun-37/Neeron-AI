#!/usr/bin/env python3
"""
Neeron AI - Autonomous Vision-Enabled Desktop Agent
Usage:
  python main.py        (Standard Terminal CLI Mode)
  python main.py --gui  (iOS 27 Dynamic Island Glass HUD Mode)
"""
import os
import sys
import warnings
from pathlib import Path

# Enforce UTF-8 console output encoding on Windows to prevent UnicodeEncodeError on emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Suppress HuggingFace Hub Windows symlink & unauthenticated warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore")

if __name__ == "__main__":
    config_path = "neeron_config.json"
    
    # Check CLI arguments for --gui / -gui mode
    use_gui = any(arg.lower() in ["--gui", "-gui", "gui"] for arg in sys.argv[1:])
    
    if use_gui:
        try:
            from neeron.ui.hud_widget import launch_gui_hud
            launch_gui_hud(config_path)
        except Exception as e:
            print(f"Error launching GUI HUD: {e}, falling back to terminal CLI mode...")
            from neeron.daemon import start_daemon
            start_daemon(config_path)
    else:
        from neeron.daemon import start_daemon
        start_daemon(config_path)
