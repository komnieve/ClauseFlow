# ClauseFlow Demo Deployment

Quick deployment guide for demos and testing.

## Ports

- **Backend:** 9847
- **Frontend:** 9848

These ports were chosen to avoid conflicts with common services (8080, 3000, etc.).

## Quick Start

```bash
# Clone/pull the repo
git clone <repo-url>
cd ClauseFlow

# Ensure backend/.env exists with your API key
cat backend/.env
# Should contain: OPENAI_API_KEY=sk-...

# Launch
./start-demo.sh
```

The script will:
1. Create Python virtual environment (first run)
2. Install Python dependencies
3. Install npm packages (first run)
4. Start backend on port 9847
5. Start frontend on port 9848
6. Display local and network URLs

## Stopping

```bash
# From another terminal
./stop-demo.sh

# Or Ctrl+C in the terminal running start-demo.sh
```

## Network Access (Demo to Others)

The script displays the server IP. Access from other machines:
- Frontend: `http://<server-ip>:9848`
- Backend API: `http://<server-ip>:9847`
- API Docs: `http://<server-ip>:9847/docs`

### Firewall

Ports 9847 and 9848 must be open for external access.

**AWS Security Groups:** Add inbound rules for TCP 9847 and 9848.

**UFW (Ubuntu):**
```bash
sudo ufw allow 9847/tcp
sudo ufw allow 9848/tcp
```

## Environment Variables

### Backend (`backend/.env`)

```
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4
APP_NAME=ClauseFlow
APP_VERSION=0.1.0
DEBUG=True
```

### Frontend

The frontend API URL is set automatically by the start script via `VITE_API_URL`.

## Troubleshooting

### Port already in use
```bash
# Check what's using the port
lsof -i:9847
lsof -i:9848

# Kill if needed
lsof -ti:9847 | xargs kill
```

### Backend won't start
- Check `backend/.env` exists and has valid API key
- Check Python 3.10+ is installed: `python3 --version`

### Frontend can't reach backend
- Verify backend is running: `curl http://localhost:9847/health`
- Check browser console for CORS errors (should be fixed - CORS allows all origins)

### Dependencies fail to install
```bash
# Backend - manual install
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend - manual install
cd frontend
npm install
```

## Manual Start (without script)

If you need to run things separately:

```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 9847

# Terminal 2 - Frontend
cd frontend
VITE_API_URL=http://localhost:9847 npm run dev -- --port 9848 --host 0.0.0.0
```

## Verified Working

Tested 2025-01-30:
- Frontend loads, shows upload area and document list
- Backend health check responds
- Document review flow works (navigation, filtering, mark reviewed)
- 75+ clauses extracted from sample PO document
