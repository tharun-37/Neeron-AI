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

## 3. Future Kernel & Security Expansion Pipeline

1. **Kernel Driver & Filter Module Audit**:
   - Query loaded kernel drivers via `driverquery` and `fltmc` filter driver inspection.
2. **Windows Security Event Log Auditor**:
   - Parse Security and System channels (`Get-WinEvent`) to detect unauthorized login attempts or process injection.
3. **Network Active Socket & Port Auditor**:
   - Inspect active TCP/UDP listeners and map process IDs using `Get-NetTCPConnection` / `netstat -ano`.
4. **Task Scheduler & Persistence Monitor**:
   - Audit WMI jobs and scheduled tasks (`schtasks`) to enforce system persistence hygiene.
