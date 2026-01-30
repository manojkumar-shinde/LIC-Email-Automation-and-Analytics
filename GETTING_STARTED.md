# Getting Started with LIC Email Intelligence Platform

This guide will help you start the LIC Email Intelligence Platform on your local machine.

## Prerequisites

Before starting the project, ensure you have the following installed and running:

### Required Software
- **Python 3.8+** - For the backend services
- **Node.js 16+** - For the frontend application
- **Ollama** - Local AI model runtime (must be running on port 11434)
- **Gmail API Credentials** - `credentials.json` file in the `backend/` directory

### Verify Ollama is Running
```powershell
# Check if Ollama is running
curl http://localhost:11434/api/tags
```

If Ollama is not running, start it:
```powershell
ollama serve
```

---

## Quick Start

### Option 1: Start Both Services (Recommended)

Open **two separate PowerShell/Command Prompt windows**:

#### Window 1 - Backend
```powershell
cd c:\Users\KHAN\.gemini\antigravity\scratch\lic-platform\backend
python run.py
```

#### Window 2 - Frontend
```powershell
cd c:\Users\KHAN\.gemini\antigravity\scratch\lic-platform\frontend
npm run dev
```

---

## Detailed Setup Instructions

### Backend Setup

1. **Navigate to backend directory**:
   ```powershell
   cd c:\Users\KHAN\.gemini\antigravity\scratch\lic-platform\backend
   ```

2. **Create virtual environment** (first time only):
   ```powershell
   python -m venv venv
   ```

3. **Activate virtual environment**:
   ```powershell
   .\venv\Scripts\activate
   ```

4. **Install dependencies** (first time only):
   ```powershell
   pip install -r requirements.txt
   ```

5. **Ensure Gmail credentials exist**:
   - Place your `credentials.json` file in the `backend/` directory
   - This is required for Gmail API access

6. **Start the backend**:
   ```powershell
   python run.py
   ```

   The backend will start three services:
   - **API Server** - http://localhost:8000
   - **Ingestor Worker** - Polls Gmail for new emails
   - **ETL Worker** - Processes emails with AI analysis

7. **Verify backend is running**:
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

---

### Frontend Setup

1. **Navigate to frontend directory**:
   ```powershell
   cd c:\Users\KHAN\.gemini\antigravity\scratch\lic-platform\frontend
   ```

2. **Install dependencies** (first time only):
   ```powershell
   npm install
   ```

3. **Start the development server**:
   ```powershell
   npm run dev
   ```

4. **Access the dashboard**:
   - Open your browser to the URL shown in the terminal (typically http://localhost:5173)

---

## Stopping the Project

### Stop Backend
- Press `Ctrl + C` in the backend terminal window
- This will gracefully shut down all three backend services

### Stop Frontend
- Press `Ctrl + C` in the frontend terminal window

---

## Troubleshooting

### Backend Issues

**Problem**: `ModuleNotFoundError` or import errors
```powershell
# Solution: Reinstall dependencies
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
```

**Problem**: `credentials.json not found`
```
# Solution: Ensure credentials.json is in backend/ directory
backend/
└── credentials.json  ← Must be here
```

**Problem**: Ollama connection errors
```powershell
# Solution: Start Ollama service
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

**Problem**: Database errors
```powershell
# Solution: The SQLite database is auto-created
# If corrupted, you can delete and restart:
cd backend
Remove-Item data\emails.db
python run.py  # Will recreate database
```

### Frontend Issues

**Problem**: `npm: command not found`
```
# Solution: Install Node.js from https://nodejs.org/
```

**Problem**: Port 5173 already in use
```powershell
# Solution: Kill the process using the port or use a different port
npm run dev -- --port 5174
```

**Problem**: Frontend can't connect to backend
```
# Solution: Ensure backend is running on http://localhost:8000
# Check frontend/vite.config.js proxy settings
```

---

## System Architecture

When you start the project, the following components run:

```
┌─────────────────────────────────────────────────────────┐
│                    LIC Email Platform                    │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Frontend (Port 5173)                                    │
│  └─ React Dashboard + Vite Dev Server                    │
│                        ↓                                  │
│  Backend (Port 8000)                                     │
│  ├─ FastAPI Server (REST API)                           │
│  ├─ Ingestor Worker (Gmail Polling)                     │
│  └─ ETL Worker (AI Analysis Pipeline)                   │
│                        ↓                                  │
│  External Services                                       │
│  ├─ SQLite Database (backend/data/emails.db)            │
│  ├─ Gmail API (Email ingestion)                         │
│  └─ Ollama AI (Port 11434 - AI processing)             │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## First Time Setup Checklist

- [ ] Python 3.8+ installed
- [ ] Node.js 16+ installed
- [ ] Ollama installed and running
- [ ] Gmail API `credentials.json` in `backend/` directory
- [ ] Backend virtual environment created
- [ ] Backend dependencies installed (`pip install -r requirements.txt`)
- [ ] Frontend dependencies installed (`npm install`)
- [ ] Backend started (`python run.py`)
- [ ] Frontend started (`npm run dev`)
- [ ] Dashboard accessible in browser

---

## Useful Commands

### Backend
```powershell
# Check API status
curl http://localhost:8000/health

# View API documentation
# Open browser: http://localhost:8000/docs

# View recent emails
curl http://localhost:8000/emails

# Check worker status
# (Shows in terminal logs when backend is running)
```

### Frontend
```powershell
# Build production version
npm run build

# Preview production build
npm run preview
```

---

## Next Steps

Once the platform is running:

1. **Monitor the Dashboard** - View email processing stats and pipeline health
2. **Check Logs** - Backend logs appear in the terminal showing email ingestion and processing
3. **Test Email Processing** - Send an email to the configured Gmail account and watch it get processed
4. **Explore the API** - Visit http://localhost:8000/docs to interact with the REST API

---

## Support

For issues or questions:
- Check the logs in the backend terminal
- Review `backend/app.log` for detailed error messages
- Ensure all prerequisites are met
- Verify Ollama is running and accessible

Happy analyzing! 🚀
