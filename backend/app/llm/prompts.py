"""
LLM Prompts and Schemas for Resume Extraction, Institution Classification, and Publication Venue Classification.
"""

EXTRACTION_SYSTEM_PROMPT = """You are an expert recruiter and resume parser assistant.
Your task is to extract structured candidate information from the provided cleaned resume text.
You MUST output ONLY valid JSON matching the exact JSON schema provided.
Do NOT wrap your output in ```json or markdown tags.
Do NOT include any explanations, preambles, or postscripts.
Extract ONLY factual information present in the resume. Never invent or hallucinate data.
Represent missing values as null.
"""

EXTRACTION_USER_PROMPT_TEMPLATE = """Extract structured candidate details from this resume according to the JSON schema below.

JSON SCHEMA:
{{
  "personal_information": {{
    "full_name": "John Doe or null",
    "current_designation": "Assistant Professor or null",
    "email": "email@example.com or null",
    "phone": "+91 9876543210 or null"
  }},
  "education": [
    {{
      "qualification_type": "UG | PG | PhD | PDF | JRF | Other",
      "degree": "PhD | M.Tech | B.Tech | M.Sc | B.Sc | MCA | MBA | etc",
      "stream": "Computer Science and Engineering",
      "university": "Name of College or University",
      "year": "Year of graduation or completion e.g. 2022",
      "cgpa": "CGPA or percentage string if available or null"
    }}
  ],
  "publications": [
    {{
      "publication_type": "journal | conference | book | book_chapter | patent | other",
      "publication_name": "Title of paper or patent",
      "venue_name": "Journal or Conference or Publisher name",
      "published_at": "YYYY-MM or YYYY if available or null",
      "publication_year": 2024
    }}
  ],
  "experience": {{
    "academic": [
      {{
        "experience_type": "academic",
        "institution": "University / Institute Name",
        "role": "Designation / Role",
        "duration_years": 4.5
      }}
    ],
    "industry": [
      {{
        "experience_type": "industry",
        "organization": "Company / Organization Name",
        "role": "Role / Designation",
        "duration_years": 2.0,
        "location": "City/Country or null"
      }}
    ]
  }}
}}

INSTRUCTIONS:
1. Extract ALL education records available (UG, PG, PhD, etc.). Do not drop lower degrees.
2. Extract ALL publications and patents with their venue names and year.
3. Distinguish Academic Experience (teaching/research in universities) from Industry Experience (corporate/R&D jobs).
4. Calculate duration_years as a float if start/end years are given (e.g. 2020-2024 = 4.0 years).
5. If information is missing, set to null.

RESUME TEXT:
{resume_text}
"""

INSTITUTION_CLASSIFIER_PROMPT = """Classify the following educational or academic institution into Tier 1, Tier 2, or Tier 3.

Guidelines:
- Tier 1: Top-tier global/national institutions (e.g. IITs, IISc, NITs, BITS, Ivy League, Stanford, MIT, Oxford, Top 50 global universities).
- Tier 2: Recognized state universities, reputed accredited colleges, established national universities.
- Tier 3: Standard unranked colleges, local institutes, unaccredited entities.

Institution Name: {institution_name}

Return ONLY valid JSON with no markdown:
{{
  "institution": "{institution_name}",
  "tier": "Tier 1 | Tier 2 | Tier 3",
  "score": 1.0,
  "reason": "Brief explanation of tier classification"
}}
"""

PUBLICATION_CLASSIFIER_PROMPT = """Classify the following academic publication venue (Journal, Conference, or Publisher) into Tier 1, Tier 2, or Tier 3.

Guidelines:
- Tier 1: Top-tier IEEE/ACM Transactions, Nature, Science, CORE A*/A conferences, Q1 SCI journals.
- Tier 2: Scopus indexed journals, recognized international conferences, IEEE/Springer conference proceedings, Q2/Q3 journals, UGC CARE list.
- Tier 3: Standard regional journals, open-access blogs, unindexed workshops, self-published media.

Venue Name: {venue_name}

Return ONLY valid JSON with no markdown:
{{
  "venue_name": "{venue_name}",
  "tier": "Tier 1 | Tier 2 | Tier 3",
  "score": 1.0,
  "reason": "Brief explanation of venue tier classification"
}}
"""
