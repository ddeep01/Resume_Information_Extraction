# Recruiter-Based Resume Shortlisting & Ranking System

An end-to-end production-oriented system for recruiters to create recruitment sessions, set candidate criteria, upload batch ZIP resume archives, automatically extract structured candidate data using LLMs, classify institution and publication venue tiers, evaluate eligibility, calculate component scores, rank candidates, and review shortlisted profiles via a modern Web UI.

---

## 1. System Architecture

```text
Recruiter Web UI
       │
       ▼
FastAPI REST API (/api/sessions)
       │
       ▼
Recruitment Session Manager & Storage (data/sessions/SES-2026-XXXX/)
       │
       ├─► Safe ZIP Extraction & File Discovery (PDF/DOCX)
       ├─► Text Extraction (PyMuPDF -> PDFMiner -> OCR Fallback | python-docx)
       ├─► Text Preprocessing (Unicode NFKC, Control Chars, Hyphen Wrapping, Bullets)
       ├─► LLM Structured Extraction (Abstracted LLM Provider: Ollama / OpenAI / Fallback)
       ├─► Institution Tier Classifier (LLM + Persistent Cache: Tier 1/2/3)
       ├─► Publication Venue Tier Classifier (LLM + Persistent Cache: Tier 1/2/3)
       ├─► Eligibility Filter (Degree, Specialization, Experience, Publication Window)
       ├─► Candidate Scoring Engine (Education, Publication, Academic & Industry Exp)
       ├─► Ranking Engine (Sort by Final Score, Top-N Shortlist Assignment)
       └─► Audit Persistence (SQLite DB + Detailed JSON artifacts)
```

---

## 2. Directory Structure

```text
e:/LLM_Based_Extraction/
├── backend/
│   └── app/
│       ├── main.py                     # FastAPI main application
│       ├── config.py                   # Global settings and env configuration
│       ├── api/                        # API routes (sessions, candidates, shortlist)
│       │   ├── router.py
│       │   ├── sessions.py
│       │   └── candidates.py
│       ├── models/                     # SQLite database ORM & schemas
│       │   ├── database.py
│       │   ├── session.py
│       │   └── candidate.py
│       ├── schemas/                    # Pydantic data schemas
│       │   ├── recruiter.py
│       │   ├── candidate.py
│       │   └── results.py
│       ├── pipeline/                   # Extraction & Preprocessing pipeline
│       │   ├── pdf_extractor.py
│       │   ├── docx_extractor.py
│       │   ├── preprocessor.py
│       │   └── orchestrator.py
│       ├── llm/                        # Provider Abstraction & Extraction
│       │   ├── base.py
│       │   ├── ollama_provider.py
│       │   ├── remote_provider.py
│       │   ├── extraction.py
│       │   └── prompts.py
│       ├── classification/             # Tier 1/2/3 Classifiers & Caches
│       │   ├── institution_classifier.py
│       │   └── publication_classifier.py
│       ├── shortlisting/               # Matching, Scoring & Ranking logic
│       │   ├── degree_matcher.py
│       │   ├── specialization_matcher.py
│       │   ├── eligibility.py
│       │   ├── scoring.py
│       │   └── ranking.py
│       ├── services/                   # Business logic services
│       │   ├── session_service.py
│       │   ├── zip_service.py
│       │   └── candidate_service.py
│       └── workers/                    # Asynchronous background processing worker
│           └── processing_worker.py
│
├── frontend/                           # Recruiter Web Dashboard
│   ├── css/
│   │   └── app.css                     # Dark mode modern design system
│   ├── js/
│   │   └── app.js                      # Application state & API integration
│   └── index.html                      # Single page web interface
│
├── data/                               # Session-isolated data storage
│   ├── sessions/                       # Session data (SES-2026-XXXX)
│   ├── cache/                          # Persistent caches (institutions.json, publication_venues.json)
│   └── test_resumes/                   # Sample ZIP archives for testing
│
├── tests/                              # Pytest automated test suite
│   ├── test_pipeline.py
│   ├── test_shortlisting.py
│   └── test_api.py
│
├── .env.example
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## 3. Processing Stages

Each resume batch progresses through 10 stages:

1. **ZIP Extraction**: Safely unpacks uploaded ZIP file with path-traversal protection.
2. **Text Extraction**: Converts PDF (PyMuPDF -> PDFMiner -> OCR fallback) and DOCX files into raw text.
3. **Text Cleaning**: Normalizes Unicode NFKC, removes control characters, fixes hyphenated word linebreaks, and normalizes space/bullet symbols.
4. **LLM Structured Extraction**: Passes cleaned text to LLM to extract JSON matching Pydantic schema (Personal info, Education, Publications, Experience).
5. **Institution Classification**: Classifies each university into Tier 1 (1.00), Tier 2 (0.66), or Tier 3 (0.33) with persistent caching.
6. **Publication Venue Classification**: Classifies each publication venue into Tier 1 (1.00), Tier 2 (0.66), or Tier 3 (0.33) with persistent caching.
7. **Experience Processing**: Separates Academic and Industry experience and calculates exact duration in years.
8. **Eligibility Filtering**: Verifies mandatory recruiter criteria (Degree, Specialization, Min Experience, Min Publications in Window).
9. **Candidate Scoring**: Computes normalized component scores (0.0 to 1.0) and computes weighted `final_score` (0 to 100).
10. **Ranking & Shortlisting**: Ranks eligible candidates by final score descending, selects Top-N candidates as `SHORTLISTED`, and stores results.

---

## 4. Scoring Formulas

$$\text{Final Score} = \left( S_{\text{edu}} \cdot W_{\text{edu}} + S_{\text{pub}} \cdot W_{\text{pub}} + S_{\text{acad}} \cdot W_{\text{acad}} + S_{\text{ind}} \cdot W_{\text{ind}} \right) \times 100$$

Where:
- $S_{\text{edu}}$ = Weighted average of institution tier scores (Tier 1 = 1.0, Tier 2 = 0.66, Tier 3 = 0.33) across PhD (50%), PG (30%), and UG (20%).
- $S_{\text{pub}}$ = Combination of publication quantity score (40%) and venue tier average (60%) within publication time window.
- $S_{\text{acad}}$ = Academic experience duration score (50%) + academic institution tier score (50%).
- $S_{\text{ind}}$ = Industry experience duration score capped at 8 years.
- $W_{\text{edu}}, W_{\text{pub}}, W_{\text{acad}}, W_{\text{ind}}$ = Recruiter configured weights (must sum to 100%). Default: 35%, 30%, 20%, 15%.

---

## 5. Local Execution Guide

### Prerequisites
- Python 3.9+
- Pip & Virtual Environment

### Step 1: Clone & Setup Environment
```bash
git clone https://github.com/your-org/LLM_Based_Extraction.git
cd LLM_Based_Extraction

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default `.env` configuration:
```ini
LLM_PROVIDER="ollama"
LLM_MODEL="llama3.2"
LLM_BASE_URL="http://localhost:11434"
```

### Step 3: Start LLM Service (Ollama)
```bash
ollama run llama3.2
```

### Step 4: Launch FastAPI Backend Server
```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 5: Open Recruiter Web UI
Open your browser and navigate to:
```text
http://localhost:8000/
```

---

## 6. Lightning AI GPU Deployment Guide

To deploy and run the system on **Lightning AI Studio** (GPU Cloud Environment):

### Step 1: Create a Lightning AI Studio
1. Log in to [Lightning AI Studio](https://lightning.ai/).
2. Click **New Studio**.
3. Select a GPU tier (e.g. **T4**, **A10G**, or **L4** GPU).

### Step 2: Clone Repository in Studio Terminal
```bash
cd ~
git clone <your-repo-url> LLM_Based_Extraction
cd LLM_Based_Extraction
```

### Step 3: Set Up Python Virtual Environment & OCR Dependencies
```bash
# System dependencies for PDF & OCR support
sudo apt-get update && sudo apt-get install -y tesseract-ocr libtesseract-dev poppler-utils

# Create python venv
python3 -m venv venv
source venv/bin/activate

# Install python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Install & Start Ollama on GPU Studio
```bash
# Install Ollama CLI
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama server in background
ollama serve &

# Pull LLM model
ollama pull llama3.2
```

### Step 5: Configure `.env` for Cloud Execution
```bash
cp .env.example .env
```

### Step 6: Start FastAPI Server & Expose Port 8000
```bash
python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```
In Lightning AI Studio UI, open the **Ports** tab and expose port **8000**. Open the public URL provided by Lightning AI to access the Recruiter Dashboard.

---

## 7. Automated Testing Suite

To run all automated unit and integration tests:

```bash
# Run pytest test suite
python -m pytest -v
```

Expected output:
```text
tests/test_api.py::test_health_check PASSED                              [ 10%]
tests/test_api.py::test_create_and_get_session PASSED                    [ 20%]
tests/test_api.py::test_upload_and_status PASSED                         [ 30%]
tests/test_pipeline.py::test_text_cleaner PASSED                         [ 40%]
tests/test_pipeline.py::test_docx_extractor_non_existent PASSED          [ 50%]
tests/test_pipeline.py::test_pdf_extractor_non_existent PASSED           [ 60%]
tests/test_shortlisting.py::test_degree_normalization PASSED             [ 70%]
tests/test_shortlisting.py::test_degree_matching PASSED                  [ 80%]
tests/test_shortlisting.py::test_specialization_matching PASSED          [ 90%]
tests/test_shortlisting.py::test_scoring_and_ranking PASSED              [100%]
```

---

## 8. API Specification

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/sessions` | Create a new recruitment session |
| `GET` | `/api/sessions` | List all recruitment sessions |
| `GET` | `/api/sessions/{session_id}` | Get session details & configuration |
| `POST` | `/api/sessions/{session_id}/upload` | Upload resumes ZIP archive |
| `POST` | `/api/sessions/{session_id}/start` | Start asynchronous resume processing |
| `GET` | `/api/sessions/{session_id}/status` | Get real-time processing stage & progress |
| `GET` | `/api/sessions/{session_id}/candidates` | List candidates (with search, filter, sort) |
| `GET` | `/api/sessions/{session_id}/shortlist` | Get shortlisted Top-N candidates |
| `GET` | `/api/sessions/{session_id}/candidates/{candidate_id}` | Get complete candidate profile detail |

---

## 9. Troubleshooting & FAQ

- **LLM Connection Error (`Ollama API request error`)**:
  - Verify Ollama is running using `ollama list` or `curl http://localhost:11434`.
  - If Ollama is offline, the system automatically uses the internal fallback parser so processing is never interrupted.
- **Port 8000 already in use**:
  - Launch uvicorn on another port: `python -m uvicorn backend.app.main:app --port 8080`.
- **Missing OCR dependencies on Linux**:
  - Run `sudo apt-get install -y tesseract-ocr poppler-utils`.

---

## 10. Future Scalability Roadmap

1. **Database Migration**: Migrate SQLite database layer to **PostgreSQL** by updating connection string in `config.py`.
2. **Task Queue Migration**: Migrate background threads in `processing_worker.py` to **Celery + Redis**.
3. **Object Storage**: Move local file directories (`data/sessions/`) to **AWS S3** or **Google Cloud Storage**.
4. **Remote LLM Endpoints**: Switch `LLM_PROVIDER=openai` or use vLLM / HuggingFace TGI endpoints.
