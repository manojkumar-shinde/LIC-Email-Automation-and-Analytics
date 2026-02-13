# LIC Email Intelligence Platform

> **Enterprise-grade AI-assisted email processing for Life Insurance Corporation of India**  
> A secure, local-first platform with human-in-the-loop reply assistance and multi-layered safety controls.

---

## 🎯 Overview

An on-premise AI platform that analyzes incoming emails, classifies intent, generates safe reply drafts, and maintains complete audit trails—all while protecting customer privacy and ensuring regulatory compliance.

**Key Capabilities:**
- 📧 **Gmail OAuth Integration** with automatic token refresh
- 🔒 **PII Redaction** using Microsoft Presidio
- 🤖 **Local AI Analysis** via Ollama (Gemma 2B)
- ✅ **Safety-First Reply Generation** with multi-tier validation
- 📊 **Real-time Dashboard** for monitoring and analytics
- 🔍 **RAG-powered** policy document search

---

## ✨ Features

### Email Processing Pipeline
- **Gmail Sync**: OAuth 2.0 integration with refresh token support (never expires!)
- **PII Protection**: Automatic redaction of emails, phone numbers, and sensitive data
- **Intent Classification**: GENERAL_ENQUIRY, REQUEST, COMPLAINT, CLAIM_RELATED, etc.
- **Priority Calculation**: Rule-based HIGH/MEDIUM/LOW with audit trail
- **Sentiment Analysis**: POSITIVE, NEUTRAL, NEGATIVE detection

### Reply Generation (Enhanced Safety System)
- **Two-Tier Keyword Blocking**:
  - Hard blocks: Claims, payments, refunds, legal (always NO_REPLY)
  - Soft blocks: Timelines, approvals (block only with risk indicators)
- **Deterministic Pattern Selection**: Intent → Response mapping (no LLM discretion)
- **Post-Generation Validation**: Second safety gate for forbidden terms
- **Enhanced Audit Logging**: Explicit reasons for every NO_REPLY decision
- **Human-in-the-Loop**: All replies require manual approval before sending

### Dashboard
- Real-time email feed with priority color coding
- Live stats (pending, processing, completed, failed)
- Reply draft display with NO_REPLY safety indicators
- Gmail account management
- Manual email import (CSV/JSON)

---

## 🏗️ Architecture

### Backend
- **Framework**: FastAPI (Python 3.8+)
- **Database**: SQLite with WAL mode
- **Vector Store**: ChromaDB for RAG
- **LLM**: Ollama (Gemma2:2b, localhost:11434)
- **Email API**: Gmail API with OAuth 2.0
- **Processing**: Multiprocessing (API + Worker + Ingestor)

### Frontend
- **Framework**: React + Vite
- **Styling**: Vanilla CSS with dark mode
- **State**: React Hooks (useState, useEffect)
- **HTTP**: Fetch API to backend

### Data Flow
```
Gmail → OAuth Sync → PII Redaction → AI Analysis → Priority Rules → Reply Generation → Human Approval
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Ollama running on `localhost:11434`
- Gmail API credentials (`credentials.json`)

### 1. Backend Setup
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Add Gmail OAuth credentials
# Place credentials.json in backend/ directory

# Start services (API + Worker + Ingestor)
python run.py
```

Backend will start on: **http://localhost:8001**

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend will start on: **http://localhost:5173**

---

## 🔐 Gmail OAuth Setup

### Get OAuth Credentials
1. Visit [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable Gmail API
4. Create OAuth 2.0 Client ID (Desktop app)
5. Download credentials as `credentials.json`
6. Place in `backend/` directory

### Connect Gmail Account
```bash
# 1. Get authorization URL
curl "http://localhost:8001/api/gmail/oauth/authorize?gmail_email=your@gmail.com"

# 2. Visit the URL, authorize, copy the code

# 3. Complete OAuth
curl -X POST "http://localhost:8001/api/gmail/oauth/callback" \
  -H "Content-Type: application/json" \
  -d '{"gmail_email":"your@gmail.com","auth_code":"YOUR_CODE"}'
```

**Result:** Permanent connection with automatic token refresh!

---

## 📁 Project Structure

```
lic-platform/
├── backend/
│   ├── app/
│   │   ├── api.py              # REST endpoints
│   │   ├── worker.py           # Email processing pipeline
│   │   ├── ingestor.py         # Gmail sync service
│   │   ├── reply.py            # Reply generation (enhanced)
│   │   ├── brain.py            # AI analysis + RAG
│   │   ├── redaction.py        # PII protection
│   │   ├── priority.py         # Priority calculation
│   │   ├── database.py         # SQLite operations
│   │   └── gmail_fetcher.py    # Gmail API + OAuth
│   ├── data/
│   │   ├── emails.db           # Main database
│   │   └── chroma_db/          # Vector embeddings
│   ├── tests/
│   │   └── test_reply_safety.py # Reply agent tests
│   ├── credentials.json        # Gmail OAuth credentials
│   └── run.py                  # Service launcher
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── EmailTile.jsx   # Email display card
│   │   │   ├── RecentEmails.jsx # Email feed
│   │   │   └── ...
│   │   ├── App.jsx             # Main dashboard
│   │   └── index.css           # Dark mode styles
│   └── vite.config.js
│
└── README.md
```

---

## 🔧 API Endpoints

### Email Management
- `GET /api/stats` - Dashboard statistics
- `GET /api/emails` - Paginated email list
- `POST /api/upload` - Manual email upload (CSV/JSON)
- `POST /api/export` - Export emails

### Gmail Integration
- `GET /api/gmail/accounts` - List connected accounts
- `GET /api/gmail/oauth/authorize` - Start OAuth flow
- `POST /api/gmail/oauth/callback` - Complete OAuth
- `POST /api/gmail/sync` - Trigger sync
- `DELETE /api/gmail/disconnect` - Remove account

### Testing
- `GET /api/health` - Service health check

---

## 🧪 Testing

### Reply Safety Tests
```bash
cd backend
python tests/test_reply_safety.py
```

**Test Coverage:**
- Hard keyword blocking (claims, payments, fraud)
- Soft keyword + risk detection (timeline + urgent)
- Deterministic pattern selection
- Entry condition validation
- Post-generation forbidden term scanning

**Result:** All 10 tests pass ✅

---

## 🛡️ Safety Guarantees

### Multi-Layer Reply Safety
1. **Entry Conditions**: Priority, intent, confidence checks
2. **Hard Keyword Blocking**: Always block high-risk terms
3. **Soft Keyword + Risk**: Block timelines/approvals if urgent or negative
4. **Deterministic Patterns**: No LLM discretion in response selection
5. **Post-Validation**: Scan output for forbidden commitments
6. **Human Approval**: Required for all replies

### Compliance Features
- Complete audit trail for all NO_REPLY decisions
- Explicit blocking reasons logged
- No automated sending
- PII redaction before AI processing
- Local LLM (no data leaves premises)

---

## 📊 Database Schema

### Tables
- `emails` - Email content and metadata
- `gmail_config` - OAuth credentials with refresh tokens
- `priority_rules` - Configurable priority logic
- `chroma_embeddings` - Vector store for RAG

### Sample Query
```sql
SELECT 
    id, sender, subject, 
    json_extract(analysis, '$.intent') as intent,
    json_extract(analysis, '$.priority') as priority,
    generated_reply,
    status
FROM emails 
WHERE status = 'COMPLETED' 
ORDER BY received_at DESC;
```

---

## 🔄 Recent Updates

### v2.0 - Reply Agent Safety Enhancements
- ✅ Two-tier keyword blocking (hard vs soft)
- ✅ Deterministic pattern selection (intent → response mapping)
- ✅ Post-generation validation layer
- ✅ Enhanced audit logging with explicit NO_REPLY reasons
- ✅ Improved coverage for safe emails while maintaining zero-risk

### v1.5 - Gmail OAuth Integration
- ✅ OAuth 2.0 with refresh token support
- ✅ Automatic token renewal (permanent connection)
- ✅ Database schema updates for token storage
- ✅ Worker integration with OAuth handler

---

## 🤝 Contributing

This is an internal LIC platform. For improvements:
1. Create feature branch
2. Implement with tests
3. Ensure all safety tests pass
4. Submit for review

**Safety First:** All changes must maintain zero-risk guarantees.

---

## 📝 License

Internal use only - Life Insurance Corporation of India

---

## 🆘 Troubleshooting

### Gmail Sync Fails
```bash
# Check OAuth token status
curl http://localhost:8001/api/gmail/accounts

# Re-authorize if needed
curl "http://localhost:8001/api/gmail/oauth/authorize?gmail_email=your@gmail.com"
```

### Worker Not Processing
```bash
# Check logs
tail -f backend/logs/startup.log

# Verify Ollama is running
curl http://localhost:11434/api/tags
```

### Database Locked
```bash
# SQLite WAL mode should prevent this, but if it happens:
cd backend/data
sqlite3 emails.db "PRAGMA wal_checkpoint(TRUNCATE);"
```

---

## 📚 Documentation

- [Getting Started Guide](GETTING_STARTED.md)
- [Reply Agent Walkthrough](backend/docs/reply_agent.md)
- [Gmail OAuth Setup](backend/docs/oauth_setup.md)
- [API Reference](backend/docs/api.md)

---

## 🎯 Roadmap

- [ ] Multi-language support
- [ ] Email thread tracking
- [ ] Advanced RAG with policy versioning
- [ ] Workflow automation rules
- [ ] Email categorization auto-tags
- [ ] Performance metrics dashboard

---

**Built with ❤️ for secure, compliant email intelligence**
