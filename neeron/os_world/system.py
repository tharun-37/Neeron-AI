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
    """System and environment execution controller supporting Windows PowerShell/CMD & Linux."""
    def __init__(self, temp_dir: Optional[Path] = None):
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.mkdtemp(prefix="neeron_"))
        self.validator = CommandValidator()
    
    def execute_shell(self, command: str) -> CommandResult:
        is_valid, reason = self.validator.validate(command)
        if not is_valid:
            logger.warning(f"Command rejected: {reason}")
            return CommandResult(success=False, output="", error=reason, command=command)
        
        logger.info(f"Executing command: {command} on {sys.platform}")
        start_time = time.time()
        
        try:
            if sys.platform == "win32":
                # Run via PowerShell on Windows for maximum flexibility
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
    
    def open_browser(self, url: str) -> str:
        """Opens a web URL across Windows and Linux."""
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        
        try:
            if sys.platform == "win32":
                os.startfile(url)
                return f"Opened web URL {url} in default Windows browser"
            else:
                subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Opened web URL {url} in system browser"
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")
            return f"Error opening URL {url}: {e}"
    
    def cleanup(self):
        pass
