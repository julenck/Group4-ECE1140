"""Start the REST API Server

This script starts the REST API server that manages train state files
and provides endpoints for Raspberry Pi clients to connect to.

Run this on the main computer (server).

Usage:
    python start_server.py [--port PORT] [--host HOST]

Example:
    python start_server.py --port 5000 --host 0.0.0.0
"""
import os
import sys
import argparse
import socket

# Add api directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
api_dir = os.path.join(current_dir, "api")
sys.path.insert(0, api_dir)

def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        # Connect to external address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train System REST API Server")
    parser.add_argument("--port", type=int, default=5000, help="Port to run server on (default: 5000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    args = parser.parse_args()
    
    # Import and start server
    from train_api_server import app
    
    local_ip = get_local_ip()
    
    print("=" * 80)
    print("  TRAIN SYSTEM REST API SERVER")
    print("=" * 80)
    print(f"\n✓ Server starting on {args.host}:{args.port}")
    print(f"✓ Local IP address: {local_ip}")
    print(f"\n📡 Raspberry Pis should connect to: http://{local_ip}:{args.port}")
    print("\n📋 Available Endpoints:")
    print(f"   http://{local_ip}:{args.port}/api/health")
    print(f"   http://{local_ip}:{args.port}/api/trains")
    print(f"   http://{local_ip}:{args.port}/api/train/<id>/state")
    print("\n🔧 To stop the server, press Ctrl+C")
    print("=" * 80)
    print()
    
    try:
        app.run(host=args.host, port=args.port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n\n✓ Server stopped gracefully")
    except Exception as e:
        print(f"\n✗ Error starting server: {e}")
        sys.exit(1)
