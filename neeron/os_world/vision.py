import os
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("NeeronAi")

class ScreenPerception:
    """Screen capture and visual perception provider for multimodal LLMs."""
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir()) / "neeron_vision"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.latest_screenshot_path: Optional[str] = None
    
    def capture_screenshot(self) -> Optional[str]:
        """Captures desktop screen on-demand and saves PNG file for vision model input."""
        target_path = self.output_dir / "latest_screen.png"
        
        # 1. Try mss (fastest cross-platform screen capture)
        try:
            import mss
            from PIL import Image
            with mss.mss() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                img.save(target_path)
                self.latest_screenshot_path = str(target_path)
                logger.info(f"Screen captured via MSS: {target_path}")
                return self.latest_screenshot_path
        except Exception as e:
            logger.warning(f"MSS screenshot failed: {e}")
        
        # 2. Try PIL ImageGrab
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(all_screens=True)
            img.save(target_path)
            self.latest_screenshot_path = str(target_path)
            logger.info(f"Screen captured via ImageGrab: {target_path}")
            return self.latest_screenshot_path
        except Exception as e:
            logger.warning(f"ImageGrab screenshot failed: {e}")
        
        # 3. Try PyAutoGUI screenshot
        try:
            import pyautogui
            img = pyautogui.screenshot()
            img.save(target_path)
            self.latest_screenshot_path = str(target_path)
            logger.info(f"Screen captured via PyAutoGUI: {target_path}")
            return self.latest_screenshot_path
        except Exception as e:
            logger.warning(f"PyAutoGUI screenshot failed: {e}")
        
        logger.error("Failed to capture screen using any method")
        return None
    
    def cleanup(self):
        """Deletes all screenshot files generated during processing."""
        try:
            if self.output_dir.exists():
                for file in self.output_dir.glob("*.png"):
                    try:
                        file.unlink()
                        logger.info(f"Deleted screenshot: {file}")
                    except Exception as e:
                        logger.warning(f"Could not delete screenshot {file}: {e}")
            self.latest_screenshot_path = None
        except Exception as e:
            logger.error(f"Vision cleanup error: {e}")
