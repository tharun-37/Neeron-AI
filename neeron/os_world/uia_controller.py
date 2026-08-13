import logging
import time
import difflib
from typing import List, Dict, Any, Optional

logger = logging.getLogger("NeeronAi")

class UIAController:
    """Native Windows UI Automation (UIA) controller with Fuzzy String Matching and Element Invocation."""
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
        """Locates a control by Name or AutomationId in active window with Fuzzy String Matching fallback."""
        if not self._uia:
            return "Windows UI Automation engine not available."
        
        try:
            focus_win = self._uia.GetForegroundControl()
            if not focus_win:
                return "No active window found."
            
            top_win = focus_win.GetTopLevelControl()
            
            def safe_click(c):
                try:
                    c.GetInvokePattern().Invoke()
                    return f"Invoked UIA control '{c.Name}'"
                except Exception:
                    try:
                        c.Click()
                        return f"Clicked UIA control '{c.Name}'"
                    except Exception:
                        try:
                            import ctypes
                            rect = c.BoundingRectangle
                            cx = (rect.left + rect.right) // 2
                            cy = (rect.top + rect.bottom) // 2
                            ctypes.windll.user32.SetCursorPos(cx, cy)
                            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0) # DOWN
                            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0) # UP
                            return f"Hardware clicked UIA control '{c.Name}' at center ({cx}, {cy})"
                        except Exception as ex:
                            return f"Failed to click UIA control '{c.Name}': {ex}"

            # Calculator button alias mapping (maps symbols, digits, and words to native Windows Calculator AutomationId / Name)
            calc_aliases = {
                "0": ["num0Button", "Zero", "0"],
                "1": ["num1Button", "One", "1"],
                "2": ["num2Button", "Two", "2"],
                "3": ["num3Button", "Three", "3"],
                "4": ["num4Button", "Four", "4"],
                "5": ["num5Button", "Five", "5"],
                "6": ["num6Button", "Six", "6"],
                "7": ["num7Button", "Seven", "7"],
                "8": ["num8Button", "Eight", "8"],
                "9": ["num9Button", "Nine", "9"],
                "+": ["plusButton", "Plus", "+", "Add"],
                "-": ["minusButton", "Minus", "-", "Subtract"],
                "*": ["multiplyButton", "Multiply by", "Multiply", "*", "Times"],
                "/": ["divideButton", "Divide by", "Divide", "/"],
                "=": ["equalButton", "Equals", "Equal", "="],
                "c": ["clearButton", "Clear", "C"],
                "ce": ["clearEntryButton", "Clear entry", "CE"],
            }
            
            q_norm = str(query).lower().strip()
            search_terms = [query]
            if q_norm in calc_aliases:
                search_terms = calc_aliases[q_norm] + search_terms
            
            # 1. Try Exact or Substring match
            for term in search_terms:
                ctrl = top_win.Control(searchDepth=6, SubName=term)
                if not ctrl.Exists(maxSearchSeconds=0.5):
                    ctrl = top_win.Control(searchDepth=6, AutomationId=term)
                
                if ctrl.Exists(maxSearchSeconds=0.5):
                    res = safe_click(ctrl)
                    time.sleep(0.3)
                    return res
            
            # 2. Fallback: Fuzzy String Matching using difflib across all window controls
            all_controls = []
            def gather_controls(control, depth=0):
                if depth > 5:
                    return
                try:
                    if control.Name and control.Name.strip():
                        all_controls.append((control.Name.strip(), control))
                    if control.AutomationId and control.AutomationId.strip():
                        all_controls.append((control.AutomationId.strip(), control))
                    for child in control.GetChildren():
                        gather_controls(child, depth + 1)
                except Exception:
                    pass
            
            gather_controls(top_win)
            
            if all_controls:
                name_map = {name: c for name, c in all_controls}
                matches = difflib.get_close_matches(query, name_map.keys(), n=1, cutoff=0.5)
                if matches:
                    best_match = matches[0]
                    matched_ctrl = name_map[best_match]
                    res = safe_click(matched_ctrl)
                    time.sleep(0.5)
                    return f"Fuzzy match ('{query}' -> '{best_match}'): {res}"
            
            return f"UIA control matching '{query}' not found in active window"
        except Exception as e:
            logger.error(f"Error clicking UIA element: {e}")
            return f"Error clicking UIA element '{query}': {e}"
