#!/usr/bin/env python3
"""
Simple HTTP server to serve the visualization locally and avoid CORS issues.
"""

import http.server
import socketserver
import os
import webbrowser
from threading import Timer

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def open_browser():
    webbrowser.open(f'http://localhost:{PORT}/diva_optimized.html')

if __name__ == "__main__":
    os.chdir(DIRECTORY)

    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"Server starting at http://localhost:{PORT}")
        print(f"Serving files from: {DIRECTORY}")
        print("\nOpen your browser to:")
        print(f"  http://localhost:{PORT}/diva_optimized.html")
        print("\nPress Ctrl+C to stop the server")

        # Open browser after 1 second
        timer = Timer(1, open_browser)
        timer.daemon = True
        timer.start()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")