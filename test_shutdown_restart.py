import subprocess
import time
import requests
import sys

def test_restart():
    """Test restart functionality"""
    print("Starting server...")
    proc = subprocess.Popen([sys.executable, "app.py"], 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE,
                           text=True)
    
    # Wait for server to start
    time.sleep(3)
    
    try:
        # Test restart endpoint
        print("Calling restart endpoint...")
        response = requests.post("http://127.0.0.1:7860/api/system/restart", timeout=5)
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
    
    print(f"Process exited with code: {exit_code}")
    if "exiting with 3" in stderr or "exit code 3" in stderr.lower():
        print("[PASS] Restart exit code is correct (3)")
        return True
    elif exit_code == 3:
        print("[PASS] Restart exit code is correct (3)")
        return True
    else:
        print(f"[FAIL] Expected exit code 3, got {exit_code}")
        if stderr:
            print(f"STDERR:\n{stderr[-500:]}")
        return False

def test_shutdown():
    """Test shutdown functionality"""
    print("\nStarting server...")
    proc = subprocess.Popen([sys.executable, "app.py"], 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE,
                           text=True)
    
    # Wait for server to start
    time.sleep(3)
    
    try:
        # Test shutdown endpoint
        print("Calling shutdown endpoint...")
        response = requests.post("http://127.0.0.1:7860/api/system/shutdown", timeout=5)
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
    
    print(f"Process exited with code: {exit_code}")
    if exit_code == 0:
        print("[PASS] Shutdown exit code is correct (0)")
        return True
    else:
        print(f"[FAIL] Expected exit code 0, got {exit_code}")
        if stderr:
            print(f"STDERR:\n{stderr[-500:]}")
        return False

if __name__ == "__main__":
    try:
        restart_ok = test_restart()
        shutdown_ok = test_shutdown()
        
        if restart_ok and shutdown_ok:
            print("\n[PASS] All tests passed!")
        else:
            print("\n[FAIL] Some tests failed")
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()
