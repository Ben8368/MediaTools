import os
import signal
import sys
import time
import threading

_restart_requested = False

def _signal_handler(signum, frame):
    global _restart_requested
    print(f"Signal {signum} received")
    _restart_requested = True
    raise SystemExit(3)

signal.signal(signal.SIGTERM, _signal_handler)

def delayed_signal():
    time.sleep(1)
    print(f"Sending SIGTERM to PID {os.getpid()}")
    os.kill(os.getpid(), signal.SIGTERM)

threading.Thread(target=delayed_signal, daemon=True).start()

try:
    time.sleep(5)
except SystemExit as e:
    print(f"SystemExit caught with code {e.code}")
    sys.exit(e.code)

print("Should not reach here")
