# 🤖 NEERON AI - MULTIMODAL VISION-ENABLED AUTONOMOUS DESKTOP AGENT

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Ollama Vision](https://img.shields.io/badge/Ollama-Gemma4_Vision-000000?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com/)
[![Windows UIA](https://img.shields.io/badge/OS-Windows_10%2F11_UIA-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://microsoft.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

Neeron AI is a **100% private, local, voice-activated multimodal desktop agent** designed for Windows. It operates with full system-wide access to control the Windows desktop environment using native UI Automation (UIA), Selenium browser control, Task Manager process analytics, persistent vector memory, and neural speech synthesis—all optimized to run reliably within a strict **8GB GPU VRAM hardware budget**.

---

## 📐 SYSTEM ARCHITECTURE

```
+-----------------------------------------------------------------------------------------------+
|                                     NEERON AI DATA PIPELINE                                   |
+-----------------------------------------------------------------------------------------------+
  
 1. SENSORY INPUT (AUDIO & VOICE)
    +-----------------------------------------------------------------------------------------+
    | PyAudio Microphones -> RMS Audio Visualizer -> Faster-Whisper (CPU) STT Transcriber     |
    | Features: Spoken 'STOP' Interrupt + Customizable Wake Word ("hello" / "buddy")           |
    +-----------------------------------------------+-----------------------------------------+
                                                    |
                                                    v (Text Command)
 2. REASONING & MEMORY CORE
    +-----------------------------------------------------------------------------------------+
    | Ollama Agent (Gemma4 Multimodal Vision Model on GPU VRAM)                               |
    | Integrated with ChromaDB Persistent Long-Term Vector Memory                             |
    +-----------------------------------------------+-----------------------------------------+
                                                    |
                                                    v (Tool Dispatch)
 3. OS & BROWSER EXECUTION ENGINE
    +-------------------+-------------------+-------------------+-----------------------------+
    | Windows UIA Tree  | Selenium Browser  | Task Manager      | Win32 Kernel & Hardware     |
    | Native Control    | Legitimate Mode   | Diagnostic Engine | ETW Event Log Auditor +     |
    | Parser & Clicker  | Human Slow Typing | RAM / CPU Scans   | SendInput Direct Clicks     |
    +-------------------+-------------------+-------------------+-----------------------------+
                                                    |
                                                    v (Feedback & Screenshots)
 4. PERCEPTION & VOICE FEEDBACK
    +-----------------------------------------------------------------------------------------+
    | Active Window Cropped Screenshot Perception -> Microsoft EdgeTTS Neural Speech Output   |
    +-----------------------------------------------------------------------------------------+
```

---

## 📁 REPOSITORY DIRECTORY & FILE HIERARCHY

```
Neeron/
├── main.py                       # Main application entry point initializing NeeronDaemon
├── neeron_config.json            # Configuration file for wake words, models, and logging
├── mock_gmail.html               # Offline HTML test bench for browser sign-in simulations
├── requirements.txt              # Project dependencies specification
└── neeron/
    ├── __init__.py               # Core package initializer
    ├── config.py                 # Dataclass configuration loader (NeeronConfig)
    ├── daemon.py                 # Main system orchestrator daemon (listening & execution loop)
    ├── audio/
    │   ├── __init__.py           # Audio package initializer
    │   ├── stt.py                # Faster-Whisper CPU Speech-to-Text transcriber & STTEngine
    │   ├── tts.py                # TTSEngine (EdgeTTS Microsoft Neural Voice + pyttsx3 fallback)
    │   └── visualizer.py         # Terminal real-time ASCII waveform visualizer (AudioVisualizer)
    ├── agent/
    │   ├── __init__.py           # Agent package initializer
    │   ├── llm.py                # OllamaAgent multimodal vision-action loop handler
    │   ├── conversation.py       # ConversationManager context history & image role sanitizer
    │   ├── memory_db.py          # PersistentMemoryDB (ChromaDB vector memory manager)
    │   └── tools.py              # AgentToolRegistry tool definitions & dispatch router
    └── os_world/
        ├── __init__.py           # OS World package initializer
        ├── system.py             # SystemController (PowerShell execution & Selenium Chrome)
        ├── uia_controller.py     # UIAController (Native Windows UI Automation API parser)
        ├── kernel_controller.py  # KernelServiceController (Win32 Event Log & SendInput clicks)
        ├── vision.py             # ScreenPerception (Active window screenshot cropper)
        ├── app_manager.py        # DesktopAppManager (Start Menu indexer & calc handler)
        └── gui_controller.py     # GUIController (PyAutoGUI mouse & keyboard fallback)
```

---

## 📦 LIBRARIES & TECHNOLOGY STACK

### 🎙️ Audio & Voice Engine
* **`faster-whisper`**: Ultra-fast local C++ Whisper implementation. Forced on CPU (`int8` compute) to save 100% GPU VRAM for the vision LLM.
* **`pyaudio`**: Cross-platform audio I/O library for real-time microphone stream recording.
* **`edge-tts`**: Microsoft Edge Neural Voice API producing human-quality speech output (`en-US-ChristopherNeural` male voice) with 0% VRAM cost.
* **`pyttsx3`**: Offline fallback text-to-speech engine using native Windows SAPI5 drivers.

### 🧠 Vision & Multimodal Reasoning Core
* **`ollama`**: Lightweight local LLM runner offloading `gemma4:e4b-it-qat` vision model to NVIDIA GPU VRAM.
* **`chromadb`**: Persistent open-source vector database storing facts, user preferences, and long-term context across restarts.
* **`pillow` (PIL)**: Python Imaging Library for screenshot processing, resizing, and window cropping.
* **`mss`**: Ultra-fast cross-platform screen capture library.
* **`opencv-python` (cv2)**: Computer vision utility library for image array transformations.

### 💻 Windows OS & UI Automation
* **`uiautomation`**: Python wrapper for Microsoft UI Automation API. Inspects active window control trees, names, AutomationIds, and edit boxes directly from the OS.
* **`pywin32`**: Win32 extensions providing access to Event Tracing for Windows (ETW), Event Logs, and `SendInput` hardware mouse event injection.
* **`psutil`**: Cross-platform process and system monitoring library querying real-time RAM megabytes and CPU percentage.
* **`pygetwindow`**: Active window geometry utility for application-wise screenshot cropping.
* **`pyautogui`**: GUI automation fallback for raw pixel clicking and key hotkey presses.

### 🌐 Web Browser Automation
* **`selenium`**: Browser automation framework operating Chrome in standard legitimate mode with CDP `navigator.webdriver` overrides and human-like typing delays (70ms–170ms).
* **`webdriver-manager`**: Automatic driver binary installer for Google Chrome and Firefox.

---

## 🛠️ COMPLETE TOOL DEFINITION MATRIX

| Tool Name | Category | Functional Description |
| :--- | :--- | :--- |
| **`task_completed`** | System | Signals task completion and logs final verification summary. |
| **`ask_user_voice`** | Interactive | Speaks a clarification prompt aloud via TTS and listens for user voice response mid-task. |
| **`store_memory`** | Memory | Stores a fact, preference, habit, or instruction permanently in ChromaDB vector memory. |
| **`query_memory`** | Memory | Queries vector memory for relevant stored facts or instructions. |
| **`check_kernel_events`**| Kernel | Queries Windows Event Logs & ETW kernel event providers for system auditing. |
| **`inject_hardware_click`**| Kernel | Injects hardware-level mouse click via Win32 `SendInput` API below application event filters. |
| **`analyze_task_manager`**| Diagnostics | Opens Task Manager (`taskmgr`), scans RAM/CPU usage, and flags suspicious executable paths. |
| **`inspect_uia_tree`**| UIA Control | Parses native Windows UIA accessibility control tree of active window. |
| **`read_window_text`** | UIA Control | Reads text content, input field values, and document bodies directly from active window. |
| **`click_uia_element`**| UIA Control | Clicks a GUI button/control natively by Name or AutomationId without pixel errors. |
| **`open_browser`** | Web | Opens requested webpage URL in Selenium Chrome browser. |
| **`browser_click`** | Web | Clicks link or button on active webpage by visible text, ID, or CSS selector. |
| **`browser_type`** | Web | Types text into webpage input fields with human-like typing speed delays. |
| **`browser_scroll`** | Web | Scrolls active webpage up or down. |
| **`open_application`** | Application | Launches desktop application (Notepad, Calculator, Chrome, Explorer). |
| **`close_application`**| Application | Closes application process by name. |
| **`execute_shell`** | System Shell | Executes Windows PowerShell or CMD shell command with safety validation. |
| **`inspect_screen`** | Vision | Captures current desktop screenshot for visual analysis. |
| **`gui_click`** | Fallback | Clicks mouse at explicit screen pixel coordinates (x, y). |
| **`gui_type`** | Fallback | Types text into currently focused window. |
| **`gui_hotkey`** | Fallback | Presses key combination (e.g. `['ctrl', 's']`, `['alt', 'tab']`). |

---

## ⚡ INSTALLATION & SETUP GUIDE

### Prerequisites
1. **Windows 10 / 11** OS.
2. **Python 3.10+** installed.
3. **Ollama** installed locally with `gemma4:e4b-it-qat` model downloaded:
   ```bash
   ollama pull gemma4:e4b-it-qat
   ```

### Quick Start Commands
```powershell
# 1. Clone Repository
git clone https://github.com/tharun-37/Neeron-AI.git
cd Neeron-AI

# 2. Create Virtual Environment
python -m venv venv
.\venv\Scripts\activate

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Launch Neeron AI
python main.py
```

---

## 🔒 HARDWARE OPTIMIZATION & COMPLIANCE

* **8GB VRAM Dual Allocation**: Forced Whisper STT on CPU and Ollama Gemma4 on NVIDIA GPU to prevent Out-Of-Memory (OOM) GPU crashes.
* **Ollama Tokenizer Compliance**: Formats screenshots into `role: "user"` message payloads and caps active image context to the **latest 2 screenshots**, eliminating HTTP 400 tokenization errors.
* **100% Offline & Private**: All audio, vision, and system data remain strictly on your local machine.

---

## 🌍 UN SUSTAINABLE DEVELOPMENT GOALS (SDGs) ALIGNMENT

* **SDG 9: Industry, Innovation, and Infrastructure (Target 9.5)**: Advances local edge computing and multimodal AI execution on standard consumer hardware.
* **SDG 10: Reduced Inequalities (Target 10.2)**: Serves as an assistive accessibility tool for individuals with motor or physical impairments by enabling hands-free computer control.
* **SDG 4: Quality Education (Target 4.4)**: Provides an open-source reference implementation for students learning computer vision, local LLMs, and OS automation.
* **SDG 12: Responsible Consumption and Production (Target 12.2)**: Reduces e-waste and energy consumption by running local AI efficiently on existing consumer PCs.

---

## 📄 LICENSE
Distributed under the **MIT License**. See `LICENSE` for details.
