import sys
import time
import ctypes
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger("NeeronAi")

class GUIController:
    """Agent-S style GUI mouse, keyboard, and window automation controller optimized for Windows."""
    def __init__(self):
        self._init_dpi_awareness()
        self._init_pyautogui()
    
    def _init_dpi_awareness(self):
        if sys.platform == "win32":
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2) # Per-monitor DPI aware
                logger.info("Windows Per-Monitor DPI awareness enabled")
            except Exception:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                    logger.info("Windows Process DPI awareness enabled")
                except Exception as e:
                    logger.warning(f"Could not set DPI awareness: {e}")
    
    def _init_pyautogui(self):
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            pyautogui.PAUSE = 0.2
            logger.info("PyAutoGUI initialized for GUI automation")
        except ImportError:
            logger.warning("PyAutoGUI not installed - GUI mouse/keyboard control disabled")
    
    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> str:
        """Click mouse at screen coordinates (x, y)."""
        try:
            import pyautogui
            pyautogui.click(x=x, y=y, clicks=clicks, button=button)
            return f"Clicked {button} mouse button {clicks} time(s) at coordinates ({x}, {y})"
        except Exception as e:
            logger.error(f"GUI click error: {e}")
            return f"Failed to click at ({x}, {y}): {e}"
    
    def type_text(self, text: str, press_enter: bool = True) -> str:
        """Type text into currently active window/field."""
        try:
            import pyautogui
            pyautogui.write(text, interval=0.03)
            if press_enter:
                pyautogui.press('enter')
            return f"Typed text '{text}' into focused window (press_enter={press_enter})"
        except Exception as e:
            logger.error(f"GUI type_text error: {e}")
            return f"Failed to type text: {e}"
    
    def press_hotkey(self, keys: List[str]) -> str:
        """Press hotkey combination or key sequence (e.g. ['ctrl', 's'], ['alt', 'tab'], ['enter'], ['f2'])."""
        try:
            import pyautogui
            if not keys:
                return "No keys provided"
            
            clean_keys = [str(k).lower().strip() for k in keys]
            if len(clean_keys) == 1:
                pyautogui.press(clean_keys[0])
            else:
                pyautogui.hotkey(*clean_keys)
            return f"Pressed key combination: {clean_keys}"
        except Exception as e:
            logger.error(f"GUI press_hotkey error: {e}")
            return f"Failed to press keys {keys}: {e}"
    
    def scroll(self, amount: int, x: Optional[int] = None, y: Optional[int] = None) -> str:
        """Scroll mouse wheel up (positive) or down (negative)."""
        try:
            import pyautogui
            if x is not None and y is not None:
                pyautogui.moveTo(x, y)
            pyautogui.scroll(amount)
            return f"Scrolled mouse wheel by {amount}"
        except Exception as e:
            logger.error(f"GUI scroll error: {e}")
            return f"Failed to scroll: {e}"
    
    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> str:
        """Drag mouse from (start_x, start_y) to (end_x, end_y)."""
        try:
            import pyautogui
            pyautogui.moveTo(start_x, start_y)
            pyautogui.dragTo(end_x, end_y, duration=0.8, button='left')
            return f"Dragged mouse from ({start_x}, {start_y}) to ({end_x}, {end_y})"
        except Exception as e:
            logger.error(f"GUI drag error: {e}")
            return f"Failed to drag mouse: {e}"
    
    def focus_window(self, title_query: str) -> str:
        """Finds and brings a window matching title_query into focus."""
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title_query)
            if windows:
                win = windows[0]
                if win.isMinimized:
                    win.restore()
                win.activate()
                return f"Focused window: '{win.title}'"
            return f"No window found matching '{title_query}'"
        except Exception as e:
            logger.error(f"focus_window error: {e}")
            return f"Could not focus window '{title_query}': {e}"
