# PROJECT_STRUCTURE.md

---

| Field               | Value                                                          |
|---------------------|----------------------------------------------------------------|
| **Project Name**    | LLM-Based Faculty Resume Information Extraction System         |
| **Documentation Date** | 2026-08-12                                                  |
| **Purpose**         | Automated extraction of structured data from faculty PDF resumes using local LLMs |
| **Current Architecture** | Batch Python pipeline + static HTML/JS frontend          |
| **Current Status**  | Research / College Demo — not production-ready                 |
| **Entry Points**    | `backend/extraction/pdf_extractor.py` → `backend/text_cleaning/cleaner.py` → `backend/llm/extractor.py` |

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Project Goals](#2-project-goals)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Complete Directory Structure](#4-complete-directory-structure)
5. [Technology Stack](#5-technology-stack)
6. [End-to-End Data Flow](#6-end-to-end-data-flow)
7. [Pipeline Architecture](#7-pipeline-architecture)
8. [Detailed Module Documentation](#8-detailed-module-documentation)
9. [Resume Text Extraction](#9-resume-text-extraction)
10. [Text Cleaning](#10-text-cleaning)
11. [LLM Extraction System](#11-llm-extraction-system)
12. [Extraction Schema](#12-extraction-schema)
13. [Validation System](#13-validation-system)
14. [Deduplication](#14-deduplication)
15. [State Management](#15-state-management)
16. [Error Handling & Retry Strategy](#16-error-handling--retry-strategy)
17. [Logging & Monitoring](#17-logging--monitoring)
18. [Configuration Management](#18-configuration-management)
19. [Input and Output Structure](#19-input-and-output-structure)
20. [Frontend / UI](#20-frontend--ui)
21. [Database / Persistence](#21-database--persistence)
22. [Dependencies](#22-dependencies)
23. [Runtime Requirements](#23-runtime-requirements)
24. [How to Run the Current Project](#24-how-to-run-the-current-project)
25. [Current Automation](#25-current-automation)
26. [Production Readiness Assessment](#26-production-readiness-assessment)
27. [Known Limitations](#27-known-limitations)
28. [Potential Production Improvements](#28-potential-production-improvements)
29. [Security Considerations](#29-security-considerations)
30. [Scalability](#30-scalability)
31. [Testing](#31-testing)
32. [Deployment Architecture](#32-deployment-architecture)
33. [Developer Guide](#33-developer-guide)
34. [Complete Execution Example](#34-complete-execution-example)
35. [Architecture Summary](#35-architecture-summary)

---

## 1. Project Overview

**Project Name:** LLM-Based Faculty Resume Information Extraction System

**Purpose:**  
An automated end-to-end pipeline that reads raw faculty resume PDFs, extracts meaningful text, cleans and normalizes it, sends it to a locally running Large Language Model (LLM) via Ollama, and produces structured JSON output. A static web frontend visualizes the extracted data as an interactive faculty intelligence dashboard.

**Problem it Solves:**  
Faculty resumes exist as unstructured PDFs with inconsistent formats, fonts, and structures. Manually extracting and standardizing information (name, designation, degrees, work history, publication counts) across dozens of resumes is time-consuming and error-prone. This system automates that extraction, enforcing a consistent JSON schema and providing a visual interface for browsing the results.

**Target Users:**  
- College administrators or HR departments browsing faculty academic profiles
- Academic researchers evaluating LLM extraction capability on Indian faculty resumes
- Students and developers exploring LLM-based information extraction pipelines

**Main Functionality:**
- PDF text extraction from faculty resumes (dual-engine: PyMuPDF primary, pdfplumber fallback)
- 9-stage deterministic text normalization pipeline
- Structured JSON extraction using a locally hosted LLM (via Ollama)
- Recursive JSON schema validation and repair
- SHA-256 hash-based duplicate file detection
- Benchmarking suite comparing extraction quality (text fidelity + LLM accuracy)
- Glassmorphism web dashboard for searching, filtering, and viewing faculty profiles

**Current Project Maturity:**  
Research / College Demo. The pipeline is functional for a fixed dataset of 40 resumes. Multiple bugs exist in the frontend JavaScript. No backend HTTP server or authentication exists. Not suitable for production deployment without significant rework.

**Main Technologies:**  
Python 3.9+, PyMuPDF (`fitz`), pdfplumber, Ollama (local LLM inference), LLaMA 3.1 8B / Qwen 2.5 7B / Mistral 7B, HTML5, Vanilla CSS3, JavaScript ES6+, Chart.js, FontAwesome

---

## 2. Project Goals

### Currently Implemented Goals

- ✅ PDF text extraction from resume files with dual-engine fallback (PyMuPDF → pdfplumber)
- ✅ Deterministic 9-stage text cleaning pipeline (Unicode normalization, whitespace, bullets, hyphens)
- ✅ LLM invocation via Ollama with zero-temperature JSON-mode inference
- ✅ Recursive JSON schema validation with default-value repair and unknown-key stripping
- ✅ Retry logic at both HTTP and validation levels (up to 3 attempts per resume)
- ✅ SHA-256 hash-based duplicate detection (utility exists; not integrated into the main pipeline)
- ✅ Invalid response logging (raw LLM output saved to `data/invalid_json/`)
- ✅ Batch processing of a directory of cleaned resume text files
- ✅ Static web dashboard with faculty directory, search, filters, and profile detail view
- ✅ Dark/light theme toggle with localStorage persistence (on the index page)
- ✅ Multi-criteria filtering (degree, designation, experience range, publications)
- ✅ Benchmarking framework: text extraction accuracy (F1, CER, BLEU, NED) and LLM field accuracy (precision, recall, F1 per section)
- ✅ Comparative evaluation across multiple models (LLaMA 3.1, Qwen 2.5, Mistral 7B)
- ✅ Visualization plots for text extraction benchmark (matplotlib bar charts)

### Future / Planned Goals (Not Implemented)

- ❌ REST API server (no Flask/FastAPI backend exists)
- ❌ Dynamic file discovery (frontend hardcodes 40 files by sequential ID)
- ❌ OCR support for scanned/image-based PDFs
- ❌ Real-time resume upload from the browser
- ❌ Database persistence (no PostgreSQL, SQLite, or equivalent)
- ❌ Authentication or access control
- ❌ Automated pipeline orchestration (no Airflow, Celery, or equivalent)
- ❌ Dark/light theme toggle on the faculty profile page
- ❌ Parallel LLM processing

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND PIPELINE (Python)                   │
│                        (Run manually)                           │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────┐  │
│  │ Raw Resume   │    │ SHA-256      │    │  PDF Text         │  │
│  │ PDFs         │───►│ Deduplication│───►│  Extraction       │  │
│  │ data/raw_    │    │ hash_checker │    │  pdf_extractor.py │  │
│  │ resumes/     │    │ .py          │    │                   │  │
│  └──────────────┘    └──────────────┘    └────────┬──────────┘  │
│                                                   │             │
│                                                   ▼             │
│                                          ┌─────────────────┐    │
│                                          │  Text Cleaning  │    │
│                                          │  cleaner.py     │    │
│                                          │  (9-stage pipe) │    │
│                                          └────────┬────────┘    │
│                                                   │             │
│                                                   ▼             │
│                                          ┌─────────────────┐    │
│                                          │  Prompt Builder │    │
│                                          │  prompt.py      │    │
│                                          └────────┬────────┘    │
│                                                   │             │
│                                                   ▼             │
│                                          ┌─────────────────┐    │
│                                          │  Ollama LLM     │    │
│                                          │  (local server) │    │
│                                          │  LLaMA/Qwen/    │    │
│                                          │  Mistral        │    │
│                                          └────────┬────────┘    │
│                                                   │             │
│                                                   ▼             │
│                                          ┌─────────────────┐    │
│                                          │  JSON Validator │    │
│                                          │  validator.py   │    │
│                                          └────────┬────────┘    │
│                                                   │             │
│                                                   ▼             │
│                             ┌─────────────────────────────────┐ │
│                             │  data/extracted_json/R-XXX.json │ │
│                             └──────────────┬────────────────── ┘ │
└──────────────────────────────────────────┬─┘                    │
                                           │
          ┌────────────────────────────────┘
          │  (Manual copy / pre-populated)
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  EVALUATION FRAMEWORK (Python)                  │
│                                                                 │
│  ┌────────────────────────┐   ┌────────────────────────────┐   │
│  │ Text Extraction Bench  │   │ LLM Accuracy Benchmark     │   │
│  │ evaluate.py / metrics  │   │ evaluate_json.py /         │   │
│  │ .py / generate_plots   │   │ metrics_json.py            │   │
│  │ F1, CER, BLEU, NED     │   │ Precision/Recall/F1        │   │
│  └────────────────────────┘   └────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
          │
          │  JSON results served as static files
          ▼
┌─────────────────────────────────────────────────────────────────┐
│               FRONTEND DASHBOARD (HTML/CSS/JS)                  │
│                   (Static file serving)                         │
│                                                                 │
│  ┌─────────────────────────┐   ┌──────────────────────────┐    │
│  │  index.html             │   │  faculty.html            │    │
│  │  Dashboard Overview     │   │  Faculty Profile Detail  │    │
│  │  ┌─────────────────┐   │   │  ┌────────────────────┐  │    │
│  │  │ loader.js       │   │   │  │ faculty.js         │  │    │
│  │  │ app.js          │   │   │  │ (tabs, modal,      │  │    │
│  │  │ filters.js      │   │   │  │  download, resume) │  │    │
│  │  │ search.js       │   │   │  └────────────────────┘  │    │
│  │  │ dashboard.js    │   │   └──────────────────────────┘    │
│  │  └─────────────────┘   │                                    │
│  └─────────────────────────┘                                    │
│                                                                 │
│  fetch() ──► evaluation/result_llm/data/qwen2.5_7b/R-XXX.json  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Summary

| Component | Technology | Role |
|-----------|-----------|------|
| PDF Extractor | PyMuPDF, pdfplumber | Extracts raw text from PDF resumes |
| Text Cleaner | Python / regex / unicodedata | Normalizes extracted text |
| Prompt Builder | Python / string formatting | Constructs structured LLM messages |
| LLM Extractor | Ollama Python client | Calls local LLM and collects JSON |
| JSON Validator | Python / json / regex | Parses, repairs, and validates LLM output |
| Hash Checker | Python / hashlib | Detects duplicate PDF files |
| Text Benchmark | rapidfuzz, jiwer, nltk | Measures PDF extraction quality |
| LLM Benchmark | rapidfuzz, pandas | Measures field-level extraction accuracy |
| Frontend Dashboard | HTML5 / Vanilla CSS / JS | Interactive visualization of extracted data |

---

## 4. Complete Directory Structure

```
LLM_Based_Extraction/
│
├── backend/                          # Python processing pipeline
│   ├── deduplication/
│   │   └── hash_checker.py           # SHA-256 file hash utilities
│   ├── extraction/
│   │   └── pdf_extractor.py          # PDF → plain text (PyMuPDF + pdfplumber)
│   ├── text_cleaning/
│   │   ├── cleaner.py                # 9-stage text normalization pipeline
│   │   ├── cleaning_report.py        # Per-file cleaning statistics report
│   │   └── report/                   # Generated JSON statistics (runtime output)
│   │       └── cleaning_statistics.json
│   ├── llm/
│   │   ├── prompt.py                 # System prompt, rules, and JSON schema builder
│   │   ├── validator.py              # LLM response cleaner, parser, schema validator
│   │   └── extractor.py              # Ollama client wrapper, retry loop, batch runner
│   └── utils.py                      # Shared path constants (partially unused)
│
├── data/                             # All data files (NOT committed to git ideally)
│   ├── raw_resumes/                  # Input PDF files (R-001.pdf … R-040.pdf)
│   ├── extracted_text/               # Stage 2 output: raw text per resume (.txt)
│   ├── cleaned_text/                 # Stage 3 output: cleaned text per resume (.txt)
│   ├── extracted_json/               # Stage 4 output: validated LLM JSON (.json)
│   ├── invalid_json/                 # LLM responses that failed parsing (for debugging)
│   ├── ground_truth/                 # Human-verified reference text (R-001.txt…R-010.txt)
│   ├── csv_output/                   # (Directory exists; no generator script found)
│   └── json_output/                  # (Directory exists; no generator script found)
│
├── evaluation/
│   ├── result_text_extraction/       # Text extraction benchmark
│   │   ├── extractor.py              # Runs PyMuPDF, pdfplumber, pdfminer on R-001..R-010
│   │   ├── extract_test_files.py     # Copies ground-truth and extracted text for eval
│   │   ├── metrics.py                # F1, CER, NED, BLEU metric functions
│   │   ├── evaluate.py               # Runs metrics across all tools and resumes
│   │   ├── generate_plots.py         # Produces matplotlib bar charts from CSV results
│   │   ├── data/
│   │   │   ├── ground_truth/         # Reference text files (10 resumes)
│   │   │   ├── pymupdf/              # PyMuPDF extracted text files
│   │   │   ├── pdfplumber/           # pdfplumber extracted text files
│   │   │   └── pdfminer/             # pdfminer extracted text files
│   │   ├── results/                  # per_resume_metrics.csv, summary_metrics.csv
│   │   └── plots/                    # f1_comparison.png, cer_comparison.png, etc.
│   │
│   └── result_llm/                   # LLM extraction benchmark
│       ├── evaluate_json.py          # Compares LLM output JSON against ground-truth JSON
│       ├── metrics_json.py           # fuzzy field similarity, P/R/F1 for lists
│       ├── data/
│       │   ├── ground_truth/         # Human-verified JSON files (R-001.json…R-010.json)
│       │   ├── llama3.1_8b/          # LLaMA 3.1 8B output JSONs (R-001..R-040.json)
│       │   ├── mistral_7b/           # Mistral 7B output JSONs
│       │   └── qwen2.5_7b/           # Qwen 2.5 7B output JSONs (39 files; R-019 missing)
│       └── results/                  # per_resume_metrics.csv, summary_metrics.csv
│
├── frontend/                         # Static web dashboard
│   ├── index.html                    # Dashboard overview page
│   ├── faculty.html                  # Individual faculty profile page
│   ├── css/
│   │   ├── style.css                 # Global CSS variables, layout, header, buttons
│   │   ├── cards.css                 # Faculty card grid and card component styles
│   │   ├── dashboard.css             # Metric card styles for stat numbers
│   │   ├── faculty.css               # Faculty profile page full stylesheet
│   │   └── responsive.css            # Responsive breakpoints (1500/1200/992/768/480px)
│   ├── js/
│   │   ├── loader.js                 # Data loading, state management, stats computation
│   │   ├── app.js                    # Stats card rendering, faculty card rendering, filter init
│   │   ├── filters.js                # Filter panel logic, candidate filtering
│   │   ├── search.js                 # Real-time search input listener
│   │   ├── dashboard.js              # ⚠️ Broken orphan file — fragment, not callable
│   │   └── faculty.js                # Faculty profile page: data loading, tab switching, JSON modal
│   ├── assets/                       # (Directory exists; empty)
│   └── components/                   # (Directory exists; empty)
│
├── logs/
│   └── llm_extraction.log            # Runtime log from extractor.py (UTF-8)
│
├── requirements.txt                  # Python dependencies (incomplete — see Section 22)
├── .gitignore                        # Ignores __pycache__, .env, venv (not data/ or logs/)
├── README.md                         # Project overview and usage guide
└── venv/                             # Local Python virtual environment (should be gitignored)
```

### Key Files By Role

| File | Role |
|------|------|
| `backend/llm/extractor.py` | Main pipeline entry point for LLM extraction |
| `backend/extraction/pdf_extractor.py` | Stage 2: PDF → text |
| `backend/text_cleaning/cleaner.py` | Stage 3: Text normalization |
| `backend/llm/prompt.py` | Prompt template + extraction schema definition |
| `backend/llm/validator.py` | JSON parsing and schema enforcement |
| `backend/deduplication/hash_checker.py` | SHA-256 duplicate detection utility |
| `evaluation/result_llm/evaluate_json.py` | LLM accuracy benchmark runner |
| `evaluation/result_text_extraction/evaluate.py` | Text extraction benchmark runner |
| `frontend/js/loader.js` | Frontend: loads all JSON files, manages global state |
| `frontend/js/app.js` | Frontend: renders dashboard and faculty cards |
| `frontend/js/faculty.js` | Frontend: renders faculty profile detail page |

---

## 5. Technology Stack

| Technology | Version / Details | Purpose | Where Used |
|------------|------------------|---------|------------|
| Python | 3.9+ | Backend pipeline language | All `.py` files |
| PyMuPDF (`fitz`) | Latest | Primary PDF text extraction | `pdf_extractor.py`, `extractor.py` (eval) |
| pdfplumber | Not in requirements.txt | Fallback PDF extraction | `pdf_extractor.py`, `extractor.py` (eval) |
| pdfminer | Not in requirements.txt | Third extractor (evaluation only) | `extractor.py` (eval) |
| ollama (Python client) | Not in requirements.txt | Call local Ollama inference server | `extractor.py` (backend/llm) |
| Ollama (local server) | External service | LLM inference runtime | Must be installed separately |
| LLaMA 3.1 8B | Ollama model | Current active extraction model | `extractor.py` (MODEL_NAME) |
| Qwen 2.5 7B | Ollama model | Alternative extraction model (commented out) | Pre-run JSONs in `evaluation/` |
| Mistral 7B | Ollama model | Alternative extraction model (commented out) | Pre-run JSONs in `evaluation/` |
| pandas | Latest | CSV output and reporting | `cleaning_report.py`, `evaluate.py`, `evaluate_json.py` |
| rapidfuzz | Latest | Fuzzy string matching for evaluation | `metrics_json.py`, `metrics.py` |
| jiwer | Latest | Character Error Rate (CER) metric | `metrics.py` |
| nltk | Latest | BLEU score computation | `metrics.py` |
| matplotlib | Latest | Bar chart generation for benchmarks | `generate_plots.py` |
| python-docx | Listed in requirements | Word document support (not actively used in pipeline) | Listed only |
| tqdm | Listed in requirements | Progress bars (not used in current code) | Listed only |
| python-dotenv | Listed in requirements | `.env` file loading (no `.env` file exists) | Listed only |
| hashlib | Python stdlib | SHA-256 file hashing | `hash_checker.py` |
| unicodedata | Python stdlib | Unicode NFKC normalization | `cleaner.py` |
| pathlib | Python stdlib | Cross-platform path handling | All `.py` files |
| logging | Python stdlib | Log file and console output | `extractor.py`, `cleaner.py` |
| json | Python stdlib | JSON parsing and serialization | `validator.py`, `extractor.py`, all eval scripts |
| re | Python stdlib | Regex for cleaning and response parsing | `cleaner.py`, `validator.py` |
| dataclasses | Python stdlib | Config and statistics data structures | `cleaner.py`, `extractor.py` |
| HTML5 | — | Dashboard page structure | `index.html`, `faculty.html` |
| Vanilla CSS3 | — | All styling (glassmorphism, responsive) | All `.css` files |
| JavaScript ES6+ | — | Frontend logic, data loading, rendering | All `.js` files |
| Chart.js | CDN (jsdelivr) | Chart support (imported but no charts rendered) | `index.html` |
| FontAwesome 6 | CDN (cdnjs) | Icon library | `index.html` (6.5.2), `faculty.html` (6.6.0) |
| Google Fonts (Inter) | CDN | Typography | Both HTML pages |

---

## 6. End-to-End Data Flow

### Step 1 — Place Raw PDF Resumes
- **Input:** PDF files named `R-001.pdf` through `R-040.pdf`
- **Location:** `data/raw_resumes/`
- **Processing:** None at this step
- **Error condition:** Missing files are silently skipped by the extractor

### Step 2 — (Optional) Duplicate Detection
- **Input:** PDF file path, hash CSV path
- **Function:** `is_duplicate_file()` in `backend/deduplication/hash_checker.py`
- **Processing:** SHA-256 hash computed in 8KB chunks; compared against `data/file_hashes.csv`
- **Output:** Boolean `(is_duplicate, hash_hex)`
- **Important:** This module exists as a utility but is **not called** by the main pipeline scripts. Integration is a manual step.
- **Error condition:** If the CSV does not exist, the function returns `False` (treats as new file)

### Step 3 — PDF Text Extraction
- **Input:** `data/raw_resumes/*.pdf`
- **Function:** `PDFExtractor.extract()` → `extract_pymupdf()` → fallback `extract_pdfplumber()`
- **Processing:**
  1. Attempt extraction with PyMuPDF (fast, layout-preserving)
  2. If extracted text length < 100 characters, fall back to pdfplumber
  3. If both fail, return empty string with method label `"failed"`
- **Output:** Plain text `.txt` files written to `data/extracted_text/`
- **Error condition:** Exceptions are caught per-PDF; failed files are printed but not retried; no log file

### Step 4 — Text Cleaning
- **Input:** `data/extracted_text/*.txt` (UTF-8, read with `errors="ignore"`)
- **Function:** `TextCleaner.clean()` in `backend/text_cleaning/cleaner.py`
- **Processing:** 9-stage deterministic normalization (see Section 10)
- **Output:** Cleaned `.txt` files written to `data/cleaned_text/`
- **Error condition:** Individual file failures increment `stats.failed`; logged via `logger.exception()`

### Step 5 — LLM Prompt Construction
- **Input:** Cleaned resume text string
- **Function:** `PromptBuilder.build_messages()` in `backend/llm/prompt.py`
- **Processing:** Builds a two-message list: `system` message (role + anti-hallucination rules) + `user` message (extraction rules + JSON schema + resume text)
- **Output:** `List[Dict]` in Ollama chat format
- **Error condition:** Raises `TypeError` if input is not a string; raises `ValueError` if input is empty

### Step 6 — LLM Invocation
- **Input:** Message list from prompt builder
- **Function:** `LLMExtractor.call_llm()` in `backend/llm/extractor.py`
- **Processing:** Calls `ollama.chat()` with `format="json"`, `temperature=0.0`, `top_p=0.8`, `num_predict=8192`; retries up to 3 times with 3-second delays
- **Output:** Raw JSON string from LLM
- **Error condition:** Any exception triggers a retry; after 3 failures returns `None`

### Step 7 — JSON Parsing and Validation
- **Input:** Raw LLM response string
- **Function:** `JSONValidator.validate()` in `backend/llm/validator.py`
- **Processing:**
  1. Strip markdown code fences and common prefix phrases
  2. Extract outermost `{ … }` substring
  3. Parse with `json.loads()`
  4. Remove unknown keys not in schema
  5. Recursively validate and repair missing/wrong-typed fields
- **Output:** Python dictionary conforming to the extraction schema
- **Error condition:** Parse failure saves raw response to `data/invalid_json/` and raises `ValueError`; outer loop in `extract_resume()` retries up to 3 times

### Step 8 — JSON Output Storage
- **Input:** Validated Python dictionary
- **Function:** `LLMExtractor.save_json()` in `backend/llm/extractor.py`
- **Processing:** `json.dumps()` with `indent=4, ensure_ascii=False`; written to `data/extracted_json/`
- **Output:** `data/extracted_json/R-XXX.json`
- **Error condition:** I/O errors propagated as exceptions, caught by outer try/except

### Step 9 — (For Evaluation) Copy to Model Directory
- **Input:** `data/extracted_json/R-XXX.json`
- **Processing:** Manually copy to `evaluation/result_llm/data/<model_name>/`
- **Note:** This step is **manual** — no script automates the copy for LLM benchmark

### Step 10 — Frontend Visualization
- **Input:** JSON files in `evaluation/result_llm/data/qwen2.5_7b/`
- **Processing:** `loader.js` fetches each file sequentially via `fetch()`; normalizes into candidate objects; `app.js` renders cards; `filters.js` handles filtering; `faculty.js` renders individual profile pages
- **Output:** Interactive browser dashboard

---

## 7. Pipeline Architecture

### 7.1 Input

Raw PDF resumes placed in `data/raw_resumes/`. Files must be named with the pattern `R-NNN.pdf` for the evaluation framework to function correctly. The main pipeline (`pdf_extractor.py`) uses `RAW_DIR.glob("*.pdf")` so any filename is accepted for extraction.

### 7.2 File Validation

**Currently:** No formal file validation. The `PDFExtractor.extract()` method wraps extraction in a try/except. If both extractors fail, the tuple `("", "failed")` is returned and the file is skipped with a console print.

**Not validated:** file type (MIME check), file size limits, password protection, corruption.

### 7.3 Deduplication

Implemented as a standalone utility in `backend/deduplication/hash_checker.py`. **Not integrated** into the main pipeline scripts. Must be called manually. See Section 14 for full details.

### 7.4 Text Extraction

Two-stage extraction implemented in `backend/extraction/pdf_extractor.py`:

1. **Primary:** `PDFExtractor.extract_pymupdf()` — uses `fitz.open()` and `page.get_text()` for each page
2. **Fallback:** `PDFExtractor.extract_pdfplumber()` — uses `pdfplumber.open()` and `page.extract_text()`
3. **Threshold:** Falls back if primary result is < 100 characters (`MIN_TEXT_LENGTH`)
4. **Failure result:** Returns `("", "failed")` — file is skipped, not retried

Note: This script uses **relative paths** (`Path("data/raw_resumes")`), unlike all other backend modules that compute absolute paths from `__file__`. It must be run from the project root directory.

### 7.5 Text Cleaning

Nine deterministic stages applied in sequence by `TextCleaner.clean()` in `backend/text_cleaning/cleaner.py`. See Section 10 for full details.

### 7.6 Prompt Building

`PromptBuilder.build_messages()` in `backend/llm/prompt.py` returns a list of two messages:

- **Message 1 (system):** Role definition + anti-hallucination instructions
- **Message 2 (user):** 21 extraction rules + the target JSON schema (serialized with `json.dumps()`) + the full resume text

The schema is embedded directly in the prompt at runtime using `self.json_schema()` which calls `json.dumps(self.schema, indent=4)`.

### 7.7 LLM Extraction

`LLMExtractor.call_llm()` calls `ollama.chat()` with:
- `model`: configured via `MODEL_NAME` constant (currently `"llama3.1:8b"`)
- `format`: `"json"` (Ollama JSON mode)
- `temperature`: `0.0` (fully deterministic)
- `top_p`: `0.8`
- `num_predict`: `8192` tokens

Outer retry loop: up to `MAX_RETRIES = 3` attempts with `RETRY_DELAY = 3` seconds between attempts.

### 7.8 JSON Parsing

`JSONValidator.clean_response()` pre-processes the raw string:
1. Removes ` ```json ` and ` ``` ` markdown fences using regex anchored to start/end
2. Strips known prefix phrases ("Here is the JSON:", "Output:", etc.)
3. Slices the string from `text.find("{")` to `text.rfind("}")` to isolate the JSON object

Then `json.loads()` is called on the cleaned string. A `json.JSONDecodeError` propagates as an exception.

### 7.9 Schema Validation

`JSONValidator.validate_schema()` → `_validate_value()` (recursive):
- **dict in schema:** ensures all schema keys are present; fills missing with default values; strips extra keys via `remove_unknown_keys()` called before this step
- **list in schema:** validates each item against `schema[0]` as the item template
- **str in schema:** coerces to `str`, returns `""` for `None`
- **int in schema:** coerces to `int`, returns schema default on failure
- **float in schema:** coerces to `float`, returns schema default on failure
- **bool in schema:** coerces to `bool`

> ⚠️ **Known Bug:** `_validate_value` and `save_invalid_response` are indented incorrectly in the current source file (inside other methods after `return` statements), making them unreachable as instance methods. The validation pipeline will raise `AttributeError` at runtime.

### 7.10 Post Processing

No post-processing step exists. The validated dictionary is passed directly to `save_json()`.

### 7.11 Output Storage

`LLMExtractor.save_json()` writes the validated dictionary as indented JSON to `data/extracted_json/R-XXX.json`. File names match the input `.txt` stem.

### 7.12 Logging

`extractor.py` configures a root logger named `"LLMExtractor"` that writes to both:
- `logs/llm_extraction.log` (file handler, UTF-8)
- Console (stream handler)

`validator.py` uses `logging.getLogger("LLMExtractor")` to share the same logger instance.

`cleaner.py` configures its own root logger named `"ResumeCleaner"` writing to console only.

### 7.13 Pipeline State

There is no persistent pipeline state. No database, no status file, no resume tracking. Each pipeline stage is a standalone script that processes whatever files are present in its input directory at run time. If a run is interrupted, it must be restarted from scratch (though already-written output files are not regenerated unless deleted).

---

## 8. Detailed Module Documentation

---

### File: `backend/extraction/pdf_extractor.py`

**Purpose:** Extracts plain text from PDF resume files using a dual-engine strategy.

**Main Classes:**
- `PDFExtractor` — static-method class encapsulating both extraction engines

**Main Functions:**
- `extract_pymupdf(pdf_path)` — opens PDF with `fitz.open()`, iterates pages, joins text with `\n`
- `extract_pdfplumber(pdf_path)` — opens PDF with `pdfplumber.open()`, calls `page.extract_text()` per page
- `extract(pdf_path)` — classmethod: tries PyMuPDF first, falls back to pdfplumber based on `MIN_TEXT_LENGTH = 100`
- `process_all_resumes()` — module-level function: globs `data/raw_resumes/*.pdf`, calls `extract()`, writes `.txt` files

**Input:** PDF files in `data/raw_resumes/` (relative path — must run from project root)

**Output:** `.txt` files in `data/extracted_text/`; returns `(text, method)` where method is `"pymupdf"`, `"pdfplumber"`, or `"failed"`

**Dependencies:** `fitz` (PyMuPDF), `pdfplumber`, `pathlib`

**Used By:** Standalone script; not imported by other pipeline modules

**Failure Handling:** Exceptions caught per engine, prints error to console, returns `""`. Failed files are printed as `[FAILED]` and skipped.

**Known Issue:** Uses `Path("data/raw_resumes")` (relative), unlike all other modules which use absolute paths via `Path(__file__).resolve().parents[N]`.

---

### File: `backend/text_cleaning/cleaner.py`

**Purpose:** Applies a nine-stage deterministic text normalization pipeline to extracted resume text.

**Main Classes:**
- `CleanerConfig` — dataclass with boolean toggles for each cleaning stage (all default `True`)
- `CleaningStatistics` — dataclass tracking per-batch statistics (documents, successful, failed, character counts, etc.)
- `TextCleaner` — core cleaner implementing all 9 stages; maintains a `CleaningStatistics` instance
- `ResumeCleaner` — higher-level wrapper: reads input directory, writes output directory, exports statistics JSON

**Main Functions (TextCleaner):**
- `normalize_unicode(text)` — NFKC normalization + 17-entry explicit replacement map (ligatures, smart quotes, dashes, bullets, zero-width chars)
- `remove_control_characters(text)` — strips `\x00–\x08`, `\x0B`, `\x0C`, `\x0E–\x1F`
- `normalize_line_endings(text)` — converts `\r\n` and `\r` to `\n`
- `fix_hyphenated_words(text)` — joins `word-\nword` line-break hyphens: pattern `([A-Za-z])-\n([A-Za-z])`
- `normalize_tabs(text)` — replaces `\t` with single space
- `normalize_spaces(text)` — collapses `2+` consecutive spaces to one
- `normalize_bullets(text)` — replaces bullet symbols `•●▪■◦►➤✓✔` with `-`; ⚠️ these were already replaced in `normalize_unicode()` so this stage is effectively a no-op and `stats.bullet_normalized` will always be 0
- `trim_trailing_spaces(text)` — `line.rstrip()` per line
- `collapse_blank_lines(text)` — reduces `3+` consecutive newlines to `\n\n`
- `clean(text)` — executes all stages in order; updates statistics

**Main Functions (ResumeCleaner):**
- `clean_file(input_file, output_file)` — reads one file, cleans, writes
- `clean_directory(input_dir, output_dir, pattern)` — iterates all `.txt` files
- `export_statistics()` — writes `backend/text_cleaning/report/cleaning_statistics.json`

**Input:** `data/extracted_text/*.txt`

**Output:** `data/cleaned_text/*.txt` (filenames preserved); `report/cleaning_statistics.json`

**Dependencies:** `pathlib`, `re`, `unicodedata`, `json`, `logging`, `dataclasses`

**Used By:** Standalone script; not imported by other pipeline modules

**Failure Handling:** Individual file failures caught; `stats.failed` incremented; exception logged

---

### File: `backend/text_cleaning/cleaning_report.py`

**Purpose:** Generates a per-resume comparison report between raw extracted text and cleaned text.

**Main Functions:**
- `analyze_file(raw_text, clean_text)` — returns dict with character/word/line counts before and after, removal deltas, compression ratio
- `main()` — iterates matched pairs from `data/extracted_text/` and `data/cleaned_text/`; produces `report/cleaning_report.csv` and `report/summary.json`

**Input:** `data/extracted_text/*.txt` and `data/cleaned_text/*.txt`

**Output:** `backend/text_cleaning/report/cleaning_report.csv`, `report/summary.json`

**Dependencies:** `pathlib`, `json`, `pandas`

**Used By:** Standalone script; run independently from `cleaner.py`

---

### File: `backend/deduplication/hash_checker.py`

**Purpose:** SHA-256 file hashing for duplicate detection.

**Main Functions:**
- `calculate_file_hash(file_path)` — reads file in 8KB chunks, returns SHA-256 hex digest
- `is_duplicate_file(file_path, hash_csv)` — checks if file hash exists in CSV; returns `(bool, hash_hex)`
- `save_file_hash(filename, file_hash, hash_csv)` — appends filename+hash row to CSV (creates if missing)

**Input:** Any file path; hash registry CSV path

**Output:** Boolean + hash string; CSV row appended on save

**Dependencies:** `hashlib`, `pandas`, `pathlib`

**Used By:** Standalone utility — **not called by any other pipeline module**; must be integrated manually

**Known Issue:** `__main__` block uses `"data/file_hashes.csv"` (relative), while `utils.py` defines the correct path as `BASE_DIR / "data" / "metadata" / "file_hashes.csv"`. These are inconsistent.

---

### File: `backend/utils.py`

**Purpose:** Shared path constants for the backend.

**Constants:**
- `BASE_DIR` — project root via `Path(__file__).resolve().parent.parent`
- `RAW_RESUME_DIR` — `BASE_DIR / "data" / "raw_resumes"`
- `EXTRACTED_DIR` — `BASE_DIR / "data" / "extracted_text"`
- `CLEANED_DIR` — `BASE_DIR / "data" / "cleaned_text"`
- `FILE_HASH_CSV` — `BASE_DIR / "data" / "metadata" / "file_hashes.csv"`
- `TEXT_HASH_CSV` — `BASE_DIR / "data" / "metadata" / "text_hashes.csv"`

**Main Functions:**
- `ensure_directories()` — creates `EXTRACTED_DIR` and `CLEANED_DIR` only (does not create `metadata/`)

**Used By:** Not imported by any current pipeline module — unused in practice

---

### File: `backend/llm/prompt.py`

**Purpose:** Constructs the complete prompt sent to the LLM. Defines the extraction schema.

**Main Classes:**
- `PromptBuilder` — holds `self.schema` dict; provides methods to build messages

**Main Functions:**
- `system_prompt()` — returns a single-paragraph string establishing the LLM's role and anti-hallucination rules
- `extraction_rules()` — returns a multi-line string of 21 numbered extraction rules (JSON format, no markdown, no hallucination, default values for missing fields, publication counts only)
- `json_schema()` — serializes `self.schema` as indented JSON string
- `build_messages(resume_text)` — validates input type/emptiness; returns `[{system}, {user}]` message list

**Schema Structure (defined in `__init__`):**
- `personal_information` dict with 11 fields
- `education` list with one template dict (6 fields)
- `experience` list with one template dict (6 fields)
- `publication_summary` dict with 5 int fields

**Input:** `resume_text: str`

**Output:** `List[Dict[str, str]]` — Ollama chat messages format

**Dependencies:** `json`, `typing`

**Used By:** `backend/llm/extractor.py` (instantiated in `LLMExtractor.__init__`), `backend/llm/validator.py` (instantiated in `JSONValidator.__init__`)

---

### File: `backend/llm/validator.py`

**Purpose:** Parses, cleans, and validates the raw JSON string returned by the LLM.

**Main Classes:**
- `JSONValidator` — holds `self.schema` (deep copy of `PromptBuilder().schema`)

**Main Functions:**
- `clean_response(response)` — removes markdown code fences, known prefix phrases; extracts `{...}` substring
- `parse_json(response)` — calls `clean_response()` then `json.loads()`
- `_validate_value(value, schema)` — recursive type coercion and default-filling (dict, list, str, int, float, bool)
- `validate_schema(data)` — calls `_validate_value(data, self.schema)`
- `remove_unknown_keys(data, schema)` — strips keys not in schema (recursive for nested dicts and lists of dicts)
- `save_invalid_response(response, file_name)` — writes raw response to `data/invalid_json/<stem>_raw.txt`
- `validate(response, file_name)` — orchestrates: parse → remove unknown keys → validate schema → return dict; on failure: saves invalid response and raises `ValueError`

**Input:** Raw LLM response string

**Output:** Validated Python dictionary matching the schema

**Dependencies:** `json`, `re`, `copy`, `logging`, `pathlib`, `prompt.PromptBuilder`

**Used By:** `backend/llm/extractor.py` (instantiated in `LLMExtractor.__init__`, called in `extract_resume()`)

**Known Bug:** `_validate_value` (line 188) and `save_invalid_response` (line 418) are indented incorrectly — they appear after `return` statements inside other methods, making them unreachable as instance methods. The validate pipeline will fail with `AttributeError` at runtime.

**Known Issue:** Uses bare import `from prompt import PromptBuilder` — only works if run from within `backend/llm/` directory.

---

### File: `backend/llm/extractor.py`

**Purpose:** Main LLM extraction orchestrator. Reads cleaned text files, calls LLM, validates output, saves JSON.

**Configuration Constants:**
- `MODEL_NAME = "llama3.1:8b"` (active; `qwen2.5:7b` and `mistral:7b` commented out)
- `REQUEST_TIMEOUT = 180` (defined but not passed to `ollama.chat()`)
- `MAX_RETRIES = 3`
- `RETRY_DELAY = 3` (seconds)
- `NUM_PREDICT = 8192`
- `TOP_P = 0.8`
- `TEMPERATURE = 0.0`

**Main Classes:**
- `LLMExtractor`

**Main Functions:**
- `check_model()` — calls `ollama.list()` to verify the model is available; returns bool
- `call_llm(resume_text)` — builds messages, calls `ollama.chat()`, returns raw content string; retries up to `MAX_RETRIES`
- `extract_resume(resume_file)` — reads `.txt` file, calls `call_llm()`, calls `validator.validate()`, calls `save_json()`; outer retry loop up to `MAX_RETRIES`
- `save_json(data, output_file)` — serializes and writes JSON
- `process_directory()` — globs `data/cleaned_text/*.txt`, calls `extract_resume()` for each; calls `check_model()` first

**Input:** `data/cleaned_text/*.txt`

**Output:** `data/extracted_json/R-XXX.json`

**Dependencies:** `ollama`, `json`, `logging`, `time`, `pathlib`, `dataclasses`, `prompt.PromptBuilder`, `validator.JSONValidator`

**Failure Handling:** Exceptions at every level are caught; logged with `logger.exception()`; processing continues to next file

**Known Issue:** `logger.info(response)` at line 248 logs the entire Ollama response object (including full extracted content) at INFO level — will accumulate PII in log files rapidly.

**Known Issue:** Bare imports `from validator import JSONValidator` and `from prompt import PromptBuilder` fail unless run from within `backend/llm/`.

---

### File: `evaluation/result_llm/metrics_json.py`

**Purpose:** Provides metric functions for comparing LLM-extracted JSON against ground-truth JSON.

**Main Functions:**
- `field_similarity(gt_val, pred_val)` — fuzzy string similarity using `rapidfuzz.fuzz.ratio`; returns `None` if GT is empty (not scored), `0.0` if prediction is empty but GT has value
- `object_similarity(gt_obj, pred_obj, fields)` — averages `field_similarity()` across given field names for a dict pair
- `match_list_entries(gt_list, pred_list, key_fields, match_threshold=0.5)` — greedy bipartite matching of list entries using key field similarity
- `list_of_dicts_score(gt_list, pred_list, key_fields, all_fields)` — precision/recall/F1 on entry count + field accuracy on matched pairs
- `count_field_score(gt_counts, pred_counts)` — `1 - normalized_absolute_error` averaged across count fields (for `publication_summary`)

**Input:** GT and prediction dicts/lists from parsed JSON files

**Output:** Float scores (0.0–1.0) and dicts with precision/recall/f1/field_accuracy

**Dependencies:** `rapidfuzz`

---

### File: `evaluation/result_llm/evaluate_json.py`

**Purpose:** Runs the LLM accuracy benchmark: compares all three model outputs against ground-truth JSON.

**Flow:**
1. Iterates models: `["llama3.1_8b", "mistral_7b", "qwen2.5_7b"]`
2. For each model, iterates ground-truth JSON files in `evaluation/result_llm/data/ground_truth/`
3. Loads prediction JSON from model's subfolder; if missing or invalid, records zero scores
4. Computes: personal info score, education P/R/F1/field accuracy, experience P/R/F1/field accuracy, publication summary score
5. Exports `results/per_resume_metrics.csv` and `results/summary_metrics.csv`

**Input:** `evaluation/result_llm/data/ground_truth/*.json`, `evaluation/result_llm/data/<model>/*.json`

**Output:** `evaluation/result_llm/results/per_resume_metrics.csv`, `summary_metrics.csv`

**Dependencies:** `json`, `pathlib`, `pandas`, `metrics_json`

---

### File: `evaluation/result_text_extraction/extractor.py`

**Purpose:** Benchmark extractor that applies all three PDF tools (PyMuPDF, pdfplumber, pdfminer) to a fixed set of 10 resumes and saves results for evaluation.

**Note:** Uses `Path.cwd()` as `ROOT` — must be run from the project root directory.

**Main Functions:**
- `pymupdf_extract(pdf_path)` — identical logic to production extractor
- `pdfplumber_extract(pdf_path)` — identical logic to production extractor
- `pdfminer_extract(pdf_path)` — uses `pdfminer.high_level.extract_text()`
- `save_text(text, output_file)` — writes UTF-8 text
- `main()` — processes R-001 through R-010 with all three tools

**Input:** `data/raw_resumes/R-001.pdf` through `data/raw_resumes/R-010.pdf`

**Output:** `evaluation/result_text_extraction/data/{pymupdf,pdfplumber,pdfminer}/R-XXX.txt`

---

### File: `evaluation/result_text_extraction/evaluate.py`

**Purpose:** Computes text extraction metrics (F1, CER, BLEU, NED) comparing each tool against ground truth text.

**Flow:** Iterates tools → ground-truth files → paired prediction files → computes 4 metrics per pair → exports CSVs

**Input:** `evaluation/result_text_extraction/data/ground_truth/*.txt`, tool output files

**Output:** `results/per_resume_metrics.csv`, `results/summary_metrics.csv`

---

### File: `evaluation/result_text_extraction/generate_plots.py`

**Purpose:** Reads the summary metrics CSV and generates 5 matplotlib bar charts comparing the three extraction tools.

**Charts Generated:**
- `f1_comparison.png` — Average F1 score per tool
- `cer_comparison.png` — Average Character Error Rate per tool
- `bleu_comparison.png` — Average BLEU-4 score per tool
- `ned_comparison.png` — Average Normalized Edit Distance per tool
- `overall_ranking.png` — Tool ranking by combined F1+BLEU

**Output:** `evaluation/result_text_extraction/plots/*.png` (300 DPI)

---

## 9. Resume Text Extraction

### Libraries Used

| Library | Role | Priority |
|---------|------|----------|
| PyMuPDF (`fitz`) | Primary extraction engine | 1st |
| pdfplumber | Fallback extraction engine | 2nd |
| pdfminer | Benchmark-only (evaluation) | N/A for production |

### Extraction Strategy

**File:** `backend/extraction/pdf_extractor.py`, class `PDFExtractor`

1. `extract_pymupdf()` calls `fitz.open(pdf_path)`, iterates all pages with `page.get_text()`, joins with `\n`, strips surrounding whitespace
2. If the result's character count is ≥ `MIN_TEXT_LENGTH` (100), it is used
3. Otherwise, `extract_pdfplumber()` opens the file with `pdfplumber.open()`, calls `page.extract_text()` per page, filters `None` results, joins with `\n`
4. If pdfplumber also produces < 100 characters, the file is marked as `"failed"`

### Handling Empty / Scanned PDFs

No OCR is implemented. If a PDF is image-based (scanned), both PyMuPDF and pdfplumber will return empty or near-empty text. The file will be marked as `"failed"` and skipped. **There is no OCR fallback.**

### Text Quality Checks

Only a minimum character length check (`MIN_TEXT_LENGTH = 100`) is performed. No structure, language, or content-quality validation exists.

### Output Format

Plain UTF-8 `.txt` files written to `data/extracted_text/`. One file per resume, same stem name as the PDF.

---

## 10. Text Cleaning

**File:** `backend/text_cleaning/cleaner.py`, class `TextCleaner`

The cleaning pipeline applies 9 deterministic stages in this fixed order:

| Stage | Method | What It Does | Configurable |
|-------|--------|-------------|--------------|
| 1 | `normalize_unicode` | NFKC normalization + 17-entry char replacement map (ligatures→ASCII, smart quotes, dashes, bullets, BOM, ZWSP) | Yes |
| 2 | `remove_control_characters` | Strips non-printable control chars: `\x00–\x08`, `\x0B`, `\x0C`, `\x0E–\x1F` | Yes |
| 3 | `normalize_line_endings` | `\r\n` and `\r` → `\n` | Yes |
| 4 | `fix_hyphenated_words` | Joins `word-\nword` patterns (PDF line-break artifacts) | Yes |
| 5 | `normalize_tabs` | `\t` → single space | Yes |
| 6 | `normalize_spaces` | Collapses `2+` spaces to one | Yes |
| 7 | `normalize_bullets` | Replaces bullet chars with `-` (⚠️ already done in stage 1) | Yes |
| 8 | `trim_trailing_spaces` | `rstrip()` per line | Yes |
| 9 | `collapse_blank_lines` | Reduces 3+ consecutive blank lines to 2 (`\n\n`) | Yes |

### What Is Preserved

- All resume content including names, dates, institutions, publication counts
- Line structure (single blank lines, meaningful indentation after tab normalization)
- Non-ASCII characters in non-bullet, non-special-char categories (e.g., accented names)

### What May Be Removed

- Zero-width spaces (`\u200B`) — stripped in unicode normalization
- BOM characters (`\ufeff`) — stripped
- Non-breaking spaces (`\u00A0`) — replaced with regular space
- Control characters (rare in well-formed PDFs)
- Extra whitespace

### Configuration

Each stage can be disabled independently via `CleanerConfig` boolean fields. Default: all stages enabled.

---

## 11. LLM Extraction System

### LLM Provider

**Ollama** — locally hosted LLM inference server. Must be running at `localhost:11434` (Ollama default) before executing `extractor.py`.

### Active Model

`llama3.1:8b` — configured as `MODEL_NAME` constant in `extractor.py` line 80. Two alternatives are commented out in the same file:
- `# MODEL_NAME = "qwen2.5:7b"` 
- `# MODEL_NAME = "mistral:7b"`

Pre-run results for all three models are present in `evaluation/result_llm/data/`.

### Prompt Construction

**System Prompt** (`prompt.py`, `system_prompt()`):
```
You are an expert faculty resume parser.
Extract information accurately from faculty resumes.
Return ONLY valid JSON matching the provided schema.
Do not return markdown.
Do not explain anything.
Do not hallucinate missing information.
```

**User Prompt** (`prompt.py`, `build_messages()`):
Combines three sections in one string:
1. 21 numbered extraction rules (JSON format enforcement, no hallucination, missing-value defaults, publication counting rules)
2. The JSON schema serialized as `json.dumps(self.schema, indent=4)`
3. The full cleaned resume text

### Inference Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| `temperature` | `0.0` | Fully deterministic — maximizes consistency |
| `top_p` | `0.8` | Nucleus sampling threshold |
| `num_predict` | `8192` | Maximum output tokens |
| `format` | `"json"` | Ollama JSON mode — constrains output grammar |
| `REQUEST_TIMEOUT` | `180` | Defined but not passed to `ollama.chat()` |

### Retry Logic

Two nested retry loops:

1. **LLM call retry** (`call_llm()`): up to `MAX_RETRIES = 3` attempts; `RETRY_DELAY = 3` seconds between attempts; triggered on any exception from `ollama.chat()`
2. **Extraction retry** (`extract_resume()`): up to `MAX_RETRIES = 3` attempts; `RETRY_DELAY = 3` seconds between attempts; triggered when `call_llm()` returns `None` OR when `validator.validate()` raises `ValueError`

Maximum attempts per resume: `3 × 3 = 9` LLM calls in the absolute worst case.

### Model Response Parsing

`JSONValidator.clean_response()` handles common LLM output variations:
- Strips ` ```json ` / ` ``` ` markdown fences
- Removes prefix phrases like "Here is the JSON:" or "Output:"
- Extracts the outermost `{...}` object from the response string
- Falls back on `json.loads()` — no custom JSON repair library

### Failure Handling

- LLM call failure (timeout, connection refused, empty response): retry up to 3 times; after all retries, `call_llm()` returns `None`
- JSON parse failure or validation exception: raw response saved to `data/invalid_json/`; `ValueError` raised; outer extraction loop retries up to 3 more times
- Complete failure after all retries: `extract_resume()` returns `False`; pipeline logs error and continues to next resume

---

## 12. Extraction Schema

Defined in `backend/llm/prompt.py`, `PromptBuilder.__init__()`, `self.schema`.

### `personal_information` (object)

| Field | Type | Required | Example | Notes |
|-------|------|----------|---------|-------|
| `full_name` | string | Yes (default: `""`) | `"Dr. Jane Doe"` | Full name as in resume |
| `current_designation` | string | Yes (default: `""`) | `"Associate Professor"` | Current job title |
| `total_experience` | string | Yes (default: `""`) | `"12 Years"` | As stated in resume; not computed |
| `email` | string | Yes (default: `""`) | `"jane@univ.edu"` | |
| `phone` | string | Yes (default: `""`) | `"+91 9876543210"` | |
| `date_of_birth` | string | Yes (default: `""`) | `"1982-05-14"` | Format varies by resume |
| `gender` | string | Yes (default: `""`) | `"Female"` | |
| `address` | string | Yes (default: `""`) | `"Dept of CS, State University"` | |
| `linkedin` | string | Yes (default: `""`) | `"https://linkedin.com/in/janedoe"` | |
| `google_scholar` | string | Yes (default: `""`) | `"https://scholar.google.com/..."` | |
| `researchgate` | string | Yes (default: `""`) | `"https://researchgate.net/..."` | |

### `education` (array of objects)

| Field | Type | Required | Example | Notes |
|-------|------|----------|---------|-------|
| `degree` | string | Yes (default: `""`) | `"Ph.D."` | Degree title |
| `specialization` | string | Yes (default: `""`) | `"Computer Science"` | Subject/branch |
| `institution` | string | Yes (default: `""`) | `"IIT Delhi"` | College/university name |
| `board_university` | string | Yes (default: `""`) | `"IIT"` | Affiliating body |
| `year` | string | Yes (default: `""`) | `"2012"` | Year of completion |
| `cgpa_percentage` | string | Yes (default: `""`) | `"9.5/10"` | Grade as stated |

Rule: All education entries are to be extracted; order must be preserved as-is from the resume.

### `experience` (array of objects)

| Field | Type | Required | Example | Notes |
|-------|------|----------|---------|-------|
| `designation` | string | Yes (default: `""`) | `"Associate Professor"` | Job title |
| `organization` | string | Yes (default: `""`) | `"State University"` | Employer name |
| `start_date` | string | Yes (default: `""`) | `"2018"` | As stated |
| `end_date` | string | Yes (default: `""`) | `"Present"` | `"Present"` for current roles |
| `duration` | string | Yes (default: `""`) | `"6 Years"` | As stated |
| `description` | string | Yes (default: `""`) | `"Led AI research..."` | Max 1-2 sentences per rules |

### `publication_summary` (object)

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `journal_publications` | integer | Yes | `0` | Count only; no titles |
| `conference_publications` | integer | Yes | `0` | Count only |
| `book_publications` | integer | Yes | `0` | Full books authored/edited |
| `book_chapters` | integer | Yes | `0` | Chapters in edited books |
| `patents` | integer | Yes | `0` | Granted or filed patents |

Rule: Individual publication details (title, authors, DOI, ISBN, journal name) are explicitly excluded by prompt rules.

### Default Values (when field is missing)

| Schema Type | Default |
|-------------|---------|
| string | `""` |
| list | `[]` |
| integer | `0` |

---

## 13. Validation System

**File:** `backend/llm/validator.py`, class `JSONValidator`

### Structural Validation

`clean_response()` + `parse_json()` ensure a valid JSON object can be extracted from the LLM response. Uses `json.loads()` — no lenient parsing library.

### Schema Validation

`_validate_value()` recursively walks the response dict against the schema dict:
- Missing keys → filled with schema default (deep copy)
- Wrong type for string → coerced via `str(value).strip()`; `None` → `""`
- Wrong type for int → coerced via `int(value)`; failure → schema default
- Wrong type for float → coerced via `float(value)`; failure → schema default
- Wrong type for dict → replaced with `{}`
- Non-list where list expected → replaced with `[]`

### Key Stripping

`remove_unknown_keys()` is called before schema validation. Any key in the LLM response not present in the schema is silently removed. This handles models that add extra fields like `"skills"`, `"publications_list"`, etc.

### Data Validation

No field-level data validation beyond type coercion. Email format, phone format, URL format, and date ranges are **not validated**.

### Business-Rule Validation

No business-rule validation (e.g., "end date must be after start date", "experience years must be positive"). All field content is taken as-is from the LLM.

### Error Handling

- `json.JSONDecodeError` → caught in `validate()`; raw response saved; `ValueError` re-raised
- Any other exception → caught in `validate()`; raw response saved; `ValueError` re-raised
- Caller (`extract_resume()`) catches `ValueError` and retries

---

## 14. Deduplication

**File:** `backend/deduplication/hash_checker.py`

### Algorithm

SHA-256 hash of the entire file contents, read in 8192-byte chunks using `hashlib.sha256()`.

### Comparison

Hash is compared against all values in the `file_hash` column of a CSV file at a configurable path.

### State Storage

A CSV file with columns `filename` and `file_hash`. Default path in `__main__` block: `"data/file_hashes.csv"` (relative). Correct path per `utils.py`: `data/metadata/file_hashes.csv`.

### What Happens on Duplicate

`is_duplicate_file()` returns `(True, hash_hex)`. The **caller** is responsible for deciding what to do (skip processing). The deduplication module itself takes no action beyond returning the boolean.

### What Happens on New File

`is_duplicate_file()` returns `(False, hash_hex)`. `save_file_hash()` must then be called manually to register the new hash.

### Integration Status

**Not integrated** into the main extraction pipeline. `pdf_extractor.py`, `cleaner.py`, and `extractor.py` do not call any deduplication functions. Must be added manually before processing begins.

---

## 15. State Management

**There is no persistent state management system in this project.**

Each script operates independently:

- `pdf_extractor.py` — reads from `data/raw_resumes/`, writes to `data/extracted_text/`. If output already exists for a file, it is overwritten silently.
- `cleaner.py` — reads from `data/extracted_text/`, writes to `data/cleaned_text/`. Same overwrite behavior.
- `extractor.py` — reads from `data/cleaned_text/`, writes to `data/extracted_json/`. Same overwrite behavior.

There is no concept of `PENDING → PROCESSING → COMPLETED` status tracking. The presence or absence of output files is the only implicit state indicator.

If a pipeline run is interrupted mid-batch, completed files will exist and incomplete files will be absent. Re-running the script will re-process all files (including already-completed ones).

---

## 16. Error Handling & Retry Strategy

### What Can Fail

| Point of Failure | Caught? | Logged? | Retried? |
|-----------------|---------|---------|---------|
| Ollama server not running | Yes | Yes (exception) | Yes (up to 3) |
| Model not found in Ollama | Yes | Yes (error) | No (early exit) |
| PDF cannot be opened | Yes | Console print | No |
| PDF extraction returns empty | No | Console print | No — skipped |
| Resume text file empty | Yes | Warning | No |
| LLM returns empty response | Yes (ValueError) | Warning | Yes (up to 3) |
| LLM response not valid JSON | Yes (ValueError) | Exception | Yes (up to 3) |
| JSON fails schema validation | Yes (ValueError) | Exception | Yes (up to 3) |
| File write error | Yes | Exception | No |
| Ollama timeout | Partial (exception) | Exception | Yes (up to 3) |

### Retry Count and Delay

- `MAX_RETRIES = 3` (both LLM call and extraction loop)
- `RETRY_DELAY = 3` seconds between retries

### Batch Behavior

One resume failure does **not** stop the batch. `process_directory()` loops over all resumes and continues regardless of individual failures. Failed resumes are only logged — no resume-level failure report file is generated.

### Failed Response Storage

When JSON parsing fails, the raw LLM response string is written to `data/invalid_json/<stem>_raw.txt` for manual inspection.

---

## 17. Logging & Monitoring

### LLM Extractor Logging

**File:** `backend/llm/extractor.py` (line 99), shared by `validator.py`

**Configuration:** `logging.basicConfig()` with:
- Level: `INFO`
- Format: `"%(asctime)s | %(levelname)s | %(message)s"`
- Handlers:
  - `FileHandler` → `logs/llm_extraction.log` (UTF-8)
  - `StreamHandler` → console

**Logger name:** `"LLMExtractor"` — shared by `extractor.py` and `validator.py`

**What is logged:**
- Extractor initialization (model name)
- Per-resume processing start/finish
- Each LLM request attempt number
- **Full Ollama response object at INFO level** (⚠️ includes extracted content / PII)
- Retry events (warning)
- Validation success (info)
- Validation failure with full exception traceback
- Save confirmation (file name)
- Batch statistics (start/finish markers)
- Model availability check result

### Text Cleaner Logging

**File:** `backend/text_cleaning/cleaner.py` (line 32)

**Configuration:** `logging.basicConfig()` with:
- Level: `INFO`
- Format: `"%(asctime)s | %(levelname)s | %(message)s"`
- Handlers: `StreamHandler` only (no log file for cleaner)

**Logger name:** `"ResumeCleaner"`

**What is logged:** Per-file cleaning start and save messages; exception tracebacks

### Diagnosing Errors

- LLM extraction failures: inspect `logs/llm_extraction.log`
- Raw LLM responses that failed parsing: inspect `data/invalid_json/`
- Cleaning failures: console output only (no log file)
- PDF extraction failures: console output only (no log file)

---

## 18. Configuration Management

### Hardcoded Configuration (Source Code Constants)

| Constant | File | Value | Purpose |
|----------|------|-------|---------|
| `MODEL_NAME` | `extractor.py:80` | `"llama3.1:8b"` | Active Ollama model |
| `REQUEST_TIMEOUT` | `extractor.py:83` | `180` | Defined but unused |
| `MAX_RETRIES` | `extractor.py:85` | `3` | Max attempts per resume/LLM call |
| `RETRY_DELAY` | `extractor.py:87` | `3` | Seconds between retries |
| `NUM_PREDICT` | `extractor.py:89` | `8192` | Max LLM output tokens |
| `TOP_P` | `extractor.py:91` | `0.8` | Sampling top-p |
| `TEMPERATURE` | `extractor.py:93` | `0.0` | LLM temperature |
| `MIN_TEXT_LENGTH` | `pdf_extractor.py:8` | `100` | Minimum characters for extraction success |
| File count range | `loader.js:52` | `1–40` | Number of resumes the frontend loads |
| JSON folder path | `loader.js:42` | `"../evaluation/result_llm/data/qwen2.5_7b/"` | Frontend data source path |
| JSON folder path | `faculty.js:12-13` | Same as above | Faculty page data source path |

### Environment-Based Configuration

**None implemented.** `python-dotenv` is listed in `requirements.txt` but no `.env` file exists and `load_dotenv()` is never called in any script.

### Runtime Configuration

The only runtime configurability is passing a `model` parameter to `LLMExtractor(model=...)`. When called via `main()`, the default constant `MODEL_NAME` is used.

### Switching Models

To change the active LLM model, edit line 80 in `backend/llm/extractor.py`:
```python
MODEL_NAME = "qwen2.5:7b"  # or "mistral:7b"
```
Then ensure that model is pulled in Ollama: `ollama pull qwen2.5:7b`.

---

## 19. Input and Output Structure

### Input Structure

```
data/
└── raw_resumes/
    ├── R-001.pdf
    ├── R-002.pdf
    ├── ...
    └── R-040.pdf
```

Files can have any name accepted by `glob("*.pdf")`. The evaluation framework and frontend assume the `R-NNN` naming pattern.

### Intermediate Artifacts (generated by pipeline)

```
data/
├── extracted_text/           # Stage 2 output
│   ├── R-001.txt             # Raw text from PDF
│   └── ...
├── cleaned_text/             # Stage 3 output
│   ├── R-001.txt             # Cleaned text
│   └── ...
├── extracted_json/           # Stage 4 output (main pipeline)
│   ├── R-001.json
│   └── ...
└── invalid_json/             # Failed LLM responses
    └── R-XXX_raw.txt
```

### Evaluation Data Structure

```
evaluation/result_llm/data/
├── ground_truth/             # Human-annotated reference JSONs (10 files)
│   ├── R-001.json
│   └── ...R-010.json
├── llama3.1_8b/              # LLaMA output JSONs (40 files)
│   └── R-001.json ... R-040.json
├── mistral_7b/               # Mistral output JSONs (40 files)
│   └── R-001.json ... R-040.json
└── qwen2.5_7b/               # Qwen output JSONs (39 files; R-019 missing)
    └── R-001.json ... R-040.json

evaluation/result_text_extraction/data/
├── ground_truth/             # Reference text files (10 files)
├── pymupdf/                  # PyMuPDF extracted text (10 files)
├── pdfplumber/               # pdfplumber extracted text (10 files)
└── pdfminer/                 # pdfminer extracted text (10 files)
```

### Final Output JSON Structure (sample: `R-001.json`)

```json
{
    "personal_information": {
        "full_name": "Dr. AFZAL BEG",
        "current_designation": "",
        "total_experience": "11 years",
        "email": "afzalbeg09@gmail.com",
        "phone": "+91 9098248646, 7415952569",
        "date_of_birth": "29thSeptember 1988",
        "gender": "Male",
        "address": "",
        "linkedin": "",
        "google_scholar": "",
        "researchgate": ""
    },
    "education": [
        {
            "degree": "PH.D.",
            "specialization": "Computer Science",
            "institution": "Sarveapalli RadhaKrishnan University Bhopal",
            "board_university": "",
            "year": "2024",
            "cgpa_percentage": ""
        }
        // ... more entries
    ],
    "experience": [
        {
            "designation": "Assistant Professor",
            "organization": "Rai University, Ahmadabad Gujarat",
            "start_date": "July 2024",
            "end_date": "",
            "duration": "",
            "description": ""
        }
        // ... more entries
    ],
    "publication_summary": {
        "journal_publications": 4,
        "conference_publications": 2,
        "book_publications": 0,
        "book_chapters": 0,
        "patents": 0
    }
}
```

---

## 20. Frontend / UI

### Pages

#### `frontend/index.html` — Dashboard Overview

**Purpose:** Main entry page showing aggregated faculty statistics and a browsable faculty card grid.

**Layout sections:**
- **Topbar/Header:** Title, search box, theme toggle button, refresh button (no-op), settings button (no-op)
- **Filter Panel (left sidebar):** Dropdowns for degree, institute, designation, experience range; checkboxes for journal/conference/patent presence; Apply + Clear buttons
- **Stats Panel (right):** 10 metric cards (Total Faculty, PhD count, Assistant/Associate/Full Professor counts, Average Experience, Journal/Conference Publications, Patents, Universities)
- **Faculty Directory:** Responsive grid of faculty cards; results count badge

**CSS files:** `style.css`, `dashboard.css`, `cards.css`, `responsive.css`

**Script files loaded:** `loader.js`, `app.js`, `filters.js`, `search.js`, `dashboard.js` (⚠️ broken), `utils.js` (⚠️ file does not exist → 404)

---

#### `frontend/faculty.html` — Faculty Profile Detail

**Purpose:** Full faculty profile view with tabbed sections.

**Layout sections:**
- **Profile Header:** Back button, page title, Resume PDF button, JSON viewer button, Download JSON button
- **Hero Card:** Avatar initials, name, Ph.D. badge, designation, university, contact info (email, phone, location)
- **Stats Strip:** Experience years, Journal Papers, Conference Papers, Patents
- **Tab Navigation:** Overview, Education, Experience, Research, Skills
- **Tab Panels:**
  - `overview`: AI summary paragraph + Quick Information grid (degree, position, institute, experience)
  - `education`: Timeline of degree entries
  - `experience`: Timeline of job entries
  - `research`: Publication count cards + `researchSummary` div (⚠️ never populated)
  - `skills`: Skill chip badges (from `skills`, `technical_skills`, `key_skills`, `core_skills` — none of which are in the LLM schema, so this tab always shows "No skills extracted")
- **JSON Modal:** Full raw JSON viewer overlay
- **Loading Screen:** Spinner shown during `init()`
- **Toast:** Transient success notifications (declared but never triggered in current code)
- **Profile Status Card:** Always shows "100%" and all-green checkmarks (⚠️ hardcoded, not computed)

**CSS files:** `style.css`, `dashboard.css`, `faculty.css`

**Script files loaded:** `faculty.js` only

---

### JavaScript Modules

#### `frontend/js/loader.js`

**Role:** Data loading, global state management, candidate normalization, stats computation

**Global state object (`loader.state`):**
```javascript
{
  candidates: [],      // All normalized candidate objects
  stats: {},           // Computed aggregate stats
  filters: {           // Current filter state
    degree, institute, designation, experience,
    journal, conference, patent
  },
  search: "",          // Current search string
  theme: "dark",       // Current theme
  applied: false       // Whether any filter is active
}
```

**Key methods:**
- `loadCandidates()` — fetches R-001 through R-040 sequentially (hardcoded 40 file limit); normalizes each; fires `candidates:loaded` custom event
- `normalizeCandidate(data, fileName)` — maps raw JSON fields to a flat `candidate` object with standardized keys
- `getJsonBaseUrl()` — returns URL pointing to `evaluation/result_llm/data/qwen2.5_7b/`
- `computeStats(candidates)` — computes 10 aggregate stats (total, phd, assistant, associate, professor, average, journal, conference, patents, universities)
- `parseExperience(value)` — extracts first number from experience string
- `applyTheme(theme)` — updates `data-theme` attribute and `localStorage`

**Exposes:** `window.loader`

---

#### `frontend/js/app.js`

**Role:** Renders stats cards and faculty card grid; populates filter dropdowns; handles theme toggle

**Key methods:**
- `renderStats(stats)` — creates 10 metric cards via `innerHTML` from stats object
- `renderFacultyCards(candidates)` — renders faculty card grid; attaches click handlers to View buttons
- `buildCard(candidate)` — generates individual faculty card HTML with avatar, name, degree badge, university, mini-stats, view button
- `getInitials(fullName)` — first two words' first characters, uppercased
- `normalizeDegree(degree)` — maps common degree strings to standard labels (Ph.D., M.Tech, B.Tech, etc.)
- `getDegreeBadge(degree)` — returns Ph.D. badge HTML or empty string
- `populateFilters(candidates)` — fills the four filter dropdowns with unique values from loaded candidates

**Exposes:** `window.app`

---

#### `frontend/js/filters.js`

**Role:** Reads filter panel state; applies combined filtering; re-renders filtered grid

**Key methods:**
- `applyFilters()` — reads all filter inputs, updates `loader.state.filters`, calls `renderFiltered()`
- `clearFilters()` — resets filter state, calls `renderFiltered()`
- `renderFiltered()` — filters `loader.state.candidates` against all active criteria; calls `window.app.renderFacultyCards(filtered)`
- `matchesExperience(years, range)` — switch-case for 0-2, 2-5, 5-10, 10+ ranges

**Combined filter criteria (all must match):**
- Text search across name, designation, university, degree
- Degree filter (partial string match)
- Institute filter (partial string match)
- Designation filter (partial string match)
- Experience range filter
- Journal publications checkbox (must have > 0)
- Conference publications checkbox (must have > 0)
- Patents checkbox (must have > 0)

**Exposes:** `window.filters`

---

#### `frontend/js/search.js`

**Role:** Real-time search — listens to `search-input` events and triggers re-filter

Updates `loader.state.search` on every `input` event and calls `window.filters.renderFiltered()`.

---

#### `frontend/js/faculty.js`

**Role:** Loads and renders the faculty profile detail page

**Key functions:**
- `init()` — async initialization: extracts `id` from URL params, fetches JSON, populates page, initializes components
- `getFacultyId()` — reads `?id=` from `URLSearchParams`
- `loadFacultyJSON(id)` — `fetch(JSON_FOLDER + id + ".json")`
- `populatePage()` — calls all render functions
- `renderHero()` — fills name, designation, university, email, phone, address, avatar, degree badge via `textContent` and `innerHTML`
- `renderStatistics()` — fills 4 stat numbers
- `renderOverview()` — fills Quick Info grid and AI summary paragraph
- `createSummary()` — generates 3-paragraph AI summary from extracted data
- `renderEducation()` — generates timeline items in `educationTimeline` div
- `renderExperience()` — generates timeline items in `experienceTimeline` div
- `renderResearch()` — fills 3 publication count numbers (does NOT fill `researchSummary`)
- `renderSkills()` — reads `skills`, `technical_skills`, `key_skills`, `core_skills` fields from JSON (none present in schema — always shows empty)
- `initializeTabs()` — attaches click handlers to `.tab-btn` elements
- `initializeJsonModal()` — opens/closes JSON viewer modal
- `initializeResumeButton()` — opens `RESUME_FOLDER + facultyId + ".pdf"` in new tab (always .pdf; fallback loop `break`s immediately)
- `initializeDownloadButton()` — creates `Blob` and triggers download of `facultyId.json`

**Known Bugs:**
- Lines 76–90: orphan code referencing undefined `button`, `buttons`, `panels` outside any function — causes `ReferenceError` on page load, crashing the entire page
- `RESUME_FOLDER` and `JSON_FOLDER` are hardcoded string paths (not using `new URL()` like `loader.js`)

---

#### `frontend/js/dashboard.js` ⚠️ BROKEN

**Status:** This file contains a floating `buildCard(candidate) { ... }` function fragment that is syntactically invalid JavaScript. It is not part of any object, class, or callable function. It duplicates (with slight differences) the `buildCard()` method already in `app.js`. This file appears to be an abandoned refactor artifact and should not be loaded or used.

---

### Data Communication (Frontend ↔ Backend)

There is **no backend API**. The frontend communicates with data by fetching pre-generated JSON files from the filesystem/server directly:

```
loader.js fetch() → ../evaluation/result_llm/data/qwen2.5_7b/R-NNN.json
faculty.js fetch() → ../evaluation/result_llm/data/qwen2.5_7b/R-NNN.json
```

These paths are relative to the location of `index.html`/`faculty.html`. The frontend assumes the entire project directory is served from a web server with `frontend/` as the document root.

### Current Limitations

- Hardcoded 40-file limit (R-001 to R-040)
- Hardcoded model directory (`qwen2.5_7b`)
- No loading skeleton — faculty grid is blank during sequential fetches
- Faculty page broken due to JavaScript syntax error (lines 76–90 of `faculty.js`)
- `dashboard.js` is syntactically invalid
- `utils.js` referenced in `index.html` does not exist
- Dark/light theme not applied on `faculty.html`
- Chart.js loaded but no charts rendered
- Skills tab always empty (schema has no skills field)
- Research summary div never populated

---

## 21. Database / Persistence

**Currently no production database is implemented.**

All data is stored as flat files:

| Data | Storage | Format |
|------|---------|--------|
| Raw resumes | `data/raw_resumes/` | PDF |
| Extracted text | `data/extracted_text/` | UTF-8 `.txt` |
| Cleaned text | `data/cleaned_text/` | UTF-8 `.txt` |
| Extracted profiles | `data/extracted_json/` | JSON |
| Failed LLM responses | `data/invalid_json/` | Plain text |
| File hash registry | `data/file_hashes.csv` (per `__main__`) | CSV |
| Cleaning statistics | `backend/text_cleaning/report/` | JSON |
| Pipeline logs | `logs/llm_extraction.log` | Plain text (log format) |
| Evaluation results | `evaluation/*/results/*.csv` | CSV |

---

## 22. Dependencies

### `requirements.txt` (current file contents)

```
PyMuPDF
python-docx
pandas
tqdm
python-dotenv
```

### Complete Required Dependencies (including missing ones)

| Package | Listed in requirements.txt | Purpose |
|---------|---------------------------|---------|
| `PyMuPDF` | ✅ Yes | Primary PDF text extraction (`fitz`) |
| `pdfplumber` | ❌ **Missing** | Fallback PDF text extraction |
| `ollama` | ❌ **Missing** | Python client for Ollama server API |
| `pandas` | ✅ Yes | CSV output and reporting |
| `python-docx` | ✅ Yes (unused) | Word document support — not used in any active module |
| `tqdm` | ✅ Yes (unused) | Progress bars — not used in any active module |
| `python-dotenv` | ✅ Yes (unused) | `.env` file loading — no `.env` file exists |
| `rapidfuzz` | ❌ Not listed | Fuzzy string matching in evaluation |
| `jiwer` | ❌ Not listed | Character Error Rate metric |
| `nltk` | ❌ Not listed | BLEU score computation |
| `matplotlib` | ❌ Not listed | Bar chart generation |
| `pdfminer.six` | ❌ Not listed | Third PDF extractor (evaluation only) |

### Python Version

Python 3.9+ required (walrus operator `:=` used in `hash_checker.py` line 10).

### External Services

| Service | Version | Purpose | Installation |
|---------|---------|---------|-------------|
| Ollama | Latest | Local LLM inference server | `https://ollama.ai` — separate installer |
| LLaMA 3.1 8B | — | Active extraction model | `ollama pull llama3.1:8b` |
| Qwen 2.5 7B | — | Alternative model (pre-run data available) | `ollama pull qwen2.5:7b` |
| Mistral 7B | — | Alternative model (pre-run data available) | `ollama pull mistral:7b` |

---

## 23. Runtime Requirements

| Requirement | Specification | Notes |
|-------------|---------------|-------|
| Operating System | Windows / Linux / macOS | Tested on Windows (CRLF in source) |
| Python | 3.9+ | Walrus operator required |
| RAM (backend) | 8 GB minimum | For local LLM inference via Ollama |
| RAM (LLM) | 8–16 GB recommended | LLaMA 3.1 8B requires ~5–8 GB VRAM or RAM |
| GPU | Optional but strongly recommended | CPU inference is very slow (minutes per resume) |
| Ollama | Installed and running | Must be at `localhost:11434` |
| LLM model pulled | `ollama pull llama3.1:8b` | Required before running `extractor.py` |
| Python packages | See Section 22 | `pip install -r requirements.txt` (incomplete) |
| `data/raw_resumes/` | Must exist and contain PDFs | Manual setup |
| `data/extracted_text/` | Auto-created by `pdf_extractor.py` | — |
| `data/cleaned_text/` | Auto-created by `cleaner.py` | — |
| `data/extracted_json/` | Auto-created by `extractor.py` | — |
| `data/invalid_json/` | Auto-created by `validator.py` | — |
| `logs/` | Auto-created by `extractor.py` | — |
| Frontend web server | `python -m http.server` or any static server | `fetch()` fails on `file://` directly |
| Browser | Modern browser with ES6+ support | Chrome, Firefox, Edge |
| Environment variables | None required | `.env` not used despite `python-dotenv` listing |

---

## 24. How to Run the Current Project

### 1. Prerequisites

```bash
# Install Python 3.9+
# Install Ollama from https://ollama.ai

# Start Ollama server (if not already running as a system service)
ollama serve
```

### 2. Install Python Dependencies

```bash
cd e:/LLM_Based_Extraction
pip install -r requirements.txt

# Install missing packages not in requirements.txt:
pip install pdfplumber ollama rapidfuzz jiwer nltk matplotlib pdfminer.six
```

### 3. Pull LLM Model

```bash
ollama pull llama3.1:8b
```

### 4. Place Resumes

Copy PDF files named `R-001.pdf` through `R-040.pdf` into `data/raw_resumes/`.

### 5. Run PDF Extraction

Must be run from the project root (relative paths in this script):

```bash
python backend/extraction/pdf_extractor.py
```

Output: `data/extracted_text/*.txt`

### 6. Run Text Cleaning

```bash
python backend/text_cleaning/cleaner.py
```

Output: `data/cleaned_text/*.txt`, `backend/text_cleaning/report/cleaning_statistics.json`

### 7. Run LLM Extraction

Must be run from within the `backend/llm/` directory (bare imports):

```bash
cd backend/llm
python extractor.py
```

Output: `../../data/extracted_json/*.json`, `../../logs/llm_extraction.log`

```bash
# Return to project root
cd ../..
```

### 8. Launch the Frontend

```bash
python -m http.server 8000 --directory frontend
```

Open `http://localhost:8000` in a browser.

> **Note:** The frontend reads JSON from `../evaluation/result_llm/data/qwen2.5_7b/`. The current pipeline writes to `data/extracted_json/`. You must manually copy or symlink the JSON files to the evaluation data directory for the frontend to display them.

### 9. Inspect Outputs

```bash
# LLM extraction log
cat logs/llm_extraction.log

# Failed LLM responses
ls data/invalid_json/

# Extracted JSON for a specific resume
cat data/extracted_json/R-001.json
```

### 10. Run Benchmarks (Optional)

```bash
# Text extraction benchmark (must run from project root)
python evaluation/result_text_extraction/extractor.py
python evaluation/result_text_extraction/evaluate.py
python evaluation/result_text_extraction/generate_plots.py

# LLM accuracy benchmark
cd evaluation/result_llm
python evaluate_json.py
```

---

## 25. Current Automation

### Fully Automated

- Text cleaning of a directory of `.txt` files (once `cleaner.py` is started)
- LLM extraction of a directory of cleaned `.txt` files with retry (once `extractor.py` is started)
- JSON schema validation and repair during extraction
- Invalid response logging
- Log file creation
- Output directory creation (auto-`mkdir`)

### Partially Automated

- PDF extraction: processes all files in `data/raw_resumes/` automatically, but errors are reported to console only and failed files are not retried
- Evaluation: scripts run the benchmark automatically but require correct file placement first

### Manual Steps Still Required

- Installing Ollama and pulling models
- Placing PDF resumes in `data/raw_resumes/`
- Running pipeline stages in the correct order (no orchestration)
- Changing active model (edit source constant)
- Copying extracted JSONs from `data/extracted_json/` to `evaluation/result_llm/data/<model>/` for the frontend and benchmarks to use
- Running deduplication checks before processing (module exists but is not wired in)
- Running `cd backend/llm` before `extractor.py` (bare import workaround)

---

## 26. Production Readiness Assessment

| Area | Current Status | Production Ready? | Notes |
|------|---------------|-------------------|-------|
| Input validation | Minimal | ❌ No | Only checks text length ≥ 100 chars; no file type, size, or password check |
| PDF extraction | Functional | ⚠️ Partial | No OCR; relative paths; errors printed not logged; no retry |
| Text cleaning | Good | ⚠️ Partial | Bullet stage is no-op (double-processed); no log file |
| LLM extraction | Functional | ⚠️ Partial | Retry implemented; validator has indentation bug; bare imports; PII in logs |
| JSON Validation | Broken | ❌ No | `_validate_value` is unreachable due to indentation error |
| Deduplication | Utility only | ❌ No | Not integrated into pipeline |
| Error handling | Partial | ⚠️ Partial | Batch continues on failure; no structured error report |
| Retry | Implemented | ⚠️ Partial | Retry at LLM + validation level; no retry at PDF extraction level |
| Logging | Partial | ⚠️ Partial | LLM stage has file logger; other stages use console only; PII logged |
| Persistence | File-based | ❌ No | No database; no atomic writes; no state tracking |
| Security | Missing | ❌ No | No auth; XSS in frontend; path traversal risk; PII in logs and git |
| Testing | None | ❌ No | Zero automated tests; no test files in repository |
| Scalability | Poor | ❌ No | Sequential processing; hardcoded 40-file limit; no parallelism |
| Deployment | Local only | ❌ No | No Docker; no Nginx; no HTTPS; no production WSGI |
| Frontend | Broken | ❌ No | Critical JS bugs; broken file references; no loading state |
| Configuration | Hardcoded | ❌ No | All settings are source-code constants |

---

## 27. Known Limitations

### Critical / Functional

1. **`faculty.js` lines 76–90:** Orphan code at module scope references undefined variables — causes `ReferenceError` on page load, the faculty profile page does not render
2. **`validator.py` indentation bug:** `_validate_value()` and `save_invalid_response()` are indented inside other methods — they are unreachable as instance methods; the validator will raise `AttributeError`
3. **`dashboard.js` is syntactically invalid:** Floating method fragment not belonging to any object
4. **`js/utils.js` missing:** `index.html` references a file that does not exist (404 on load)
5. **Bare imports in `extractor.py` and `validator.py`:** `from validator import JSONValidator` — fails unless run from `backend/llm/` directory
6. **`pdf_extractor.py` relative paths:** `Path("data/raw_resumes")` — fails if not run from project root

### Architecture / Design

7. **No backend API:** Frontend reads files directly; cannot upload resumes or trigger extraction from browser
8. **Hardcoded 40-file limit:** `loader.js` loops `for i in range(1, 41)` — adding resume #41 requires source code change
9. **Hardcoded model-specific path in two JS files:** `"../evaluation/result_llm/data/qwen2.5_7b/"` — changing models requires editing both files
10. **Pipeline stages are disconnected scripts:** Must be run in sequence manually; no orchestrator
11. **Deduplication not integrated:** SHA-256 hash checker exists but is never called from the pipeline
12. **No OCR:** Scanned/image PDFs produce empty text and are silently skipped

### Data / Logic

13. **Professor stat double-counts:** `professor` regex matches "Assistant Professor" and "Associate Professor" — all three stats overlap
14. **`highestDegree` from `education[0]`:** Assumes first entry is highest; not enforced
15. **Experience parser extracts first number:** `"Since 2008"` → returns `2008` (a year, not years of experience)
16. **Skills tab always empty:** `renderSkills()` looks for keys not in the extraction schema
17. **Research summary div never populated:** Placeholder text shown permanently
18. **"100% completion" always shown:** Profile status card is hardcoded

### Security

19. **XSS:** LLM-extracted data injected via `innerHTML` unsanitized in `app.js` and `faculty.js`
20. **Path traversal:** `facultyId` URL parameter used directly in `fetch()` without validation
21. **PII in log files:** Full Ollama response (containing extracted personal data) logged at INFO level
22. **`data/` and `logs/` not gitignored:** Faculty PDFs and personal data could be committed

### Deployment

23. **`requirements.txt` incomplete:** Missing `pdfplumber`, `ollama`, `rapidfuzz`, `jiwer`, `nltk`, `matplotlib`, `pdfminer.six`
24. **`venv/` directory not properly gitignored:** May be committed with the repository
25. **No `.env` configuration:** All settings hardcoded in source

---

## 28. Potential Production Improvements

### P0 — Critical (Fix Before Any Demo or Deployment)

1. **Fix `faculty.js` orphan code (lines 76–90):** Move the `button.addEventListener()` block inside `initializeTabs()` where it belongs
2. **Fix `validator.py` indentation:** Un-indent `_validate_value` and `save_invalid_response` to class level (remove erroneous indentation)
3. **Fix bare imports in `extractor.py` / `validator.py`:** Add `sys.path.insert(0, str(Path(__file__).parent))` or restructure as a proper Python package with `__init__.py`
4. **Fix `pdf_extractor.py` relative paths:** Use `ROOT = Path(__file__).resolve().parents[2]` for all paths
5. **Remove or restructure `dashboard.js`:** The file is syntactically invalid and unused
6. **Remove the `js/utils.js` reference from `index.html`:** File does not exist
7. **Add missing dependencies to `requirements.txt`:** `pdfplumber`, `ollama`, `rapidfuzz`, `jiwer`, `nltk`, `matplotlib`, `pdfminer.six`

### P1 — Important (Reliability and Quality)

8. **Create a manifest JSON** listing available resume IDs — eliminate the hardcoded 40-file loop
9. **Centralize data paths in a config file** (or at minimum a shared constants JS file)
10. **Sanitize all `innerHTML` assignments:** Use `textContent` for plain text or a sanitization library for structured HTML
11. **Validate `facultyId` URL parameter:** Reject anything not matching `/^R-\d{3}$/`
12. **Add `.gitignore` entries:** `data/`, `logs/`, `*.pdf`, `evaluation/result_llm/data/*/`, `evaluation/result_text_extraction/data/`
13. **Fix professor stat double-counting:** Use exclusive designation matching
14. **Fix `initializeResumeButton()` break logic:** Test file existence or remove the loop
15. **Remove PII from INFO-level logging:** Log only metadata (file name, response length, processing time), not the full response content
16. **Implement `REQUEST_TIMEOUT`:** Pass timeout to `ollama.chat()` or implement via `threading.Timer`
17. **Add `data-theme="dark"` to `faculty.html`** and include theme initialization
18. **Populate `researchSummary` div** in `renderResearch()`
19. **Integrate deduplication** into the main pipeline before `pdf_extractor.py` runs

### P2 — Nice to Have (Future Enhancements)

20. **Add a thin FastAPI/Flask backend:** Enables dynamic file listing, resume upload, trigger-on-demand extraction
21. **Add SQLite or PostgreSQL database** for resume state tracking and searchable metadata
22. **Implement parallel LLM processing:** Use `concurrent.futures.ThreadPoolExecutor` with bounded concurrency
23. **Replace sequential `fetch()` with `Promise.all()`** for parallel JSON loading on the dashboard
24. **Add OCR support:** Integrate `pytesseract` or `easyocr` as a third fallback for scanned PDFs
25. **Add skeleton loading states** on the dashboard grid
26. **Implement actual Chart.js visualizations** in the dashboard (publications distribution, experience histogram)
27. **Add automated tests:** pytest unit tests for `TextCleaner`, `JSONValidator`, `PDFExtractor`; integration test for the full pipeline
28. **Create Docker Compose configuration:** Package Ollama + Python pipeline + nginx in containers
29. **Add a `.env` configuration file** and wire `python-dotenv` to load model name, paths, retry settings at runtime
30. **Fix `initials()` crash on whitespace-only names**

---

## 29. Security Considerations

### Currently Implemented Protections

- All LLM inference is local (no external API calls with data)
- No user authentication layer to implement wrong (there is no auth at all)
- Ollama runs locally — extracted content never leaves the machine during processing

### Missing Protections

| Risk | Status | Details |
|------|--------|---------|
| XSS (Cross-Site Scripting) | ❌ Unprotected | Extracted fields injected via `innerHTML` in `app.js` and `faculty.js`. A resume with `<script>` in any text field executes in the browser |
| Path Traversal | ❌ Unprotected | `faculty.html?id=../../etc/passwd` — `facultyId` is used directly in `fetch()` URL without validation |
| Inline event XSS | ❌ Unprotected | `dashboard.js` builds `onclick` with `candidate.id` in a template literal |
| PII in log files | ❌ Unprotected | Full LLM response (containing personal data) logged at INFO level to `logs/llm_extraction.log` |
| PII in version control | ❌ Unprotected | `data/` not gitignored — faculty PDFs and personal info could be committed |
| Malicious PDF | ⚠️ Partial | PyMuPDF processes only text layers; embedded JavaScript in PDFs is not executed during extraction |
| No authentication | ❌ Missing | No access control on any data or page |
| No HTTPS | ❌ Missing | `python -m http.server` serves HTTP only |
| No input file validation | ❌ Missing | No MIME type check, file size limit, or password-protection check |
| Environment secrets | ✅ No risk currently | No API keys or secrets — Ollama is local; `python-dotenv` unused |

---

## 30. Scalability

### 10 Resumes
**Current behavior:** Feasible. PDF extraction completes in seconds. Cleaning in seconds. LLM extraction at ~1–3 minutes per resume on CPU, ~20–60 seconds on GPU. Total: 10–30 minutes. Frontend loads 10 files quickly.

### 100 Resumes
**Current behavior:** LLM extraction becomes the bottleneck. At 3 minutes per resume on CPU: ~5 hours sequential processing. Frontend hardcoded to 40 files — cannot display > 40 without code change. Log file grows significantly, containing PII.

### 1,000 Resumes
**Current behavior:** Not viable. Sequential processing: 50+ hours CPU-only. Frontend cannot be patched to handle 1,000 by simply raising the limit (sequential fetch of 1,000 JSON files will block the browser for minutes). No database, so file management becomes complex.

### 10,000 Resumes
**Current behavior:** Completely infeasible without architectural changes. Disk I/O for 10,000 PDF+text+JSON files, sequential LLM processing, and browser-side rendering of thousands of cards are all blocking bottlenecks.

### Identified Bottlenecks

| Bottleneck | Severity | Solution |
|------------|---------|---------|
| Sequential LLM processing | 🔴 Critical | Parallel processing with bounded thread pool |
| Ollama single-model concurrency | 🔴 Critical | Multiple Ollama instances or batching |
| Frontend hardcoded file count | 🟠 High | Manifest API or server-side pagination |
| Sequential `fetch()` for JSON files | 🟡 Medium | `Promise.all()` parallel fetch |
| All cards rendered at once (no virtual scroll) | 🟡 Medium | Pagination or virtual list |
| Flat file storage | 🟡 Medium | Database with indexed queries |
| Log file with PII | 🟡 Medium | Log rotation, PII masking |

---

## 31. Testing

### Existing Tests

**None.** There are no test files, no `tests/` directory, no `pytest.ini`, `setup.cfg`, or `tox.ini`. No unit tests, integration tests, or end-to-end tests exist anywhere in the repository.

### Areas Not Tested

- `TextCleaner` individual stage correctness
- `JSONValidator` parsing edge cases (malformed JSON, nested errors)
- `PDFExtractor` fallback trigger behavior
- `PromptBuilder` message construction
- `LLMExtractor` retry logic
- Frontend JS functions (`normalizeCandidate()`, `parseExperience()`, `matchesExperience()`, etc.)
- End-to-end pipeline integration
- Evaluation metric correctness

### Recommended Test Areas for Future

1. `TextCleaner.clean()` with edge-case inputs (empty string, only whitespace, control chars, all bullet types)
2. `JSONValidator.validate()` with known-good JSON, truncated JSON, markdown-wrapped JSON, empty JSON
3. `PDFExtractor.extract()` with real scanned PDFs and digital PDFs
4. `PromptBuilder.build_messages()` with valid and invalid inputs
5. Frontend `parseExperience()` with varied formats ("12 Years", "Since 2010", "3 to 5 years")

---

## 32. Deployment Architecture

### Current Deployment (Local Development Only)

```
Developer Machine
      │
      ├── python backend/extraction/pdf_extractor.py   (batch, manual)
      ├── python backend/text_cleaning/cleaner.py       (batch, manual)
      ├── cd backend/llm && python extractor.py         (batch, manual)
      │
      └── python -m http.server 8000 --directory frontend
                    │
                    └── Browser → http://localhost:8000
                                   │
                                   └── fetch() → evaluation/result_llm/data/qwen2.5_7b/*.json
```

### PROPOSED FUTURE ARCHITECTURE (Not Currently Implemented)

```
Internet / College LAN
        │
        ▼
   Nginx (HTTPS reverse proxy, static file serving)
        │
        ├──── Static: frontend/index.html, faculty.html, js/, css/
        │
        └──── /api/ ──► FastAPI (Python)
                              │
                              ├── POST /upload → Resume upload endpoint
                              ├── GET  /resumes → List all resume IDs + metadata
                              ├── GET  /resume/{id} → Full profile JSON
                              ├── POST /extract/{id} → Trigger extraction pipeline
                              └── GET  /stats → Aggregate statistics
                              │
                              ├──── PostgreSQL (resume metadata, processing state)
                              │
                              ├──── Celery Worker (async task queue)
                              │         │
                              │         ├── PDF extraction task
                              │         ├── Text cleaning task
                              │         ├── LLM extraction task
                              │         └── Validation task
                              │
                              └──── Ollama (local LLM server)
                                          │
                                          └── LLaMA / Qwen / Mistral
```

> **This architecture does not currently exist. It is a recommended future direction only.**

---

## 33. Developer Guide

| Task | Where to Go |
|------|------------|
| Change the active LLM model | Edit `MODEL_NAME` in `backend/llm/extractor.py` line 80 |
| Change LLM inference parameters | Constants block in `backend/llm/extractor.py` lines 83–93 |
| Change the extraction schema | `self.schema` dict in `backend/llm/prompt.py` `PromptBuilder.__init__()` |
| Change system prompt or extraction rules | `system_prompt()` and `extraction_rules()` in `backend/llm/prompt.py` |
| Change PDF extraction strategy or threshold | `PDFExtractor.extract()` and `MIN_TEXT_LENGTH` in `backend/extraction/pdf_extractor.py` |
| Change text cleaning behavior | Individual stage methods in `backend/text_cleaning/cleaner.py`; or disable stages via `CleanerConfig` |
| Add a new unicode replacement | Extend `self.unicode_map` in `TextCleaner.__init__()` in `backend/text_cleaning/cleaner.py` |
| Change retry count or delay | `MAX_RETRIES` and `RETRY_DELAY` in `backend/llm/extractor.py` |
| Change validation repair logic | `_validate_value()` in `backend/llm/validator.py` |
| Change front-end data source path | `getJsonBaseUrl()` in `frontend/js/loader.js` AND `JSON_FOLDER` in `frontend/js/faculty.js` |
| Add a new filter to the dashboard | Add filter input to `index.html`, add state to `loader.state.filters`, handle in `filters.js` `renderFiltered()`, and add to `app.js` `populateFilters()` |
| Change the number of resumes loaded | Change the loop bound `<= 40` in `frontend/js/loader.js` `loadCandidates()` |
| Add evaluation for a new LLM model | Place extracted JSONs in `evaluation/result_llm/data/<new_model_name>/`; add model name to `MODELS` list in `evaluate_json.py` |
| Change evaluation metrics | Modify `metrics_json.py` (LLM benchmark) or `metrics.py` (text extraction benchmark) |
| Add a new tab to the faculty profile | Add `<button class="tab-btn" data-tab="newTab">` and `<section id="newTab" class="tab-panel">` to `faculty.html`; add a `renderNewTab()` call to `populatePage()` in `faculty.js` |

---

## 34. Complete Execution Example

### Input

```
data/raw_resumes/R-001.pdf
```

### Step-by-Step Trace

```
R-001.pdf
    │
    │  [pdf_extractor.py — PDFExtractor.extract()]
    │  PyMuPDF: fitz.open() → page.get_text() for each page
    │  Result: 3,200 characters of text → sufficient (≥ 100)
    │
    ▼
data/extracted_text/R-001.txt
    (raw text: contains "ﬁ" ligatures, smart quotes, bullet symbols,
     double spaces, control chars, long lines)
    │
    │  [cleaner.py — TextCleaner.clean()]
    │  Stage 1: Unicode NFKC + replacements → "fi" fixed, quotes normalized
    │  Stage 2: Control chars removed
    │  Stage 3: \r\n → \n
    │  Stage 4: "Pub-\nlication" → "Publication"
    │  Stage 5: \t → space
    │  Stage 6: double spaces collapsed
    │  Stage 7: bullets (already done in stage 1)
    │  Stage 8: trailing spaces trimmed
    │  Stage 9: blank lines collapsed
    │
    ▼
data/cleaned_text/R-001.txt
    (clean normalized text: ~3,100 characters)
    │
    │  [extractor.py — LLMExtractor.extract_resume()]
    │  Read file content
    │  Call prompt_builder.build_messages(resume_text)
    │    → system message + user message (rules + schema + text)
    │
    │  [extractor.py — LLMExtractor.call_llm()]
    │  ollama.chat(model="llama3.1:8b", messages=..., format="json",
    │              options={temperature:0.0, top_p:0.8, num_predict:8192})
    │  Wait up to 180 seconds (or indefinitely — timeout not wired)
    │
    ▼
Raw LLM Response:
    '{"personal_information": {"full_name": "Dr. AFZAL BEG", ...}}'
    │
    │  [validator.py — JSONValidator.validate()]
    │  clean_response(): no markdown fences found; extract {…} substring
    │  parse_json(): json.loads() → Python dict
    │  remove_unknown_keys(): strip any extra LLM-added keys
    │  validate_schema(): recursive type coercion + fill missing fields
    │
    ▼
Validated Python dict:
    {
      "personal_information": {
        "full_name": "Dr. AFZAL BEG",
        "total_experience": "11 years",
        "email": "afzalbeg09@gmail.com",
        ...
      },
      "education": [...],
      "experience": [...],
      "publication_summary": {
        "journal_publications": 4,
        "conference_publications": 2,
        "book_publications": 0,
        "book_chapters": 0,
        "patents": 0
      }
    }
    │
    │  [extractor.py — LLMExtractor.save_json()]
    │  json.dumps(data, indent=4, ensure_ascii=False)
    │
    ▼
data/extracted_json/R-001.json
    (indented UTF-8 JSON, 106 lines)
    │
    │  [Manual step: copy to evaluation folder]
    │
    ▼
evaluation/result_llm/data/qwen2.5_7b/R-001.json
    │
    │  [Frontend: loader.js — loadCandidates()]
    │  fetch("../evaluation/result_llm/data/qwen2.5_7b/R-001.json")
    │  normalizeCandidate(data, "R-001.json") → flat candidate object
    │
    │  [Frontend: app.js — buildCard(candidate)]
    │  Renders faculty card with initials "DA", name "Dr. AFZAL BEG",
    │  designation fallback, university, experience "11", pubs "6"
    │
    ▼
Faculty card displayed in browser dashboard
    │
    │  [User clicks "View Full Profile →"]
    │  window.location.href = "faculty.html?id=R-001"
    │
    │  [faculty.js — init()]
    │  getFacultyId() → "R-001"
    │  loadFacultyJSON("R-001") → fetch R-001.json
    │  populatePage() → renderHero(), renderStatistics(), etc.
    │
    ▼
Full faculty profile page rendered
```

### Key Intermediate Artifacts

| Artifact | Location | Size (approx.) |
|----------|----------|----------------|
| Raw PDF | `data/raw_resumes/R-001.pdf` | Variable (50–500 KB) |
| Extracted text | `data/extracted_text/R-001.txt` | ~3–20 KB |
| Cleaned text | `data/cleaned_text/R-001.txt` | ~3–20 KB (slightly smaller) |
| Extracted JSON | `data/extracted_json/R-001.json` | ~2–6 KB |
| Log entry | `logs/llm_extraction.log` | ~500 bytes per resume |

---

## 35. Architecture Summary

### What the System Currently Does

The LLM-Based Faculty Resume Information Extraction System is a **batch processing pipeline** that:

1. Accepts faculty resume PDFs
2. Extracts text using PyMuPDF (with pdfplumber fallback)
3. Applies deterministic Unicode normalization and whitespace cleaning
4. Sends cleaned text to a locally running LLM (via Ollama) with a structured JSON extraction prompt
5. Validates, repairs, and saves the JSON output per resume
6. Provides a static glassmorphism web dashboard for browsing the extracted profiles

The system also includes a research-grade **evaluation framework** that benchmarks three PDF extraction tools (PyMuPDF, pdfplumber, pdfminer) against human-annotated ground truth using F1/CER/BLEU/NED metrics, and benchmarks three LLM models (LLaMA 3.1, Qwen 2.5, Mistral) against ground-truth JSON using fuzzy field-level precision/recall/F1.

### How Components Interact

```
pdf_extractor.py  →  data/extracted_text/
      ↓
cleaner.py        →  data/cleaned_text/
      ↓
extractor.py  (uses prompt.py + validator.py)  →  data/extracted_json/
      ↓
[manual copy]  →  evaluation/result_llm/data/<model>/
      ↓
loader.js + app.js + filters.js  →  Browser Dashboard
      ↓
faculty.js  →  Faculty Profile Page
```

### What Is Production-Ready

- The text cleaning logic (`cleaner.py`) is correct and robust for the task
- The evaluation metrics framework is methodologically sound
- The JSON schema design is appropriate for faculty resume data
- The retry architecture concept (LLM + validation) is the right approach
- The CSS/visual design of the frontend is polished

### What Still Needs Improvement

- **Five critical bugs** must be fixed before the system runs correctly end-to-end (see Section 27)
- **Security**: XSS, path traversal, PII in logs
- **Missing dependencies** in `requirements.txt`
- **No state management, no database, no API**
- **No tests**
- **Hardcoded 40-resume limit** and model-specific paths
- **Deduplication not wired into pipeline**

### Recommended Next Development Phases

**Phase 1 — Fix Critical Bugs (1–2 days)**  
Fix the five critical bugs identified in Sections 27 and BUG-01 through BUG-05 of the audit. The system should be fully end-to-end functional after this phase.

**Phase 2 — Stabilize (1 week)**  
Fix bare imports, add missing dependencies, add `data/` to `.gitignore`, fix XSS by sanitizing all `innerHTML`, validate URL parameters, remove PII from logs, integrate deduplication into the pipeline.

**Phase 3 — Scale (2–4 weeks)**  
Add a manifest JSON for dynamic file discovery, replace sequential `fetch()` with `Promise.all()`, add parallel LLM processing with a thread pool, add pagination to the frontend grid.

**Phase 4 — Production (1–2 months)**  
Add a FastAPI backend, PostgreSQL for state tracking, Docker Compose configuration, HTTPS, authentication, automated tests, and CI/CD pipeline.

---

*Document generated by code inspection of all 30+ source files. Based strictly on actual implementations — no assumed features documented.*
