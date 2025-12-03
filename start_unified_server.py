"""Start the Unified Railway System REST API Server

This script starts the unified REST API server that manages all system JSON files
and provides endpoints for all components:
- Train Controller
- Track Controller (Wayside)  
- CTC (Centralized Traffic Control)
- Track Model

Run this on the main computer (server) BEFORE starting any other components.

Usage:
    python start_unified_server.py [--port PORT] [--host HOST]

Example:
    python start_unified_server.py --port 5000 --host 0.0.0.0

Author: James Struyk
"""
import os
import sys
import argparse
import socket

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

def check_dependencies():
    """Check if required packages are installed."""
    missing = []
    
    try:
        import flask
    except ImportError:
        missing.append("flask")
    
    try:
        import flask_cors
    except ImportError:
        missing.append("flask-cors")
    
    if missing:
        print("=" * 80)
        print("  ERROR: Missing Required Packages")
        print("=" * 80)
        print(f"\nThe following packages are not installed:")
        for pkg in missing:
            print(f"  - {pkg}")
        print(f"\nPlease install them using:")
        print(f"  pip install {' '.join(missing)}")
        print("=" * 80)
        return False
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Unified Railway System REST API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_unified_server.py
  python start_unified_server.py --port 5000
  python start_unified_server.py --port 5001 --host 0.0.0.0

This server must be running before starting:
  - CTC UI (with --server flag)
  - Wayside Controllers on Raspberry Pis (with --server flag)
  - Train Controllers on Raspberry Pis (with --server flag)
        """
    )
    parser.add_argument("--port", type=int, default=5000, 
                       help="Port to run server on (default: 5000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", 
                       help="Host to bind to (default: 0.0.0.0)")
    args = parser.parse_args()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Import server app
    try:
        from unified_api_server import app, sync_running, sync_train_data_to_states
        from threading import Thread
    except ImportError as e:
        print(f"Error: Could not import unified_api_server.py: {e}")
        print("Make sure unified_api_server.py is in the same directory as this script.")
        sys.exit(1)
    
    local_ip = get_local_ip()
    
    print("=" * 80)
    print("  🚂 UNIFIED RAILWAY SYSTEM REST API SERVER 🚂")
    print("=" * 80)
    print(f"\n📡 Server Configuration:")
    print(f"   Host: {args.host}")
    print(f"   Port: {args.port}")
    print(f"   Local IP: {local_ip}")
    print(f"\n🌐 Connection URLs:")
    print(f"   From this computer:    http://localhost:{args.port}")
    print(f"   From Raspberry Pis:    http://{local_ip}:{args.port}")
    print(f"   Health Check:          http://{local_ip}:{args.port}/api/health")
    print(f"\n📋 Supported Components:")
    print(f"   ✓ Train Controller       (endpoints: /api/train/<id>/state)")
    print(f"   ✓ Track Controller       (endpoints: /api/wayside/<id>/state)")
    print(f"   ✓ CTC                    (endpoints: /api/ctc/*)")
    print(f"   ✓ Track Model            (endpoints: /api/track_model/*)")
    print(f"\n🔧 How to Use:")
    print(f"   1. Keep this server running")
    print(f"   2. On Raspberry Pi (Wayside): python sw_wayside_controller_ui.py --server http://{local_ip}:{args.port}")
    print(f"   3. On Raspberry Pi (Train):   python train_controller_hw_ui.py --server http://{local_ip}:{args.port}")
    print(f"   4. On Main Computer (CTC):    python ctc_ui_temp.py --server http://localhost:{args.port}")
    print(f"\n⚠️  Important:")
    print(f"   - Make sure your firewall allows port {args.port}")
    print(f"   - All Raspberry Pis must be on the same network")
    print(f"   - Write down the IP address: {local_ip}")
    print(f"\n🛑 To stop: Press Ctrl+C")
    print("=" * 80)
    print()
    
    # Start background sync thread
    print("[Server] Starting background sync threads...")
    sync_thread = Thread(target=sync_train_data_to_states, daemon=True)
    sync_thread.start()
    print("[Server] ✓ Train data sync thread started")
    
    print(f"[Server] Starting Flask server on {args.host}:{args.port}...")
    print()
    
    try:
        app.run(host=args.host, port=args.port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n" + "=" * 80)
        print("  🛑 SERVER SHUTTING DOWN")
        print("=" * 80)
        print("[Server] Stopping background threads...")
        sync_running = False
        sync_thread.join(timeout=2.0)
        print("[Server] ✓ Server stopped gracefully")
    except Exception as e:
        print(f"\n✗ Error starting server: {e}")
        sys.exit(1)
    finally:
        sync_running = False

