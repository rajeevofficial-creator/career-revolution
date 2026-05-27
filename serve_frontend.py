#!/usr/bin/env python3
"""
Simple HTTP server to serve the Career Revolution frontend.
"""

import http.server
import socketserver
import webbrowser
import os
from pathlib import Path

PORT = 3000
FRONTEND_DIR = Path(__file__).parent / "simple_frontend"

class FrontendHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)
    
    def log_message(self, format, *args):
        # Minimal logging
        print(f"[{self.log_date_time_string()}] {format % args}")

def start_server():
    """Start the HTTP server for frontend."""
    os.chdir(FRONTEND_DIR)
    
    with socketserver.TCPServer(("", PORT), FrontendHandler) as httpd:
        print("=" * 60)
        print("CAREER REVOLUTION FRONTEND SERVER")
        print("=" * 60)
        print(f"Frontend running at: http://localhost:{PORT}")
        print(f"Backend API: http://localhost:8000")
        print("\nIMPORTANT: Make sure the backend is running!")
        print("Backend should be at: http://localhost:8000")
        print("\nPress Ctrl+C to stop the server")
        print("=" * 60)
        
        # Try to open browser automatically
        try:
            webbrowser.open(f"http://localhost:{PORT}")
            print("\n[OK] Browser opened automatically")
        except:
            print("\n[WARN] Could not open browser automatically")
            print(f"Please open: http://localhost:{PORT}")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nFrontend server stopped.")
        except OSError as e:
            print(f"Error: {e}")
            print(f"Port {PORT} may be in use. Try a different port.")

if __name__ == "__main__":
    start_server()