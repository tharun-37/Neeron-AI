from collections import deque

class AudioVisualizer:
    """Clean ASCII waveform visualizer for real-time audio input."""
    def __init__(self, window_size: int = 60):
        self.window_size = window_size
        self.buffer = deque(maxlen=window_size)
    
    def add_sample(self, energy: float):
        self.buffer.append(energy)
    
    def draw(self) -> str:
        if not self.buffer:
            return "[" + " " * self.window_size + "]"
        
        max_val = max(self.buffer) if self.buffer else 1
        if max_val == 0:
            max_val = 1
        
        chars = "▁▂▃▄▅▆▇█"
        waveform = ""
        for energy in self.buffer:
            idx = min(int((energy / max_val) * (len(chars) - 1)), len(chars) - 1)
            waveform += chars[idx]
        
        return "[" + waveform + "]"
