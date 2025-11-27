#!/usr/bin/env python3
"""Diagnostic script to check Render configuration"""

import os
import sys

print("=" * 60)
print("RENDER CONFIGURATION DIAGNOSTIC")
print("=" * 60)

print(f"\n1. PORT Environment Variable:")
port = os.getenv("PORT")
if port:
    print(f"   ✅ PORT is set: {port}")
else:
    print(f"   ❌ PORT is NOT set (this is required for Render)")

print(f"\n2. Python Executable:")
print(f"   {sys.executable}")

print(f"\n3. Current Working Directory:")
print(f"   {os.getcwd()}")

print(f"\n4. Checking for app.main:")
try:
    from app.main import app
    print(f"   ✅ app.main can be imported")
    print(f"   ✅ App type: {type(app)}")
    print(f"   ✅ App title: {app.title}")
except Exception as e:
    print(f"   ❌ Cannot import app.main: {e}")

print(f"\n5. Checking for uvicorn:")
try:
    import uvicorn
    print(f"   ✅ uvicorn is installed: {uvicorn.__version__}")
except ImportError:
    print(f"   ❌ uvicorn is NOT installed")

print(f"\n6. Command that should be running:")
print(f"   uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level info")

print("\n" + "=" * 60)
print("If PORT is not set, Render may not be running this as a web service")
print("=" * 60)

