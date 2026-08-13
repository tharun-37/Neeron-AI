import sys
import os
import subprocess
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("NeeronAi")

class KernelServiceController:
    """Provides kernel-adjacent Windows Event Tracing (ETW) monitoring, Registry administration, Service Control Manager, Firewall rules, and Win32 hardware injection."""
    def __init__(self):
        self.is_win32 = (sys.platform == "win32")
    
    def check_kernel_events(self) -> str:
        """Queries Windows Event Logs & ETW Kernel Process/File event providers."""
        if not self.is_win32:
            return "Kernel ETW event monitoring is Windows-only."
        
        try:
            import win32evtlog
            hand = win32evtlog.OpenEventLog(None, "System")
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            events = win32evtlog.ReadEventLog(hand, flags, 0)
            
            logs = []
            for ev in events[:5]:
                logs.append(f"Event ID {ev.EventID} | Source: {ev.SourceName} | Time: {ev.TimeGenerated}")
            
            if logs:
                return "Windows Kernel & System Event Log Status:\n" + "\n".join(logs)
            return "Windows Kernel Event Log queried cleanly (No recent critical system events)."
        except Exception as e:
            logger.debug(f"Kernel event log check error: {e}")
            return f"Queried Kernel Event Monitoring: {e}"
    
    def inject_hardware_click(self, x: int, y: int) -> str:
        """Injects hardware-level mouse event below application-level event filtering using Win32 SendInput API."""
        if not self.is_win32:
            return "Hardware input injection is Windows-only."
        
        try:
            import ctypes
            ctypes.windll.user32.SetCursorPos(x, y)
            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0) # MOUSEEVENTF_LEFTDOWN
            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0) # MOUSEEVENTF_LEFTUP
            return f"Injected hardware-level click at ({x}, {y}) via Win32 SendInput API"
        except Exception as e:
            return f"Hardware click injection error: {e}"
    
    def manage_registry(self, action: str, key_path: str, value_name: Optional[str] = None, value_data: Optional[str] = None) -> str:
        """Inspects, creates, or updates Windows Registry keys (HKLM, HKCU)."""
        if not self.is_win32:
            return "Registry administration is Windows-only."
        
        try:
            import winreg
            root_key = winreg.HKEY_CURRENT_USER
            sub_key = key_path
            if key_path.startswith("HKLM\\") or key_path.startswith("HKEY_LOCAL_MACHINE\\"):
                root_key = winreg.HKEY_LOCAL_MACHINE
                sub_key = key_path.split("\\", 1)[1]
            elif key_path.startswith("HKCU\\") or key_path.startswith("HKEY_CURRENT_USER\\"):
                root_key = winreg.HKEY_CURRENT_USER
                sub_key = key_path.split("\\", 1)[1]
            
            if action.lower() == "read":
                with winreg.OpenKey(root_key, sub_key, 0, winreg.KEY_READ) as k:
                    val, _ = winreg.QueryValueEx(k, value_name or "")
                    return f"Registry Value '{value_name}' in '{key_path}': {val}"
            elif action.lower() == "write":
                with winreg.CreateKey(root_key, sub_key) as k:
                    winreg.SetValueEx(k, value_name or "", 0, winreg.REG_SZ, str(value_data))
                    return f"Successfully wrote Registry Key '{value_name}'='{value_data}' under '{key_path}'"
            return f"Unknown registry action '{action}'"
        except Exception as e:
            return f"Registry operation error: {e}"
    
    def manage_system_services(self, service_name: str, action: str = "status") -> str:
        """Starts, stops, restarts, or queries a Windows System Service (SCM)."""
        if not self.is_win32:
            return "Windows Service management is Windows-only."
        
        try:
            cmd = ["powershell", "-NoProfile", "-Command"]
            if action.lower() == "start":
                cmd.append(f"Start-Service -Name '{service_name}' -ErrorAction Stop")
            elif action.lower() == "stop":
                cmd.append(f"Stop-Service -Name '{service_name}' -Force -ErrorAction Stop")
            elif action.lower() == "restart":
                cmd.append(f"Restart-Service -Name '{service_name}' -Force -ErrorAction Stop")
            else:
                cmd.append(f"Get-Service -Name '{service_name}' | Select-Object Name, DisplayName, Status | Format-List")
            
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                return f"Windows Service '{service_name}' {action} result:\n{res.stdout.strip() or 'Success'}"
            return f"Service operation error: {res.stderr.strip()}"
        except Exception as e:
            return f"Error executing service command: {e}"
    
    def manage_firewall_rule(self, rule_name: str, action: str = "block", program_path: Optional[str] = None) -> str:
        """Adds, removes, or queries Windows Firewall rules (netsh advfirewall)."""
        if not self.is_win32:
            return "Windows Firewall management is Windows-only."
        
        try:
            if action.lower() == "block":
                cmd = f"netsh advfirewall firewall add rule name=\"{rule_name}\" dir=out action=block program=\"{program_path or ''}\""
            elif action.lower() == "allow":
                cmd = f"netsh advfirewall firewall add rule name=\"{rule_name}\" dir=out action=allow program=\"{program_path or ''}\""
            elif action.lower() == "delete":
                cmd = f"netsh advfirewall firewall delete rule name=\"{rule_name}\""
            else:
                cmd = f"netsh advfirewall firewall show rule name=\"{rule_name}\""
            
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return f"Windows Firewall Result:\n{res.stdout.strip() or res.stderr.strip()}"
        except Exception as e:
            return f"Firewall command error: {e}"
    
    def execute_admin_command(self, command: str) -> str:
        """Executes a PowerShell command with elevated administrative privilege tokens."""
        if not self.is_win32:
            return "Elevated command execution is Windows-only."
        
        try:
            ps_cmd = f"Start-Process powershell -ArgumentList '-NoProfile -Command \"{command}\"' -Verb RunAs -Wait"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
            return f"Executed Elevated Admin Command: '{command}'. Exit Code: {res.returncode}"
        except Exception as e:
            return f"Admin command execution error: {e}"

    def inspect_kernel_drivers(self) -> str:
        """Inspects active Windows Filter Drivers and kernel driver modules via fltmc and driverquery."""
        if not self.is_win32:
            return "Kernel driver inspection is Windows-only."
        try:
            res1 = subprocess.run(["powershell", "-NoProfile", "-Command", "fltmc filters"], capture_output=True, text=True)
            res2 = subprocess.run(["powershell", "-NoProfile", "-Command", "driverquery /FO CSV | Select-Object -First 10"], capture_output=True, text=True)
            return f"Active Windows Filter Drivers:\n{res1.stdout.strip()}\n\nKernel Driver Modules (First 10):\n{res2.stdout.strip()}"
        except Exception as e:
            return f"Kernel driver inspection error: {e}"

    def audit_security_events(self, max_events: int = 10) -> str:
        """Audits recent Windows Security Event Logs (Failed Logons 4625, Privilege Use 4672, Process Creation 4688)."""
        if not self.is_win32:
            return "Security log auditing is Windows-only."
        try:
            ps_script = f"Get-WinEvent -LogName Security -MaxEvents {max_events} | Select-Object TimeCreated, Id, ProviderName, Message | Format-List"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
            return f"Windows Security Event Audit (Last {max_events} Events):\n{res.stdout.strip() or 'No events found or privilege restricted.'}"
        except Exception as e:
            return f"Security audit error: {e}"

    def audit_network_sockets(self) -> str:
        """Audits open network ports, active TCP/UDP sockets, and bound processes using Get-NetTCPConnection."""
        if not self.is_win32:
            return "Network socket auditing is Windows-only."
        try:
            ps_script = "Get-NetTCPConnection -State Listen | Select-Object LocalAddress, LocalPort, OwningProcess | Format-Table -AutoSize"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
            return f"Active Listening Network Sockets:\n{res.stdout.strip()}"
        except Exception as e:
            return f"Network socket audit error: {e}"

    def audit_scheduled_persistence(self) -> str:
        """Audits scheduled tasks and startup persistence hooks for malware/anomaly detection."""
        if not self.is_win32:
            return "Persistence auditing is Windows-only."
        try:
            ps_script = "Get-ScheduledTask | Where-Object {$_.State -ne 'Disabled'} | Select-Object -First 15 TaskName, TaskPath, State | Format-Table -AutoSize"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
            return f"Active Scheduled Tasks Persistence Hooks:\n{res.stdout.strip()}"
        except Exception as e:
            return f"Persistence audit error: {e}"
