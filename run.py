#!/usr/bin/env python3
"""
Simple script to run Career Revolution API.
"""
import os
import sys
import asyncio
import uvicorn
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def kill_port_owner(port):
    """Detect and terminate any process listening on the specified port (Windows)."""
    if sys.platform != 'win32':
        return
    
    try:
        # Find the PID owning the port
        cmd = f"netstat -ano | findstr LISTENING | findstr :{port}"
        output = subprocess.check_output(cmd, shell=True).decode()
        
        for line in output.strip().split('\n'):
            parts = line.split()
            if len(parts) > 4:
                pid = parts[-1]
                if pid == "0": continue # System/Idle
                
                # Check if it's a python process to be safe
                check_cmd = f"tasklist /FI \"PID eq {pid}\" /NH"
                check_out = subprocess.check_output(check_cmd, shell=True).decode()
                
                if "python" in check_out.lower() or "uvicorn" in check_out.lower():
                    print(f"Found existing backend (PID {pid}) on port {port}. Terminating...")
                    subprocess.run(f"taskkill /F /PID {pid} /T", shell=True, capture_output=True)
                    # Small delay to let Windows release the port
                    import time
                    time.sleep(1)
    except Exception:
        # No process found or error (ignore)
        pass

# Windows-specific fix for Playwright/Subprocess: Use ProactorEventLoop
if sys.platform == 'win32':
    try:
        import asyncio
        from asyncio import WindowsProactorEventLoopPolicy
        asyncio.set_event_loop_policy(WindowsProactorEventLoopPolicy())
        # Disable future overrides
        asyncio.set_event_loop_policy = lambda policy: None
    except Exception:
        pass

if __name__ == "__main__":
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Configuration
    port = int(os.getenv("BACKEND_PORT", 8010))
    
    # Force clear the port before starting to avoid 10048 errors
    kill_port_owner(port)
    
    print("Starting Career Revolution API...")
    print("=" * 50)
    print(f"API Documentation: http://localhost:{port}/docs")
    print("=" * 50)
    
    # loop="asyncio" ensures that the standard asyncio loop (with our policy) is used
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
        loop="asyncio"
    )