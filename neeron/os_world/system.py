import os
import sys
import time
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
    """System and browser execution controller supporting Windows PowerShell/CMD & Firefox/Chrome Selenium Web Automation."""
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
        """Initializes or returns active Selenium WebDriver (Firefox default, Chrome fallback)."""
        if self.driver is not None:
            try:
                _ = self.driver.window_handles
                return self.driver
            except Exception:
                self.driver = None
        
        # 1. Try Firefox (GeckoDriver)
        try:
            from selenium import webdriver
            from selenium.webdriver.firefox.service import Service as FirefoxService
            from webdriver_manager.firefox import GeckoDriverManager
            
            options = webdriver.FirefoxOptions()
            options.add_argument("--width=1280")
            options.add_argument("--height=800")
            
            logger.info("Initializing Selenium Firefox Driver...")
            service = FirefoxService(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=options)
            logger.info("Selenium Firefox Driver initialized successfully")
            return self.driver
        except Exception as e:
            logger.warning(f"Firefox Selenium driver failed: {e}. Trying Chrome fallback...")
        
        # 2. Try Chrome fallback
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service as ChromeService
            from webdriver_manager.chrome import ChromeDriverManager
            
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            
            logger.info("Initializing Selenium Chrome Driver...")
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            logger.info("Selenium Chrome Driver initialized successfully")
            return self.driver
        except Exception as e:
            logger.error(f"Failed to initialize any Selenium browser driver: {e}")
            return None
    
    def open_browser(self, url: str) -> str:
        """Opens a web URL using Selenium Firefox / Chrome browser and pauses 1s for page render."""
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        
        try:
            driver = self.get_browser_driver()
            if driver:
                driver.get(url)
                time.sleep(1.0)
                return f"Opened URL '{url}' in Selenium browser ({driver.name}) and completed rendering."
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
        """Types text into an input field on the webpage by placeholder, name, ID, CSS, or XPath."""
        driver = self.get_browser_driver()
        if not driver:
            return "Browser driver not running"
        
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        
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
                        elem.clear()
                        elem.send_keys(text)
                        if press_enter:
                            elem.send_keys(Keys.RETURN)
                            time.sleep(1.0)
                        return f"Typed '{text}' into webpage field matching '{query}' (press_enter={press_enter})"
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
    
    def cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
