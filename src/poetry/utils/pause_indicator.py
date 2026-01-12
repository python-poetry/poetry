
from threading import Lock

_lock = Lock()
_counter = 0

def is_paused():
    return _counter != 0

class IndicatorPaused:
    def __enter__(self):
        global _counter
        with _lock:
            _counter += 1
    
    def __exit__(self, *exc):
        global _counter
        with _lock:
            _counter -= 1
            assert _counter >= 0
