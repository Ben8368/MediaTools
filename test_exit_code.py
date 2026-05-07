import os
import sys
import time
import threading

def delayed_exit():
    time.sleep(0.5)
    print(f"Parent PID: {os.getppid()}, Current PID: {os.getpid()}")
    try:
        import psutil
        parent = psutil.Process(os.getppid())
        print(f"Parent process name: {parent.name()}")
        if 'python' in parent.name().lower():
            print("In reload mode, exiting with 0")
            os._exit(0)
    except Exception as e:
        print(f"Error: {e}")
    
    print("Not in reload mode, exiting with 3")
    os._exit(3)

threading.Thread(target=delayed_exit, daemon=True).start()
time.sleep(2)
