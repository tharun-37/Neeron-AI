import logging
import time
from typing import List, Dict, Any, Optional

logger = logging.getLogger("NeeronAi")

class UIAController:
    """Native Windows UI Automation (UIA) controller reading element trees, text values, and executing direct UIA clicks."""
    def __init__(self):
        self._uia = None
        self._init_uia()
    
    def _init_uia(self):
        try:
            import uiautomation as auto
            self._uia = auto
            try:
                auto.SetGlobalSearchTimeout(2.0)
            except AttributeError:
                pass
            logger.info("Windows UI Automation (UIA) engine initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize uiautomation engine: {e}")
    
    def inspect_active_window_elements(self, max_depth: int = 4) -> str:
        """Parses the native Windows UI Automation (UIA) tree of the currently focused active window."""
        if not self._uia:
            return "Windows UI Automation engine not available."
        
        try:
            focus_win = self._uia.GetForegroundControl()
            if not focus_win:
                return "No active foreground window detected."
            
            top_win = focus_win.GetTopLevelControl()
            win_title = top_win.Name or "Active Window"
            
            elements = []
            def walk(control, depth=0):
                if depth > max_depth:
                    return
                try:
                    name = control.Name
                    control_type = control.ControlTypeName
                    auto_id = control.AutomationId
                    rect = control.BoundingRectangle
                    
                    if name or auto_id or control_type in ["ButtonControl", "EditControl", "MenuItemControl", "CheckBoxControl", "ListItemControl"]:
                        elem_info = f"[{control_type}] Name: '{name}' | ID: '{auto_id}' | Bounds: ({rect.left}, {rect.top}, {rect.width()}, {rect.height()})"
                        elements.append(elem_info)
                    
                    for child in control.GetChildren():
                        walk(child, depth + 1)
                except Exception:
                    pass
            
            walk(top_win)
            
            if elements:
                result_str = f"Active Window: '{win_title}' (UIA Controls Found: {len(elements)})\n" + "\n".join(elements[:35])
                return result_str
            return f"Active Window: '{win_title}' (No interactive UIA elements parsed)"
        except Exception as e:
            logger.error(f"Error inspecting UIA tree: {e}")
            return f"Error reading UIA tree: {e}"
    
    def read_active_window_text(self) -> str:
        """Reads all text values, document bodies, and input field contents from the active window via UIA."""
        if not self._uia:
            return "Windows UI Automation engine not available."
        
        try:
            focus_win = self._uia.GetForegroundControl()
            if not focus_win:
                return "No active foreground window detected."
            
            top_win = focus_win.GetTopLevelControl()
            win_title = top_win.Name or "Active Window"
            
            text_lines = []
            def extract_text(control, depth=0):
                if depth > 6:
                    return
                try:
                    # Check ValuePattern or TextPattern
                    val = None
                    try:
                        val = control.GetValuePattern().Value
                    except Exception:
                        pass
                    
                    name = control.Name
                    if val and val.strip():
                        text_lines.append(f"Value ({control.ControlTypeName}): {val.strip()}")
                    elif name and name.strip() and control.ControlTypeName in ["TextControl", "EditControl", "DocumentControl", "TitleBarControl"]:
                        text_lines.append(f"{control.ControlTypeName}: {name.strip()}")
                    
                    for child in control.GetChildren():
                        extract_text(child, depth + 1)
                except Exception:
                    pass
            
            extract_text(top_win)
            
            if text_lines:
                unique_lines = list(dict.fromkeys(text_lines))
                return f"Window Text for '{win_title}':\n" + "\n".join(unique_lines[:40])
            return f"No text content found in active window '{win_title}'"
        except Exception as e:
            logger.error(f"Error reading window text via UIA: {e}")
            return f"Error reading window text: {e}"
    
    def click_uia_element(self, query: str) -> str:
        """Locates a control by Name or AutomationId in the active window and executes a native UIA click."""
        if not self._uia:
            return "Windows UI Automation engine not available."
        
        try:
            focus_win = self._uia.GetForegroundControl()
            if not focus_win:
                return "No active window found."
            
            top_win = focus_win.GetTopLevelControl()
            
            # Search for control by Name or AutomationId
            ctrl = top_win.Control(searchDepth=6, SubName=query)
            if not ctrl.Exists(maxSearchSeconds=1):
                ctrl = top_win.Control(searchDepth=6, AutomationId=query)
            
            if ctrl.Exists(maxSearchSeconds=1):
                try:
                    ctrl.GetInvokePattern().Invoke()
                    time.sleep(0.5)
                    return f"Invoked UIA control '{ctrl.Name}' (ID: '{ctrl.AutomationId}')"
                except Exception:
                    ctrl.Click()
                    time.sleep(0.5)
                    return f"Clicked UIA control '{ctrl.Name}' (ID: '{ctrl.AutomationId}')"
            
            return f"UIA control matching '{query}' not found in active window"
        except Exception as e:
            logger.error(f"Error clicking UIA element: {e}")
            return f"Error clicking UIA element '{query}': {e}"
