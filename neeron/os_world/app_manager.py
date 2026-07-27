import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("NeeronAi")

class DesktopAppManager:
    """
    Cross-platform Desktop Application Manager (Windows + Arch/Linux).
    Indexes applications from Windows Start Menu / Program Files & Linux .desktop paths.
    """
    LINUX_DESKTOP_DIRS = [
        Path("/usr/share/applications"),
        Path("/usr/local/share/applications"),
        Path(os.path.expanduser("~/.local/share/applications")),
        Path("/var/lib/flatpak/exports/share/applications"),
    ]
    
    WINDOWS_START_DIRS = [
        Path(os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs")) if sys.platform == "win32" else None,
        Path(os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs")) if sys.platform == "win32" else None,
        Path(r"C:\Program Files") if sys.platform == "win32" else None,
        Path(r"C:\Program Files (x86)") if sys.platform == "win32" else None,
    ]
    
    def __init__(self):
        self.app_registry: Dict[str, Dict[str, str]] = {}
        self.refresh_app_registry()
    
    def refresh_app_registry(self):
        """Scans system directories for application shortcuts and binaries."""
        self.app_registry.clear()
        
        if sys.platform == "win32":
            # Windows indexing
            for d in [p for p in self.WINDOWS_START_DIRS if p and p.exists()]:
                try:
                    for item in d.glob("**/*"):
                        if item.suffix.lower() in [".lnk", ".exe"]:
                            name = item.stem.lower()
                            self.app_registry[name] = {
                                "Name": item.stem,
                                "Path": str(item),
                                "Type": "windows"
                            }
                except Exception as e:
                    logger.debug(f"Error scanning Windows dir {d}: {e}")
        else:
            # Linux indexing
            for d in self.LINUX_DESKTOP_DIRS:
                if not d.exists():
                    continue
                for desktop_file in d.glob("*.desktop"):
                    try:
                        info = self._parse_desktop_file(desktop_file)
                        if info and info.get("Name"):
                            name_key = info["Name"].lower()
                            self.app_registry[name_key] = info
                            if info.get("ExecName"):
                                self.app_registry[info["ExecName"].lower()] = info
                    except Exception as e:
                        logger.debug(f"Failed to parse desktop file {desktop_file}: {e}")
        
        logger.info(f"Indexed {len(self.app_registry)} cross-platform application shortcuts ({sys.platform})")
    
    def _parse_desktop_file(self, filepath: Path) -> Optional[Dict[str, str]]:
        name = None
        exec_cmd = None
        no_display = False
        
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            in_desktop_entry = False
            for line in f:
                line = line.strip()
                if line == "[Desktop Entry]":
                    in_desktop_entry = True
                    continue
                elif line.startswith("[") and line.endswith("]"):
                    in_desktop_entry = False
                
                if in_desktop_entry:
                    if line.startswith("Name=") and not name:
                        name = line.split("=", 1)[1].strip()
                    elif line.startswith("Exec=") and not exec_cmd:
                        exec_raw = line.split("=", 1)[1].strip()
                        exec_cmd = " ".join([token for token in exec_raw.split() if not token.startswith("%")])
                    elif line.startswith("NoDisplay=true"):
                        no_display = True
        
        if no_display or not name or not exec_cmd:
            return None
        
        exec_name = exec_cmd.split()[0]
        return {
            "Name": name,
            "Exec": exec_cmd,
            "ExecName": Path(exec_name).name,
            "DesktopFile": filepath.name,
            "Path": str(filepath),
            "Type": "linux"
        }
    
    def list_apps(self, limit: int = 30) -> List[str]:
        names = sorted(list({info["Name"] for info in self.app_registry.values()}))
        return names[:limit]
    
    def find_app(self, query: str) -> Optional[Dict[str, str]]:
        query_lower = query.lower().strip()
        
        if query_lower in self.app_registry:
            return self.app_registry[query_lower]
        
        for key, info in self.app_registry.items():
            if query_lower in key or query_lower in info["Name"].lower():
                return info
        return None
    
    def open_app(self, app_name: str) -> Tuple[bool, str]:
        """Launches an application across Windows and Linux."""
        logger.info(f"Attempting to launch app: {app_name} on {sys.platform}")
        info = self.find_app(app_name)
        
        if sys.platform == "win32":
            # 1. Launch via Windows Start Menu shortcut or path
            if info and info.get("Path"):
                try:
                    os.startfile(info["Path"])
                    return True, f"Launched Windows app '{info['Name']}' via startfile"
                except Exception as e:
                    logger.warning(f"Windows startfile failed: {e}")
            
            # 2. Try 'start' shell command or binary search
            try:
                subprocess.Popen(f'start "" "{app_name}"', shell=True)
                return True, f"Launched '{app_name}' via Windows start command"
            except Exception as e:
                return False, f"Failed to open '{app_name}' on Windows: {e}"
        else:
            # Linux launch
            if info and info.get("Type") == "linux":
                desktop_file = info["DesktopFile"]
                for launcher in ["gtk-launch", "gio launch", "dex"]:
                    if shutil.which(launcher.split()[0]):
                        try:
                            cmd = f"{launcher} {desktop_file}"
                            subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            return True, f"Successfully launched {info['Name']} via {launcher}"
                        except Exception:
                            pass
                try:
                    subprocess.Popen(info["Exec"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True, f"Successfully launched {info['Name']} ({info['Exec']})"
                except Exception as e:
                    return False, f"Failed to execute command '{info['Exec']}': {e}"
            
            binary_path = shutil.which(app_name.lower())
            if binary_path:
                try:
                    subprocess.Popen([binary_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True, f"Launched binary '{app_name}' from {binary_path}"
                except Exception as e:
                    return False, f"Error launching binary {app_name}: {e}"
            
            try:
                subprocess.Popen(["xdg-open", app_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, f"Opened '{app_name}' via xdg-open"
            except Exception:
                pass
        
        return False, f"Application '{app_name}' not found on system."
    
    def close_app(self, app_name: str) -> Tuple[bool, str]:
        """Terminates process by name on Windows / Linux."""
        info = self.find_app(app_name)
        target = info["ExecName"] if info and info.get("ExecName") else app_name
        
        try:
            if sys.platform == "win32":
                res = subprocess.run(["taskkill", "/F", "/IM", f"{target}.exe"], capture_output=True, text=True)
                if res.returncode == 0:
                    return True, f"Terminated Windows process '{target}.exe'"
                return False, f"No process found for '{target}'"
            else:
                res = subprocess.run(["pkill", "-f", target], capture_output=True, text=True)
                if res.returncode == 0:
                    return True, f"Terminated process '{target}'"
                return False, f"No process found for '{target}'"
        except Exception as e:
            return False, f"Failed to close application '{app_name}': {e}"
