# Project Info: LLM-Based Faculty Resume Information Extraction System

An end-to-end, automated AI pipeline designed to extract, clean, validate, and visualize structured information from unstructured faculty resumes (PDF format). The system combines robust PDF text extraction, deterministic text cleaning, local Large Language Model (LLM) extraction with strict JSON schema enforcement, comprehensive evaluation tools, and an interactive web-based visualization dashboard.

---

## 📋 Table of Contents
- [System Architecture & Workflow](#-system-architecture--workflow)
- [Key Features](#-key-features)
- [Project Directory Structure](#-project-directory-structure)
- [Pipeline Component Breakdown](#-pipeline-component-breakdown)
  - [1. File & Text Deduplication](#1-file--text-deduplication)
  - [2. Multi-Engine PDF Extraction](#2-multi-engine-pdf-extraction)
  - [3. Deterministic Text Cleaning](#3-deterministic-text-cleaning)
  - [4. LLM-Based Extraction & Validation](#4-llm-based-extraction--validation)
  - [5. Evaluation & Benchmarking](#5-evaluation--benchmarking)
  - [6. Web Visualization Dashboard](#6-web-visualization-dashboard)
- [Extraction JSON Schema](#-extraction-json-schema)
- [Tech Stack & Dependencies](#-tech-stack--dependencies)
- [Getting Started & Usage Guide](#-getting-started--usage-guide)

---

## 🏗️ System Architecture & Workflow

The project follows a modular, 6-stage architecture that transforms raw PDF resumes into structured, searchable faculty profiles:

```
[ Raw Resumes (PDF) ]
         │
         ▼
 1. SHA-256 Deduplication  ──────────► Check against file_hashes.csv
         │
         ▼
 2. PDF Extraction Engine  ──────────► PyMuPDF (Primary) / pdfplumber (Fallback)
         │
         ▼
 3. Text Cleaning Pipeline ──────────► Unicode NFKC, Line Endings, De-hyphenation, Bullet Normalization
         │
         ▼
 4. LLM Extraction & Validation ─────► Ollama (LLaMA 3.1 8B / Qwen 2.5) + Recursive Schema Enforcement
         │
         ▼
 5. Data Export & Storage  ──────────► JSON Outputs / Evaluation Benchmarks
         │
         ▼
 6. Interactive Frontend   ──────────► Glassmorphism Dashboard, Search, Filters, & Faculty Profiles
```

---

## ✨ Key Features

- **Duplicate Prevention**: SHA-256 hash calculation prevents re-processing identical files and text content.
- **Hybrid Extraction**: High-performance extraction using PyMuPDF (`fitz`) with automatic fallback to `pdfplumber` for lower-level fallback scanning.
- **Deterministic Cleaning**: 9-stage text normalization pipeline that cleans Unicode symbols, fixes word wrapping across hyphenated line breaks, removes non-printable control characters, and standardizes bullet structures.
- **Strict LLM Schema Enforcement**: Uses local LLM inference via [Ollama](https://ollama.ai) coupled with a recursive JSON validator that handles missing fields, strips out unknown keys, cleans markdown noise, and handles retries automatically.
- **Evaluation Framework**: Built-in benchmarking suite measuring extraction accuracy (Levenshtein distance, character error rates) and field-level precision/recall against ground-truth JSON files.
- **Modern Web Dashboard**: Glassmorphism web UI with dark/light themes, live search, multi-faceted filtering (experience, designation, publications, patents, degrees), overview charts (Chart.js), and detailed faculty profile views.

---

## 📁 Project Directory Structure

```
LLM_Based_Extraction/
├── backend/                        # Backend Python pipeline
│   ├── deduplication/              # File and text hashing modules
│   │   └── hash_checker.py         # SHA-256 hash calculation and CSV tracking
│   ├── extraction/                 # PDF text extraction engine
│   │   └── pdf_extractor.py        # PyMuPDF and pdfplumber extraction logic
│   ├── text_cleaning/              # Text normalization & cleaning engine
│   │   ├── cleaner.py              # TextCleaner class & 9-stage pipeline
│   │   ├── cleaning_report.py      # Statistical reporting generator
│   │   └── report/                 # Cleaning statistics JSON reports
│   ├── llm/                        # LLM prompt, execution, and validation
│   │   ├── prompt.py               # Extraction prompt builder & target JSON schema
│   │   ├── validator.py            # Recursive JSON parser & schema validator
│   │   └── extractor.py            # Ollama client caller with retry loops
│   └── utils.py                    # Project path helper utilities
├── frontend/                       # Web visualization dashboard
│   ├── index.html                  # Main dashboard overview page
│   ├── faculty.html                # Detailed faculty profile viewer page
│   ├── css/                        # Custom modular styling (glassmorphism UI)
│   └── js/                         # Frontend logic (Chart.js, filters, loader, search)
│       ├── app.js                  # Main dashboard app initializer & stats cards
│       ├── dashboard.js            # Analytical summary & metrics calculation
│       ├── faculty.js              # Faculty detail page rendering script
│       ├── filters.js              # Multi-faceted filter panel handler
│       ├── loader.js               # JSON dataset loader & state management
│       └── search.js               # Real-time search query listener
├── data/                           # Data storage pipeline
│   ├── raw_resumes/                # Input PDF resume documents
│   ├── extracted_text/             # Raw extracted text files (.txt)
│   ├── cleaned_text/               # Preprocessed & cleaned text (.txt)
│   ├── extracted_json/             # Final validated LLM JSON output files
│   ├── invalid_json/               # Logged raw responses that failed parsing
│   ├── ground_truth/               # Reference benchmark data
│   └── metadata/                   # Hash tracking files (file_hashes.csv)
├── evaluation/                     # Accuracy & precision metrics framework
│   ├── result_text_extraction/     # Levenshtein & OCR extraction metrics & plots
│   └── result_llm/                 # Field-level accuracy, precision & recall metrics
├── logs/                           # System execution logs (llm_extraction.log)
├── requirements.txt                # Python package dependencies
└── README.md                       # Project documentation
```

---

## ⚙️ Pipeline Component Breakdown

### 1. File & Text Deduplication
- **File**: [`backend/deduplication/hash_checker.py`](file:///e:/LLM_Based_Extraction/backend/deduplication/hash_checker.py)
- **Function**: Computes SHA-256 hex digests of incoming PDF resumes in 8KB chunks. Compares computed hashes with `data/metadata/file_hashes.csv` to flag duplicates before running costly extraction pipelines.

### 2. Multi-Engine PDF Extraction
- **File**: [`backend/extraction/pdf_extractor.py`](file:///e:/LLM_Based_Extraction/backend/extraction/pdf_extractor.py)
- **Function**: Extracts text from raw PDF resumes using a tiered strategy:
  1. Attempts primary fast extraction using **PyMuPDF** (`fitz`).
  2. Evaluates extracted text length against `MIN_TEXT_LENGTH = 100`.
  3. If text length is insufficient, falls back to **pdfplumber** layout extraction.
  4. Saves extracted text into `data/extracted_text/`.

### 3. Deterministic Text Cleaning
- **File**: [`backend/text_cleaning/cleaner.py`](file:///e:/LLM_Based_Extraction/backend/text_cleaning/cleaner.py)
- **Function**: Applies a non-destructive 9-stage cleaning pipeline:
  - **Unicode Normalization**: NFKC normalization + explicit replacement map (ligatures like `ﬁ` $\rightarrow$ `fi`, quotes, en/em dashes).
  - **Control Character Removal**: Strips non-printable control characters `\x00-\x08`, `\x0B-\x0C`, `\x0E-\x1F`.
  - **Line Ending & Space Normalization**: Standardizes `\r\n` to `\n`, converts tabs to single spaces, and collapses double/multiple space sequences.
  - **De-hyphenation**: Joins words split across line breaks with hyphens (`pattern: ([A-Za-z])-\n([A-Za-z])`).
  - **Bullet Symbol Normalization**: Converts diverse bullet point symbols (`•`, `●`, `▪`, `►`, `✓`) into clean ASCII hyphens (`-`).
  - **Blank Line Collapsing**: Restricts consecutive blank lines to a maximum of two (`\n\n`).
  - Generates full summary analytics exported to `backend/text_cleaning/report/cleaning_statistics.json`.

### 4. LLM-Based Extraction & Validation
- **Prompt Builder**: [`backend/llm/prompt.py`](file:///e:/LLM_Based_Extraction/backend/llm/prompt.py) defines the structured schema and strict system instructions (e.g., zero markdown wrapping, no hallucinated fields, publication count aggregations).
- **LLM Extractor**: [`backend/llm/extractor.py`](file:///e:/LLM_Based_Extraction/backend/llm/extractor.py) communicates with a local **Ollama** server running models such as `llama3.1:8b`, `qwen2.5:7b`, or `mistral:7b`. Features zero-temperature inference, configurable retry counts (`MAX_RETRIES = 3`), and response timing logs.
- **JSON Validator**: [`backend/llm/validator.py`](file:///e:/LLM_Based_Extraction/backend/llm/validator.py) receives raw LLM string responses and executes:
  - Stripping of markdown code fences (```json ... ```) and prefix phrases ("Here is the JSON:").
  - Extraction of the outermost JSON object bounds (`{ ... }`).
  - Recursive schema enforcement: populates missing fields with default type values (`""` for strings, `[]` for arrays, `0` for numbers), strips unknown keys not present in the master schema, and dumps unparseable responses to `data/invalid_json/` for auditing.

### 5. Evaluation & Benchmarking
- **Text Extraction Benchmark**: Located in [`evaluation/result_text_extraction/`](file:///e:/LLM_Based_Extraction/evaluation/result_text_extraction/). Evaluates PDF extraction fidelity against ground truth text using string distance metrics and outputs visualization plots.
- **LLM Accuracy Benchmark**: Located in [`evaluation/result_llm/`](file:///e:/LLM_Based_Extraction/evaluation/result_llm/). Compares extracted JSON against ground truth JSON structures across field-level precision, recall, F1 scores, and JSON syntax validity.

### 6. Web Visualization Dashboard
- **Main View**: [`frontend/index.html`](file:///e:/LLM_Based_Extraction/frontend/index.html) presents an interactive dashboard featuring:
  - Overview cards: Total Faculty, PhD count, Assistant/Associate/Full Professor distribution, Average Experience, total publications, patents, and top universities.
  - Multi-criteria Filter Panel: Filter by highest degree, institution type, designation, experience range (0-2, 2-5, 5-10, 10+ years), and presence of journal publications, conference papers, or patents.
  - Faculty Grid: Interactive cards presenting candidate initials, degree badges, current institution, experience, publication count, and profile navigation button.
- **Faculty Profile View**: [`frontend/faculty.html`](file:///e:/LLM_Based_Extraction/frontend/faculty.html) renders complete faculty dossiers including personal/contact information, education timeline, work experience history, and publication breakdown charts.

---

## 📊 Extraction JSON Schema

The LLM extracts candidate information strictly conforming to the following target schema:

```json
{
    "personal_information": {
        "full_name": "Dr. Jane Doe",
        "current_designation": "Associate Professor",
        "total_experience": "12 Years",
        "email": "jane.doe@university.edu",
        "phone": "+1-555-0199",
        "date_of_birth": "1982-05-14",
        "gender": "Female",
        "address": "Department of Computer Science, State University",
        "linkedin": "https://linkedin.com/in/janedoe",
        "google_scholar": "https://scholar.google.com/citations?user=example",
        "researchgate": "https://researchgate.net/profile/Jane-Doe"
    },
    "education": [
        {
            "degree": "Ph.D.",
            "specialization": "Computer Science & Engineering",
            "institution": "Indian Institute of Technology",
            "board_university": "IIT",
            "year": "2012",
            "cgpa_percentage": "9.5/10"
        }
    ],
    "experience": [
        {
            "designation": "Associate Professor",
            "organization": "State University",
            "start_date": "2018",
            "end_date": "Present",
            "duration": "6 Years",
            "description": "Leading research in artificial intelligence and teaching undergraduate courses."
        }
    ],
    "publication_summary": {
        "journal_publications": 14,
        "conference_publications": 22,
        "book_publications": 2,
        "book_chapters": 5,
        "patents": 3
    }
}
```

---

## 🛠️ Tech Stack & Dependencies

- **Language**: Python 3.9+
- **PDF Processing**: PyMuPDF (`fitz`), `pdfplumber`
- **Data Manipulation**: `pandas`, `dataclasses`, `pathlib`, `json`, `re`
- **LLM Integration**: `ollama` (Local inference using LLaMA 3.1 / Qwen 2.5 / Mistral)
- **Frontend Stack**: HTML5, Vanilla CSS3 (Glassmorphic Design, Dark/Light Themes), JavaScript (ES6+), FontAwesome 6, Chart.js

---

## 🚀 Getting Started & Usage Guide

### Prerequisites
1. Install Python 3.9 or higher.
2. Install and launch [Ollama](https://ollama.ai/).
3. Pull your target LLM model in Ollama:
   ```bash
   ollama pull llama3.1:8b
   ```

### Installation
1. Clone the repository or navigate to the project directory:
   ```bash
   cd e:/LLM_Based_Extraction
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Execution Steps

#### Step 1: Place Resumes
Copy raw PDF resume files into `data/raw_resumes/`.

#### Step 2: Extract Text from Resumes
Run the PDF extractor:
```bash
python backend/extraction/pdf_extractor.py
```

#### Step 3: Clean Extracted Text
Run the text cleaner:
```bash
python backend/text_cleaning/cleaner.py
```

#### Step 4: Run LLM Extraction & Schema Validation
Run the LLM extraction pipeline:
```bash
python backend/llm/extractor.py
```

#### Step 5: Launch Visualization Dashboard
Open [`frontend/index.html`](file:///e:/LLM_Based_Extraction/frontend/index.html) in your browser or run a simple local HTTP server:
```bash
python -m http.server 8000 --directory frontend
```
Navigate to `http://localhost:8000` to view the interactive Faculty Intelligence Dashboard.
