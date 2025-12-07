# 🏛️ Skarbnik AI - Agentic Budget Orchestration Platform

**An intelligent layer between users and the rigid legal framework of Polish public finance.**

## 🎯 The Problem

The budget planning process at Ministry of Digitalization (Ministerstwo Cyfryzacji) involves:
- **~600 rows** in Excel files scattered across **16 departments**
- Manual splitting and merging of files leading to **version conflicts**
- Strict adherence to classification codes (Część, Dział, Rozdział, Paragraf)
- A painful **Cutting Phase** when Ministry of Finance imposes hard limits
- Manual compliance checking against multiple PDF regulations

## 💡 The Solution: Skarbnik AI

### 1. 📊 Anti-Excel Database
Instead of passing Excel files via email, we ingest data into a **structured SQL database** that:
- Maintains a single source of truth
- Tracks all changes with full audit trail
- Eliminates version conflicts

### 2. 🖥️ Generative UI for Departments
Each Department Director gets a **personalized web form** showing only their budget entries with:
- **Real-time validation** against department limits
- **Immediate feedback** on over-limit attempts
- One-click submission to central system

### 3. ✅ Compliance Agent (The "Guardrail")
A **RAG-based validator** that checks every entry against regulations:
- **Wyciąg nr 2c**: Paragraf classifications (4xxx = current, 6xxx = investment)
- **Wyciąg nr 2e**: Expenditure groups
- **Auto-correction**: Suggests correct paragraf codes
- Example: Detects "Server Purchase" wrongly classified under 4210 → suggests 6060

### 4. 📈 Limit Negotiator Agent
When the Ministry of Finance cuts the budget, this agent:
- Analyzes **obligatory vs discretionary** spending
- Suggests which items to **defer** to next year
- Recommends **partial reductions** for medium-priority items
- **Protects** legal requirements and cybersecurity tasks

### 5. 🔄 Conflict Resolution Agent
Detects **semantic duplicates** across departments:
- Department A and B both request "Microsoft Office licenses"
- Suggests **consolidation** for bulk purchase savings (~15%)
- Prevents duplicate spending

### 6. 📄 Bureaucrat Agent (Document Generation)
Automated **official correspondence** synchronized with live data:
- **Limit notification letters** (Pisma o limitach)
- **Cut notification letters** when reductions are required
- **Budget justification narratives** for audits
- **Summary reports** for leadership
- Eliminates risk of data mismatch between "numbers" and "official letters"

### 7. 🧠 Orchestrator Agent (AI Brain) - NEW!
**Central intelligence** coordinating all agents:
- **Situational Analysis** - What phase are we in? What's critical?
- **Next Action Suggestions** - AI-driven recommendations
- **Workflow Coordination** - Invoke agents in optimal sequence
- **Risk Assessment** - Identify blocking issues before they escalate
- **Dashboard Intelligence** - Smart KPIs with context

### 8. 📈 Forecaster Agent (Predictions) - NEW!
**Multi-year budget intelligence**:
- **Trend Analysis** - Predict budget needs for 2026-2029
- **Category Growth Modeling** - Cybersecurity vs Maintenance patterns
- **Anomaly Detection** - Statistical outliers and missing data
- **Optimal Allocation** - Shift spending across years to fit limits

## 🏗️ Technical Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Frontend (React + Vite)                        │
│    Dashboard │ Departments │ Entries │ Documents │ AI Insights         │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │ REST API
┌─────────────────────────────┴───────────────────────────────────────────┐
│                          Backend (FastAPI)                              │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    🧠 ORCHESTRATOR AGENT                           │ │
│  │         Central Intelligence - Coordinates All Agents              │ │
│  │   Situational Analysis │ Next Actions │ Workflow Execution         │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    │                                     │
│  ┌────────────────┬────────────────┬────────────────┬────────────────┐  │
│  │  Ingestion     │  Compliance    │ Optimization   │  Forecaster    │  │
│  │  Agent         │  Agent         │ Agent          │  Agent         │  │
│  │  Excel → DB    │  PDF Rules     │ Smart Cuts     │  Predictions   │  │
│  └────────────────┴────────────────┴────────────────┴────────────────┘  │
│  ┌────────────────┬────────────────┬────────────────┐                   │
│  │  Conflict      │  Document      │  Export        │                   │
│  │  Agent         │  Agent         │  Agent         │                   │
│  │  Duplicates    │  Letters       │  Excel/Word    │                   │
│  └────────────────┴────────────────┴────────────────┘                   │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────────────────┐
│                        SQLite / PostgreSQL                              │
│  budget_entries │ departments │ classifications │ audit_log │ limits  │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+

### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Load Demo Data
Navigate to http://localhost:5173 and click **"Załaduj Dane Demo"** or:
```bash
curl -X POST http://localhost:8000/api/ingest/demo
```

## 📁 Project Structure

```
budzet/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── ingestion_agent.py     # Excel → DB transformation
│   │   │   ├── compliance_agent.py    # Regulation validation
│   │   │   ├── optimization_agent.py  # Budget cut suggestions
│   │   │   └── conflict_agent.py      # Duplicate detection
│   │   ├── models.py                  # SQLAlchemy models
│   │   ├── schemas.py                 # Pydantic schemas
│   │   ├── database.py                # DB configuration
│   │   └── main.py                    # FastAPI application
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx          # Main dashboard
│   │   │   ├── Optimization.jsx       # Limit Negotiator UI
│   │   │   ├── Compliance.jsx         # Compliance validation UI
│   │   │   ├── Conflicts.jsx          # Conflict resolution UI
│   │   │   ├── Departments.jsx        # Generative UI for directors
│   │   │   └── Entries.jsx            # Budget entries management
│   │   ├── services/api.js            # API client
│   │   ├── App.jsx                    # Main app component
│   │   └── index.css                  # Design system
│   └── package.json
└── docs/                              # Source PDF regulations & Excel
```

## 🔑 Key Features Demo

### Dashboard
- Budget overview with limit vs. actual comparison
- Warning indicators for over-budget situations
- Quick access to all AI agents

### Limit Negotiator
- **Gap Analysis**: Shows exactly how much over budget
- **Priority Breakdown**: Obligatory, High, Medium, Low, Discretionary
- **Smart Suggestions**: Defer or reduce items based on priority and keywords
- **Protected Items**: Never suggests cutting legal requirements or cybersecurity

### Compliance Agent  
- Validates paragraf codes against Rozporządzenie MF
- Detects investment (6xxx) vs. current (4xxx) misclassification
- Auto-suggests corrections with explanations

### Conflict Resolution
- Semantic similarity detection (using text analysis)
- Suggests consolidation for bulk purchase savings
- Resolution workflow: Consolidate, Keep Both, or Defer One

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/dashboard/stats` | GET | Dashboard statistics |
| `/api/ingest/demo` | POST | Load demo data |
| `/api/entries` | GET | List budget entries |
| `/api/departments/{code}/entries` | GET | Department-specific view |
| `/api/compliance/validate-all` | POST | Run compliance validation |
| `/api/optimization/suggest-cuts` | POST | Generate cut suggestions |
| `/api/conflicts/detect` | POST | Detect duplicates |
| `/api/export/excel` | GET | Export to Excel (.xlsx) |
| `/api/export/word/limit-letter/{dept}` | GET | Export limit letter to Word (.docx) |
| `/api/export/word/summary-report` | GET | Export summary report to Word |
| `/api/departments/{code}/deadline` | PUT | Set edit deadline |
| `/api/departments/{code}/lock` | PUT | Lock/unlock department edits |
| `/api/entries/{id}/submit` | POST | Submit with hard validation |
| `/api/entries/submit-all` | POST | Submit all entries with validation |

## 🎓 Regulations Implemented

- **Wyciąg nr 1** - Klasyfikacja części budżetowych (Część 27 = MC)
- **Wyciąg nr 2a** - Klasyfikacja działów
- **Wyciąg nr 2b** - Klasyfikacja rozdziałów  
- **Wyciąg nr 2c** - Klasyfikacja paragrafów (key for validation!)
- **Wyciąg nr 2e** - Grupy wydatków

## 🏆 Why This Wins

1. **Solves Real Problems**: Not just "chat with Excel" - addresses actual workflow bottlenecks
2. **Regulatory Compliance**: Built-in knowledge of Polish public finance law
3. **Strategic Decision Support**: Automation of "cutting phase" decision making
4. **State Management**: Replaces email-based file passing with proper workflow
5. **Conflict Prevention**: Catches duplicates before they waste money

## 👥 Team

Built for the Hackathon by leveraging:
- FastAPI for high-performance backend
- React + Vite for modern frontend
- SQLAlchemy for database abstraction
- Pandas for Excel processing

---

**🏛️ Skarbnik AI** - *Turning budget chaos into organized finance*
