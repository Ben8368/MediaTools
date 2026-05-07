import os
import signal
import sys
import time
import threading

def _signal_handler(signum, frame):
    print(f"Signal {signum} received, exiting with code 3")
    os._exit(3)

signal.signal(signal.SIGTERM, _signal_handler)

def delayed_signal():
    time.sleep(1)
    print(f"Sending SIGTERM to PID {os.getpid()}")
    os.kill(os.getpid(), signal.SIGTERM)

threading.Thread(target=delayed_signal, daemon=True).start()

time.sleep(5)
print("Should not reach here")
