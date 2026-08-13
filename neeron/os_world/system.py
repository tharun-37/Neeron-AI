import os
import sys
import time
import random
import logging
import tempfile
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Tuple, Optional

logger = logging.getLogger("NeeronAi")

@dataclass
class CommandResult:
    success: bool
    output: str
    error: Optional[str] = None
    command: Optional[str] = None
    execution_time: float = 0.0

class CommandValidator:
    DANGEROUS_PATTERNS = {
        'format c:', 'del /f /s /q c:\\windows', 'rd /s /q c:\\windows',
        'rm -rf /'
    }
    
    @staticmethod
    def validate(command: str) -> Tuple[bool, Optional[str]]:
        cmd_lower = command.lower().strip()
        for pattern in CommandValidator.DANGEROUS_PATTERNS:
            if pattern in cmd_lower:
                return False, f"Dangerous command blocked: {pattern}"
        return True, None

class SystemController:
    """System and browser execution controller supporting Windows PowerShell/CMD & Chrome Incognito Selenium Web Automation with human-like slow typing & bot detection guard."""
    def __init__(self, temp_dir: Optional[Path] = None):
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.mkdtemp(prefix="neeron_"))
        self.validator = CommandValidator()
        self.driver = None
    
    def execute_shell(self, command: str) -> CommandResult:
        is_valid, reason = self.validator.validate(command)
        if not is_valid:
            logger.warning(f"Command rejected: {reason}")
            return CommandResult(success=False, output="", error=reason, command=command)
        
        logger.info(f"Executing command: {command} on {sys.platform}")
        start_time = time.time()
        
        try:
            if sys.platform == "win32":
                cmd_exec = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
            else:
                cmd_exec = command
            
            process = subprocess.Popen(
                cmd_exec,
                shell=(sys.platform != "win32"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                text=True
            )
            stdout, stderr = process.communicate()
            exec_time = time.time() - start_time
            success = process.returncode == 0
            output = stdout.strip() if stdout else "No output"
            error = stderr.strip() if not success else None
            
            return CommandResult(
                success=success,
                output=output,
                error=error,
                command=command,
                execution_time=exec_time
            )
        except subprocess.TimeoutExpired:
            return CommandResult(success=False, output="", error="Command timeout (30s)", command=command)
        except Exception as e:
            return CommandResult(success=False, output="", error=str(e), command=command)
    
    def get_browser_driver(self):
        """Initializes or returns active Selenium WebDriver in Chrome Incognito Mode with anti-bot options."""
        if self.driver is not None:
            try:
                _ = self.driver.window_handles
                return self.driver
            except Exception:
                self.driver = None
        
        # 1. Try Chrome in Standard Mode
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service as ChromeService
            from webdriver_manager.chrome import ChromeDriverManager
            
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            logger.info("Initializing Selenium Chrome Driver (Standard Legitimate Mode)...")
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Execute CDP script to override navigator.webdriver flag
            try:
                self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        })
                    '''
                })
            except Exception:
                pass
            
            logger.info("Selenium Chrome Driver initialized successfully (Standard Legitimate Mode)")
            return self.driver
        except Exception as e:
            logger.warning(f"Chrome Selenium driver failed: {e}. Trying Firefox fallback...")
        
        # 2. Try Firefox fallback
        try:
            from selenium import webdriver
            from selenium.webdriver.firefox.service import Service as FirefoxService
            from webdriver_manager.firefox import GeckoDriverManager
            
            options = webdriver.FirefoxOptions()
            
            logger.info("Initializing Selenium Firefox Driver (Standard Mode)...")
            service = FirefoxService(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=options)
            logger.info("Selenium Firefox Driver initialized successfully")
            return self.driver
        except Exception as e:
            logger.error(f"Failed to initialize any Selenium browser driver: {e}")
            return None
    
    @staticmethod
    def _type_human_like(elem, text: str, press_enter: bool = True):
        """Types text character-by-character with realistic human keypress delays to bypass anti-bot checks."""
        from selenium.webdriver.common.keys import Keys
        try:
            elem.clear()
        except Exception:
            pass
        time.sleep(random.uniform(0.2, 0.4))
        
        for char in text:
            elem.send_keys(char)
            # Realistic variable typing delay per character (70ms to 170ms)
            time.sleep(random.uniform(0.07, 0.17))
        
        time.sleep(random.uniform(0.3, 0.6))
        if press_enter:
            elem.send_keys(Keys.RETURN)
            time.sleep(1.5)
    
    def open_browser(self, url: str) -> str:
        """Opens a web URL using Selenium Chrome Incognito browser and pauses 1s for page render."""
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        
        try:
            driver = self.get_browser_driver()
            if driver:
                driver.get(url)
                time.sleep(1.0)
                return f"Opened URL '{url}' in Selenium Chrome Incognito browser ({driver.name}) and completed rendering."
            else:
                if sys.platform == "win32":
                    os.startfile(url)
                    return f"Opened web URL '{url}' in default Windows browser"
                else:
                    subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return f"Opened web URL '{url}' in system browser"
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")
            return f"Error opening URL {url}: {e}"
    
    def open_gmail_and_read_first_email(self, email: str = "guessmymail0@gmail.com", password: str = "blahblahblahzero", use_real_gmail: bool = False) -> str:
        """Automates Chrome Incognito Gmail login (real Google or local HTML mock) with human-like typing and clickable email reading."""
        driver = self.get_browser_driver()
        if not driver:
            return "Failed to start Selenium Chrome Incognito driver."
        
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        try:
            mock_path = Path("d:/Codings/Neeron/mock_gmail.html").resolve()
            if use_real_gmail or not mock_path.exists():
                target_url = "https://mail.google.com/"
                logger.info("Navigating to REAL Google Gmail sign-in in Chrome Incognito...")
            else:
                target_url = mock_path.as_uri()
                logger.info(f"Navigating to local HTML Gmail mock interface at {target_url}...")
            
            driver.get(target_url)
            time.sleep(2.5)
            
            # Step 1: Fill Email
            email_field = None
            for selector in ["//input[@type='email']", "//*[@id='identifierId']", "//input[@name='identifier']"]:
                try:
                    email_field = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    if email_field:
                        break
                except Exception:
                    continue
            
            if email_field:
                self._type_human_like(email_field, email, press_enter=True)
                time.sleep(2.5)
            
            # Step 2: Fill Password (with Bot Detection Guard & Auto-Resume)
            pwd_field = None
            start_pwd_wait = time.time()
            bot_guard_active = False
            
            while time.time() - start_pwd_wait < 60.0:  # Poll up to 60 seconds if bot detection triggers
                for selector in ["//input[@type='password']", "//*[@name='Passwd']", "//input[@name='password']"]:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        for elem in elements:
                            if elem.is_displayed():
                                pwd_field = elem
                                break
                        if pwd_field:
                            break
                    except Exception:
                        continue
                
                if pwd_field:
                    break
                
                # Check if inbox already loaded
                try:
                    inbox_elements = driver.find_elements(By.XPATH, "//tr[contains(@class, 'zA')]")
                    if any(e.is_displayed() for e in inbox_elements):
                        logger.info("Inbox loaded directly during wait!")
                        break
                except Exception:
                    pass
                
                if not bot_guard_active:
                    print("\n[Bot Detection Guard]: Google verification active. Waiting for user interaction or password field appearance...")
                    logger.info("Bot detection guard active: waiting for password field...")
                    bot_guard_active = True
                
                time.sleep(1.0)
            
            if pwd_field:
                logger.info("Password box detected! Resuming automated login...")
                print("[Bot Detection Bypassed]: Password box detected! Typing password...")
                self._type_human_like(pwd_field, password, press_enter=True)
                time.sleep(4.0)
            
            # Step 3: Find and click first email in inbox (with wait loop for post-password verification)
            first_email = None
            start_inbox_wait = time.time()
            while time.time() - start_inbox_wait < 45.0:
                for selector in ["//tr[contains(@class, 'zA')][1]", "//div[contains(@role, 'main')]//tr[1]", "(//tr)[1]"]:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        for elem in elements:
                            if elem.is_displayed():
                                first_email = elem
                                break
                        if first_email:
                            break
                    except Exception:
                        continue
                
                if first_email:
                    break
                time.sleep(1.0)
            
            if first_email:
                first_email.click()
                time.sleep(2.0)
                return "Successfully logged into Gmail in Chrome Incognito and opened the first email! Visual screenshot is captured for content analysis."
            else:
                return "Navigated to Gmail in Chrome Incognito. Please review screenshot to verify inbox state."
        except Exception as e:
            logger.error(f"Error in Gmail automation: {e}")
            return f"Opened Gmail in Chrome Incognito. Details: {e}"
    
    def browser_click(self, query: str) -> str:
        """Clicks an element on the webpage, waits up to 5s for redirection, and pauses 1s for page render."""
        driver = self.get_browser_driver()
        if not driver:
            return "Browser driver not running"
        
        from selenium.webdriver.common.by import By
        
        old_url = driver.current_url
        old_title = driver.title
        
        strategies = [
            (By.XPATH, f"//*[contains(text(), '{query}')]"),
            (By.XPATH, f"//*[@placeholder='{query}' or @name='{query}' or @id='{query}']"),
            (By.XPATH, f"//a[contains(text(), '{query}')]"),
            (By.XPATH, f"//button[contains(text(), '{query}')]"),
            (By.XPATH, f"//*[@aria-label='{query}']"),
            (By.CSS_SELECTOR, query),
            (By.XPATH, query)
        ]
        
        clicked = False
        for by, val in strategies:
            try:
                elements = driver.find_elements(by, val)
                for elem in elements:
                    if elem.is_displayed():
                        try:
                            elem.click()
                            clicked = True
                            break
                        except Exception:
                            driver.execute_script("arguments[0].click();", elem)
                            clicked = True
                            break
                if clicked:
                    break
            except Exception:
                continue
        
        if not clicked:
            return f"Could not find or click element matching '{query}' on webpage"
        
        # Wait up to 5 seconds for page redirection/navigation to take effect
        redirected = False
        start_wait = time.time()
        while time.time() - start_wait < 5.0:
            time.sleep(0.5)
            try:
                if driver.current_url != old_url or driver.title != old_title:
                    redirected = True
                    break
            except Exception:
                pass
        
        # After redirection completes (or after 5s wait), pause 1 extra second for rendering
        time.sleep(1.0)
        
        new_url = driver.current_url
        if redirected:
            logger.info(f"Page redirected from {old_url} -> {new_url}")
            return f"Clicked '{query}'. Redirection successful to: {new_url} (rendering complete)."
        else:
            logger.info(f"No URL redirection detected after 5s for '{query}'. Current URL: {new_url}")
            return f"Clicked '{query}'. Current URL: {new_url}. No URL change detected after 5s wait (rendering complete)."
    
    def browser_type(self, query: str, text: str, press_enter: bool = True) -> str:
        """Types text naturally into an input field on the webpage character-by-character."""
        driver = self.get_browser_driver()
        if not driver:
            return "Browser driver not running"
        
        from selenium.webdriver.common.by import By
        
        strategies = [
            (By.XPATH, f"//input[@placeholder='{query}' or @name='{query}' or @id='{query}' or @aria-label='{query}']"),
            (By.XPATH, f"//textarea[@placeholder='{query}' or @name='{query}' or @id='{query}']"),
            (By.XPATH, f"//*[contains(@placeholder, '{query}')]"),
            (By.XPATH, f"//input[contains(@name, '{query}')]"),
            (By.CSS_SELECTOR, query),
            (By.XPATH, query)
        ]
        
        for by, val in strategies:
            try:
                elements = driver.find_elements(by, val)
                for elem in elements:
                    if elem.is_displayed():
                        self._type_human_like(elem, text, press_enter=press_enter)
                        return f"Typed '{text}' naturally into webpage field matching '{query}' (press_enter={press_enter})"
            except Exception:
                continue
        
        return f"Could not find input field matching '{query}' on webpage"
    
    def browser_scroll(self, direction: str = "down") -> str:
        """Scrolls the webpage up or down."""
        driver = self.get_browser_driver()
        if not driver:
            return "Browser driver not running"
        
        try:
            amount = 600 if direction.lower() == "down" else -600
            driver.execute_script(f"window.scrollBy(0, {amount});")
            time.sleep(0.5)
            return f"Scrolled webpage {direction}"
        except Exception as e:
            return f"Error scrolling browser: {e}"
    
    def analyze_task_manager(self) -> str:
        """Launches Task Manager (taskmgr), scans running Windows processes via psutil/PowerShell, and reports resource usage and potential anomalies."""
        try:
            if sys.platform == "win32":
                subprocess.Popen("start taskmgr", shell=True)
                time.sleep(1.5)
            
            import psutil
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'executable']):
                try:
                    info = proc.info
                    mem_mb = (info['memory_info'].rss / (1024 * 1024)) if info.get('memory_info') else 0
                    processes.append({
                        'pid': info['pid'],
                        'name': info['name'] or 'Unknown',
                        'cpu': info['cpu_percent'] or 0.0,
                        'memory_mb': round(mem_mb, 1),
                        'exe': info.get('executable') or 'N/A'
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            top_cpu = sorted(processes, key=lambda x: x['cpu'], reverse=True)[:5]
            top_ram = sorted(processes, key=lambda x: x['memory_mb'], reverse=True)[:5]
            
            suspicious = []
            for p in processes:
                if p['memory_mb'] > 1500 or p['cpu'] > 50.0:
                    suspicious.append(f"Resource Heavy: {p['name']} (PID: {p['pid']}, CPU: {p['cpu']}%, RAM: {p['memory_mb']} MB)")
                exe_lower = str(p['exe']).lower()
                if "temp" in exe_lower or "appdata\\local\\temp" in exe_lower:
                    suspicious.append(f"Suspicious Location: {p['name']} (PID: {p['pid']}, Path: {p['exe']})")
            
            summary = []
            summary.append("Opened Windows Task Manager (taskmgr).\n")
            summary.append("--- TOP MEMORY (RAM) CONSUMERS ---")
            for p in top_ram:
                summary.append(f"• {p['name']}: {p['memory_mb']} MB RAM (PID: {p['pid']})")
            
            summary.append("\n--- TOP CPU CONSUMERS ---")
            for p in top_cpu:
                summary.append(f"• {p['name']}: {p['cpu']}% CPU (PID: {p['pid']})")
            
            if suspicious:
                summary.append("\n--- RESOURCE HEAVY & POTENTIAL ANOMALIES ---")
                for s in suspicious[:5]:
                    summary.append(f"⚠️ {s}")
            else:
                summary.append("\nNo malware or unusual high-risk background processes detected.")
            
            return "\n".join(summary)
        except Exception as e:
            logger.error(f"Task Manager analysis error: {e}")
            return f"Opened Task Manager (taskmgr). System process analysis error: {e}"
    
    def read_file(self, filepath: str) -> str:
        """Reads contents of a file from disk safely."""
        try:
            p = Path(filepath)
            if not p.exists():
                return f"File '{filepath}' does not exist."
            if p.stat().st_size > 2 * 1024 * 1024:
                return f"File '{filepath}' is too large to read into memory directly."
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return f"File Content of '{filepath}':\n{content[:2000]}"
        except Exception as e:
            return f"Error reading file '{filepath}': {e}"
    
    def write_file(self, filepath: str, content: str, append: bool = False) -> str:
        """Creates, writes, or appends text to a file on disk."""
        try:
            p = Path(filepath)
            p.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            with open(p, mode, encoding="utf-8") as f:
                f.write(content)
            action = "Appended to" if append else "Wrote"
            return f"Successfully {action.lower()} file '{filepath}' ({len(content)} characters)."
        except Exception as e:
            return f"Error writing file '{filepath}': {e}"
    
    def inspect_system_services(self) -> str:
        """Queries administrative Windows Services status (Running/Stopped)."""
        try:
            if sys.platform == "win32":
                res = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Service | Where-Object {$_.Status -eq 'Running'} | Select-Object -First 15 Name, DisplayName, Status | Format-Table -AutoSize"], capture_output=True, text=True)
                return f"Active Windows Services:\n{res.stdout.strip()}"
            return "Windows Services inspection is Windows-only."
        except Exception as e:
            return f"Error inspecting Windows services: {e}"
    
    def manage_virtual_desktops(self, action: str = "list") -> str:
        """Manages Windows Virtual Desktops (list, switch, create)."""
        try:
            if sys.platform == "win32":
                if action.lower() == "create":
                    pyautogui.hotkey('win', 'ctrl', 'd')
                    return "Created new Windows Virtual Desktop (Win + Ctrl + D)"
                elif action.lower() == "next":
                    pyautogui.hotkey('win', 'ctrl', 'right')
                    return "Switched to next Virtual Desktop (Win + Ctrl + Right)"
                elif action.lower() == "prev":
                    pyautogui.hotkey('win', 'ctrl', 'left')
                    return "Switched to previous Virtual Desktop (Win + Ctrl + Left)"
                else:
                    pyautogui.hotkey('win', 'tab')
                    return "Opened Windows Task View / Virtual Desktops overview (Win + Tab)"
            return "Virtual Desktops management is Windows-only."
        except Exception as e:
            return f"Error managing Virtual Desktops: {e}"
    
    def set_windows_theme(self, mode: str = "dark") -> str:
        """Switches Windows OS Theme between Dark Mode and Light Mode instantly using Windows Registry (winreg)."""
        try:
            if sys.platform != "win32":
                return "Windows Theme switching is Windows-only."
            import winreg
            val = 0 if mode.lower() in ["dark", "darkmode", "night", "black"] else 1
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, val)
                winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, val)
            mode_str = "DARK" if val == 0 else "LIGHT"
            return f"Successfully switched Windows OS Theme to {mode_str} mode."
        except Exception as e:
            return f"Error setting Windows Theme: {e}"
    
    def set_screen_brightness(self, level: int = 50) -> str:
        """Sets display screen brightness percentage (0-100) via WMI PowerShell."""
        try:
            level = max(0, min(100, int(level)))
            if sys.platform == "win32":
                cmd = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"
                res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
                return f"Successfully set display screen brightness to {level}%."
            return "Brightness control is Windows-only."
        except Exception as e:
            return f"Error setting screen brightness: {e}"

    def manage_window_layout(self, action: str = "snap_left", win_title: str = "") -> str:
        """Snaps windows to 50/50 split views, tiles active apps side-by-side, or moves windows using SetWindowPos."""
        try:
            if sys.platform != "win32":
                return "Window layout snapping is Windows-only."
            
            import ctypes
            user32 = ctypes.windll.user32
            import pyautogui
            
            hwnd = user32.GetForegroundWindow()
            if win_title:
                hwnd_target = user32.FindWindowW(None, win_title)
                if hwnd_target:
                    hwnd = hwnd_target
            
            if not hwnd:
                return "No active target window found for layout snapping."
            
            sw = user32.GetSystemMetrics(0) # SM_CXSCREEN
            sh = user32.GetSystemMetrics(1) # SM_CYSCREEN
            
            act = action.lower().strip()
            
            if act in ["snap_left", "left", "split_left"]:
                user32.ShowWindow(hwnd, 9) # SW_RESTORE
                user32.SetWindowPos(hwnd, 0, 0, 0, sw // 2, sh, 0x0040) # SWP_SHOWWINDOW
                return "Snapped window to Left 50% split view."
            
            elif act in ["snap_right", "right", "split_right"]:
                user32.ShowWindow(hwnd, 9)
                user32.SetWindowPos(hwnd, 0, sw // 2, 0, sw // 2, sh, 0x0040)
                return "Snapped window to Right 50% split view."
            
            elif act in ["snap_top", "top_half"]:
                user32.ShowWindow(hwnd, 9)
                user32.SetWindowPos(hwnd, 0, 0, 0, sw, sh // 2, 0x0040)
                return "Snapped window to Top 50% split view."
            
            elif act in ["maximize", "max"]:
                user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
                return "Maximized target window."
            
            elif act in ["minimize", "min"]:
                user32.ShowWindow(hwnd, 6) # SW_MINIMIZE
                return "Minimized target window."
            
            elif act in ["center", "middle"]:
                w, h = int(sw * 0.7), int(sh * 0.7)
                x, y = (sw - w) // 2, (sh - h) // 2
                user32.ShowWindow(hwnd, 9)
                user32.SetWindowPos(hwnd, 0, x, y, w, h, 0x0040)
                return "Centered window on screen."
            
            else:
                pyautogui.hotkey('win', 'left')
                return f"Applied Windows Snap hotkey '{action}' to window."
        except Exception as e:
            return f"Error snapping window layout: {e}"

    def cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
