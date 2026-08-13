# 🏛️ Neeron AI - System Architecture & Kernel Capabilities

## 1. Overview & System Blueprint
Neeron AI is a vision-enabled autonomous personal operating assistant running natively on Windows OS. It integrates speech-to-text (Whisper CPU int8), multimodal LLM reasoning (Gemma 4 GPU), Win32 UI Automation, and an iOS 27-inspired Dynamic Island HUD.

---

## 2. Windows OS Subsystem Capabilities & API Layer

### 🖥️ Window Layout Snap & Multi-Monitor Tile Manager
- **API Engine**: `ctypes.windll.user32.SetWindowPos`, `ShowWindow`, `FindWindowW`, `GetSystemMetrics`.
- **Supported Actions**:
  - `snap_left`: Snaps active window to Left 50% split view.
  - `snap_right`: Snaps active window to Right 50% split view.
  - `snap_top`: Snaps active window to Top 50% split view.
  - `maximize` / `minimize`: Toggles window states.
  - `center`: Centers 70% scaled window workspace.

### 🎨 Windows Theme & Display Controller
- **Windows Registry API**: Direct modification of `HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize` (`AppsUseLightTheme`, `SystemUsesLightTheme`).
- **Brightness WMI API**: Display screen brightness adjustment via `(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness`.

### 🛡️ Kernel & Administrative Operations
- **Service Control Manager (SCM)**: Starts, stops, and queries administrative Windows Services (`manage_system_services`).
- **Windows Registry Manager**: Full read/write capability across `HKLM` and `HKCU` keys (`manage_registry`).
- **Windows Firewall Policy**: Adds/removes inbound and outbound firewall rules (`manage_firewall_rule`).
- **Elevated PowerShell Execution**: Bypasses restriction policies for elevated administrative script execution (`execute_admin_command`).
- **Virtual Desktop Controller**: Creates, switches, and overviews Windows Virtual Desktops (`manage_virtual_desktops`).

---

## 3. Implemented Kernel & Administrative Auditing Subsystems

1. **Kernel Driver & Filter Module Inspector (`inspect_kernel_drivers`)**:
   - Queries loaded Windows Filter Drivers (`fltmc filters`) and kernel driver modules (`driverquery /FO CSV`).
   - Used by Neeron AI to detect non-standard or third-party kernel driver hooks.

2. **Windows Security Event Log Auditor (`audit_security_events`)**:
   - Audits real-time Security Event Logs (`Get-WinEvent -LogName Security`).
   - Inspects failed logon attempts (Event ID 4625), privilege escalation (Event ID 4672), and new process creation (Event ID 4688).

3. **Active Network Socket & Port Auditor (`audit_network_sockets`)**:
   - Audits open listening network ports, TCP/UDP sockets, and bound process IDs using `Get-NetTCPConnection`.

4. **Task Scheduler & Persistence Monitor (`audit_scheduled_persistence`)**:
   - Scans active Windows Scheduled Tasks (`Get-ScheduledTask`) and startup persistence keys to enforce system hygiene and detect unauthorized startup entries.
