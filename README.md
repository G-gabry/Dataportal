# Data Portal

A web scraping and data extraction platform for educational programs, scholarships, conferences, and exchanges.

## Quick Start

### Credentials

| Service | Value |
|---------|-------|
| **App Email** | `admin@dataportal.com` |
| **App Password** | `admin123` |
| **Database Name** | `data_portal` |
| **Database User** | `ahmedali` (your Mac username) |
| **Database Password** | *(none - uses local auth)* |

### URLs (when running)

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3001 |
| Backend API | http://localhost:8001 |
| API Docs | http://localhost:8001/docs |

---

## Option 1: Run WITHOUT Docker (Local Development)

### Prerequisites
- PostgreSQL installed (`brew install postgresql@14`)
- Node.js 18+ installed
- Python 3.11 installed (`brew install python@3.11`)

### Step 1: Start PostgreSQL
```bash
brew services start postgresql@14
```

### Step 2: Initialize Database (first time only)
```bash
# Create database
psql -U ahmedali -d postgres -c "CREATE DATABASE data_portal;"

# Initialize schema
psql -U ahmedali -d data_portal -f scripts/init-db.sql

# Fix admin password (run this after init)
psql -U ahmedali -d data_portal -c "UPDATE users SET password_hash = '\$2b\$12\$FKlM2i.AO/KWZHTCjQb3r.U7H8xH7rO5zX3ui.BBFeqdPmKyrb8KK' WHERE email = 'admin@dataportal.com';"
```

### Step 3: Start Backend
```bash
cd backend
source venv/bin/activate
export DATABASE_URL="postgresql://ahmedali@localhost:5432/data_portal"
export SECRET_KEY="dev-secret-key-change-in-production"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Step 4: Start Frontend (new terminal)
```bash
cd frontend
npm run dev -- -p 3001
```

### Quick Start Script (All-in-One)
Create this as `start-local.sh` in the project root:
```bash
#!/bin/bash
cd "$(dirname "$0")"

# Start backend in background
cd backend
source venv/bin/activate
export DATABASE_URL="postgresql://ahmedali@localhost:5432/data_portal"
export SECRET_KEY="dev-secret-key-change-in-production"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 &
BACKEND_PID=$!

# Start frontend
cd ../frontend
npm run dev -- -p 3001 &
FRONTEND_PID=$!

echo "Backend running on http://localhost:8001"
echo "Frontend running on http://localhost:3001"
echo "Press Ctrl+C to stop"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
```

---

## Option 2: Run WITH Docker

### Prerequisites
- Docker Desktop installed and running

### Start Everything
```bash
docker-compose up --build
```

### Stop Everything
```bash
docker-compose down
```

### Reset Database
```bash
docker-compose down -v  # removes volumes
docker-compose up --build
```

---

## First Time Setup

### Without Docker
```bash
# 1. Install backend dependencies
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Install frontend dependencies
cd ../frontend
npm install

# 3. Initialize database (see Step 2 above)
```

### With Docker
```bash
docker-compose up --build
# That's it! Docker handles everything
```

---

## Useful Commands

### Database
```bash
# Connect to database
psql -U ahmedali -d data_portal

# List all tables
psql -U ahmedali -d data_portal -c "\dt"

# View sources
psql -U ahmedali -d data_portal -c "SELECT name, type, base_url FROM sources;"

# Reset database
psql -U ahmedali -d postgres -c "DROP DATABASE data_portal;"
psql -U ahmedali -d postgres -c "CREATE DATABASE data_portal;"
psql -U ahmedali -d data_portal -f scripts/init-db.sql
```

### API Testing
```bash
# Login and get token
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@dataportal.com","password":"admin123"}'

# Get sources (with token)
curl http://localhost:8001/api/v1/sources \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Public API (no auth needed)
curl http://localhost:8001/api/public/programs
curl http://localhost:8001/api/public/scholarships
```

---

## Project Structure

```
data-portal/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # API routes
│   │   ├── models/    # Database models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── ai/        # AI providers
│   │   └── tasks/     # Background tasks
│   └── requirements.txt
├── frontend/          # Next.js frontend
│   ├── src/
│   │   ├── app/       # Pages
│   │   ├── components/# UI components
│   │   └── lib/       # Utilities
│   └── package.json
├── scripts/
│   └── init-db.sql    # Database schema
└── docker-compose.yml
```

---

## Environment Variables

### Backend
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://ahmedali@localhost:5432/data_portal` | PostgreSQL connection |
| `SECRET_KEY` | `dev-secret-key...` | JWT signing key |
| `ANTHROPIC_API_KEY` | *(optional)* | For Claude AI |
| `GOOGLE_API_KEY` | *(optional)* | For Gemini AI |
| `OPENAI_API_KEY` | *(optional)* | For GPT AI |
| `FIRECRAWL_API_KEY` | *(optional)* | For real scraping |

### Frontend
| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8001` | Backend API URL |
