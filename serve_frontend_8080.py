#!/usr/bin/env python3
"""
Simple HTTP server to serve the Career Revolution frontend on port 8080.
"""

import http.server
import socketserver
import webbrowser
import os
from pathlib import Path

PORT = 8080
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
    
    port = 8080
    
    try:
        with socketserver.TCPServer(("", port), FrontendHandler) as httpd:
            # Configuration
            from dotenv import load_dotenv
            import os
            load_dotenv()
            backend_port = os.getenv("BACKEND_PORT", "8010")
            
            print("=" * 60)
            print("CAREER REVOLUTION FRONTEND SERVER")
            print("=" * 60)
            print(f"Frontend running at: http://localhost:{port}")
            print(f"Backend API: http://localhost:{backend_port}")
            print("\nIMPORTANT: Make sure the backend is running!")
            print(f"Backend should be at: http://localhost:{backend_port}")
            print("\nPress Ctrl+C to stop the server")
            print("=" * 60)
            
            # Try to open browser automatically
            try:
                webbrowser.open(f"http://localhost:{port}")
                print("\n[OK] Browser opened automatically")
            except:
                print("\n[WARN] Could not open browser automatically")
                print(f"Please open: http://localhost:{port}")
            
            httpd.serve_forever()
            
    except OSError as e:
        print(f"Error starting server: {e}")
        print(f"Port {port} may already be in use.")
        print("Trying port 8081...")
        # Try port 8081 instead
        port = 8081
        with socketserver.TCPServer(("", port), FrontendHandler) as httpd:
            print(f"Frontend running at: http://localhost:{port}")
            webbrowser.open(f"http://localhost:{port}")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nFrontend server stopped.")

if __name__ == "__main__":
    start_server()