#!/bin/bash
# Startup script for Render - ensures web server starts properly

echo "🚀 Starting SPDCL Automation Web Service..."
echo "📡 Binding to port: $PORT"
echo "🌐 Health check will be available at: /"

# Start uvicorn with explicit logging
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level info

