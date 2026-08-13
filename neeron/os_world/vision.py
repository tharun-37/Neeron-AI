import os
import time
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("NeeronAi")

class ScreenPerception:
    """Screen capture and visual perception provider for multimodal LLMs supporting application-wise window cropping."""
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir()) / "neeron_vision"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.latest_screenshot_path: Optional[str] = None
    
    def capture_screenshot(self, app_title: Optional[str] = None, full_screen: bool = True) -> Optional[str]:
        """Captures full desktop screen or application window screenshot on-demand."""
        filename = f"screen_{int(time.time() * 1000)}.png"
        target_path = self.output_dir / filename
        
        # 1. Try application window cropping if explicitly requested and full_screen is False
        app_rect = None
        if not full_screen:
            try:
                import pygetwindow as gw
                win = None
                if app_title:
                    matches = gw.getWindowsWithTitle(app_title)
                    if matches:
                        win = matches[0]
                if not win:
                    win = gw.getActiveWindow()
                
                if win and win.width > 100 and win.height > 100:
                    app_rect = {
                        "left": max(0, int(win.left)),
                        "top": max(0, int(win.top)),
                        "width": int(win.width),
                        "height": int(win.height)
                    }
            except Exception as e:
                logger.debug(f"Window bounds detection error: {e}")
        
        # 2. Capture using PyAutoGUI desktop screenshot
        try:
            import pyautogui
            if app_rect:
                img = pyautogui.screenshot(region=(app_rect["left"], app_rect["top"], app_rect["width"], app_rect["height"]))
            else:
                img = pyautogui.screenshot()
            img.save(target_path)
            self.latest_screenshot_path = str(target_path)
            logger.info(f"Desktop screenshot captured via PyAutoGUI: {target_path}")
            return self.latest_screenshot_path
        except Exception as e:
            logger.warning(f"PyAutoGUI screenshot failed: {e}")
        
        # 3. Fallback to mss
        try:
            import mss
            from PIL import Image
            with mss.mss() as sct:
                monitor = app_rect if app_rect else sct.monitors[0]
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                img.save(target_path)
                self.latest_screenshot_path = str(target_path)
                logger.info(f"Full desktop screenshot captured via MSS: {target_path}")
                return self.latest_screenshot_path
        except Exception as e:
            logger.warning(f"MSS screenshot failed: {e}")
        
        # 4. Fallback to PIL ImageGrab
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(all_screens=False)
            if app_rect:
                left = app_rect["left"]
                top = app_rect["top"]
                right = left + app_rect["width"]
                bottom = top + app_rect["height"]
                img = img.crop((left, top, right, bottom))
            
            img.save(target_path)
            self.latest_screenshot_path = str(target_path)
            logger.info(f"Desktop screenshot captured via ImageGrab: {target_path}")
            return self.latest_screenshot_path
        except Exception as e:
            logger.warning(f"ImageGrab screenshot failed: {e}")
        
        logger.error("Failed to capture screen using any method")
        return None
    
    def cleanup(self):
        """Deletes all screenshot files when the application fully shuts down."""
        try:
            if self.output_dir.exists():
                for file in self.output_dir.glob("*.png"):
                    try:
                        file.unlink()
                        logger.info(f"Deleted session screenshot: {file}")
                    except Exception as e:
                        logger.warning(f"Could not delete screenshot {file}: {e}")
            self.latest_screenshot_path = None
        except Exception as e:
            logger.error(f"Vision cleanup error: {e}")
