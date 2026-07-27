# Neeron AI - Autonomous Vision-Language Desktop Agent

Neeron AI is an autonomous, vision-enabled desktop agent designed for Windows. Inspired by Agent-S, Neeron AI operates via voice commands, captures real-time screen state, reasons using local multimodal LLMs via Ollama, and executes desktop actions autonomously.

## Key Features
- **Dual-GPU & CPU Optimization**: Runs Faster-Whisper STT on CPU (`int8`) to preserve GPU VRAM; offloads Ollama LLM 100% to dedicated NVIDIA GPU.
- **Autonomous Vision-Action Loop**: Single voice command prompt -> autonomous desktop perception, action execution, and screen verification loop.
- **Windows Full System Access**: Launches Windows Start Menu shortcuts, manages windows, and executes PowerShell / CMD commands.
- **Privacy-First & Local**: Local Speech Recognition, local Text-to-Speech (pyttsx3 / SAPI5), and local vision model inference via Ollama.

## Setup Instructions

### 1. Prerequisites
- Python 3.10+
- [Ollama for Windows](https://ollama.com/download)
- Pull a vision model in Ollama:
  ```powershell
  ollama pull gemma4:e4b-it-qat
  ```

### 2. Installation
Create and activate virtual environment:
```powershell
python -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
```

### 3. Running Neeron AI
```powershell
.\venv\Scripts\python.exe main.py
```

## Architecture
- `main.py` / `NeeronAi.py`: Application entry points.
- `neeron/config.py`: Configuration settings.
- `neeron/agent/llm.py`: Vision-action loop orchestrator.
- `neeron/agent/tools.py`: Tool registry and dispatch.
- `neeron/audio/stt.py`: CPU Faster-Whisper speech recognition.
- `neeron/audio/tts.py`: pyttsx3 voice output engine.
- `neeron/os_world/`: Windows app launcher, GUI automation controller, system shell execution, and screen perception.
