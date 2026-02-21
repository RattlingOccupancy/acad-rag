#!/bin/bash

# Quick start script for RAG system (macOS/Linux)

echo ""
echo "╔═══════════════════════════════════════╗"
echo "║   RAG System - Quick Start             ║"
echo "╚═══════════════════════════════════════╝"
echo ""

# Check if we have required tools
if ! command -v python3 &> /dev/null; then
    echo "✘ Python3 not found. Please install Python 3.9+"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "✘ npm not found. Please install Node.js"
    exit 1
fi

echo "✓ Python and npm found"
echo ""
echo "Starting services..."
echo ""

# Install backend dependencies
echo "[1/2] Installing backend dependencies..."
cd backend
pip install -q fastapi uvicorn python-multipart
cd ..

# Install frontend dependencies
echo "[2/2] Installing frontend dependencies..."
cd frontend
npm install -q
cd ..

echo ""
echo "Starting FastAPI backend..."
(cd backend && uvicorn api:app --reload --port 8000) &
BACKEND_PID=$!

echo "Starting React frontend..."
sleep 2
(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo ""
echo "✓ Services started!"
echo ""
echo "Frontend:  http://localhost:5173"
echo "Backend:   http://localhost:8000"
echo "API Docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop services"
echo ""

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID
