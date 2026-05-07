import subprocess
import time
import requests
import sys
import random

port = random.randint(8000, 9000)
print(f"Starting server on port {port}...")
proc = subprocess.Popen([sys.executable, "app.py", "--port", str(port)], 
                       stdout=subprocess.PIPE, 
                       stderr=subprocess.PIPE,
                       text=True)

# Wait for server to start
time.sleep(3)

try:
    # Test restart endpoint
    print("Calling restart endpoint...")
    response = requests.post(f"http://127.0.0.1:{port}/api/system/restart", timeout=5)
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error calling endpoint: {e}")

# Wait for process to exit
try:
    exit_code = proc.wait(timeout=10)
except subprocess.TimeoutExpired:
    proc.kill()
    exit_code = proc.wait()

stdout, stderr = proc.communicate()

print(f"\nProcess exited with code: {exit_code}")
if exit_code == 3:
    print("[PASS] Restart exit code is correct (3)")
else:
    print(f"[FAIL] Expected exit code 3, got {exit_code}")
    if "error" in stderr.lower():
        print(f"STDERR:\n{stderr[-500:]}")
