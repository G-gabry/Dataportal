#!/bin/bash
# Data Portal - Local Development Startup Script
# Usage: ./start-local.sh

set -e
cd "$(dirname "$0")"

echo "=========================================="
echo "  Data Portal - Local Development"
echo "=========================================="
echo ""

# Check if PostgreSQL is running
if ! brew services list | grep -q "postgresql.*started"; then
    echo "Starting PostgreSQL..."
    brew services start postgresql@14
    sleep 2
fi

# Check if database exists
if ! psql -U ahmedali -lqt | cut -d \| -f 1 | grep -qw data_portal; then
    echo "Creating database..."
    psql -U ahmedali -d postgres -c "CREATE DATABASE data_portal;"
    psql -U ahmedali -d data_portal -f scripts/init-db.sql
    psql -U ahmedali -d data_portal -c "UPDATE users SET password_hash = '\$2b\$12\$FKlM2i.AO/KWZHTCjQb3r.U7H8xH7rO5zX3ui.BBFeqdPmKyrb8KK' WHERE email = 'admin@dataportal.com';"
    echo "Database initialized!"
fi

# Start backend
echo ""
echo "Starting Backend on port 8001..."
cd backend
source venv/bin/activate
export DATABASE_URL="postgresql://ahmedali@localhost:5432/data_portal"
export SECRET_KEY="dev-secret-key-change-in-production"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend
echo "Starting Frontend on port 3001..."
cd frontend
npm run dev -- -p 3001 &
FRONTEND_PID=$!
cd ..

echo ""
echo "=========================================="
echo "  Services Running!"
echo "=========================================="
echo ""
echo "  Frontend:  http://localhost:3001"
echo "  Backend:   http://localhost:8001"
echo "  API Docs:  http://localhost:8001/docs"
echo ""
echo "  Login: admin@dataportal.com / admin123"
echo ""
echo "  Press Ctrl+C to stop all services"
echo "=========================================="

# Cleanup on exit
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "Done!"
}
trap cleanup EXIT

# Wait for processes
wait
