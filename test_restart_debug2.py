import subprocess
import time
import requests
import sys

print("Starting server on port 7862...")
proc = subprocess.Popen([sys.executable, "app.py", "--port", "7862"], 
                       stdout=subprocess.PIPE, 
                       stderr=subprocess.PIPE,
                       text=True)

# Wait for server to start
time.sleep(3)

try:
    # Test restart endpoint
    print("Calling restart endpoint...")
    response = requests.post("http://127.0.0.1:7862/api/system/restart", timeout=5)
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
print(f"\nSTDERR:\n{stderr}")
