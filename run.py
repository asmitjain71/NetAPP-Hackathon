#!/usr/bin/env python
"""
Quick start script for the Intelligent Data Management System
"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import init_db
from app import app, socketio
from config import API_HOST, API_PORT, DEBUG

if __name__ == '__main__':
    print("=" * 60)
    print("NetApp Intelligent Data Management System")
    print("=" * 60)
    print(f"Starting server on http://{API_HOST}:{API_PORT}")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    # Initialize database
    try:
        init_db()
        print("✓ Database initialized")
    except Exception as e:
        print(f"⚠ Database initialization warning: {e}")
    
    # Start application
    socketio.run(app, host=API_HOST, port=API_PORT, debug=DEBUG)


