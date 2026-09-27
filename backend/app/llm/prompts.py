"""
LLM Prompts and Schemas for Resume Extraction, Institution Classification, Publication Venue Classification, and Hierarchical Merging.
"""

SCHEMA_STR_TEMPLATE = """{
  "personal_information": {
    "full_name": "John Doe or null",
    "current_designation": "Assistant Professor or null",
    "email": "email@example.com or null",
    "phone": "+91 9876543210 or null"
  },
  "education": [
    {
      "qualification_type": "UG | PG | PhD | PDF | JRF | Other",
      "degree": "PhD | M.Tech | B.Tech | M.Sc | B.Sc | MCA | MBA | etc",
      "stream": "Computer Science and Engineering",
      "university": "Name of College or University",
      "year": "Year of graduation or completion e.g. 2022",
      "cgpa": "CGPA or percentage string if available or null"
    }
  ],
  "publications": [
    {
      "publication_type": "journal | conference | book | book_chapter | patent | other",
      "publication_name": "Title of paper or patent",
      "venue_name": "Journal or Conference or Publisher name",
      "published_at": "YYYY-MM or YYYY if available or null",
      "publication_year": 2024
    }
  ],
  "experience": {
    "academic": [
      {
        "experience_type": "academic",
        "institution": "University / Institute Name",
        "role": "Designation / Role",
        "duration_years": 4.5
      }
    ],
    "industry": [
      {
        "experience_type": "industry",
        "organization": "Company / Organization Name",
        "role": "Role / Designation",
        "duration_years": 2.0,
        "location": "City/Country or null"
      }
    ]
  }
}"""

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
""" + SCHEMA_STR_TEMPLATE + """

INSTRUCTIONS:
1. Extract ALL education records available (UG, PG, PhD, etc.). Do not drop lower degrees.
2. Extract ALL publications and patents with their venue names and year.
3. Distinguish Academic Experience (teaching/research in universities) from Industry Experience (corporate/R&D jobs).
4. Calculate duration_years as a float if start/end years are given (e.g. 2020-2024 = 4.0 years).
5. If information is missing, set to null.

RESUME TEXT:
{resume_text}
"""

LEAF_EXTRACTION_USER_PROMPT_TEMPLATE = """This is a PART of a larger resume. Extract all information explicitly present in this part according to the JSON schema below.
Do not assume that information absent from this chunk is absent from the overall resume.
Do not invent or hallucinate information.

JSON SCHEMA:
""" + SCHEMA_STR_TEMPLATE + """

INSTRUCTIONS:
1. Extract ALL details present in this chunk.
2. If personal information (name, email, phone) is present in this chunk, extract it; otherwise set missing fields to null.
3. Extract ALL education, publication, and experience entries explicitly present in this chunk.
4. Return ONLY valid JSON matching the exact schema.

PARTIAL RESUME CHUNK:
{resume_text}
"""

MERGE_SYSTEM_PROMPT = """You are an expert resume data consolidation assistant.
Your task is to merge partial extraction results from overlapping parts of the SAME candidate resume into a single, unified JSON object.
You MUST output ONLY valid JSON matching the exact candidate schema.
Do NOT include preambles, markdown tags, or postscripts.
"""

MERGE_USER_PROMPT_TEMPLATE = """You are merging partial extraction results from the SAME resume.
The source text was divided into overlapping chunks.

The partial outputs may therefore contain:
* duplicate records
* partially duplicated records
* complementary fields
* incomplete records caused by chunk boundaries

Your job is to create ONE complete candidate record.

Rules:
1. Preserve ALL unique information.
2. Never discard a field simply because it is missing from another partial result.
3. Merge records that clearly refer to the same entity (e.g. same degree/university, same paper title/venue, same company/role).
4. Remove duplicates caused by overlapping chunks.
5. Combine complementary information from partial records (e.g., if Part 1 has start_date and Part 2 has end_date for the same role, combine them into one record).
6. Preserve exact names, dates, organizations, titles, numbers, degrees, skills, publications, etc.
7. Never invent information.
8. If two values conflict and the source information cannot be resolved confidently, preserve the information according to the existing schema rather than inventing a resolution.
9. Return ONLY valid JSON matching the exact schema below.

JSON SCHEMA:
{schema_str}

PARTIAL RESULT 1:
{json_a}

PARTIAL RESULT 2:
{json_b}

Merged JSON output:"""

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

BATCH_PUBLICATION_CLASSIFIER_PROMPT = """Classify each of the following academic publication venues (Journal, Conference, or Publisher) into Tier 1, Tier 2, or Tier 3.

Guidelines:
- Tier 1: Top-tier IEEE/ACM Transactions, Nature, Science, CORE A*/A conferences, Q1 SCI journals.
- Tier 2: Scopus indexed journals, recognized international conferences, IEEE/Springer conference proceedings, Q2/Q3 journals, UGC CARE list.
- Tier 3: Standard regional journals, open-access blogs, unindexed workshops, self-published media.

Venues list:
{venues_json}

Return ONLY valid JSON with no markdown tags:
{{
  "classifications": [
    {{
      "venue_name": "Exact venue name",
      "tier": "Tier 1 | Tier 2 | Tier 3",
      "score": 1.0,
      "reason": "Brief explanation"
    }}
  ]
}}
"""

BATCH_INSTITUTION_CLASSIFIER_PROMPT = """Classify each of the following educational or academic institutions into Tier 1, Tier 2, or Tier 3.

Guidelines:
- Tier 1: Top-tier global/national institutions (e.g. IITs, IISc, NITs, BITS, Ivy League, Stanford, MIT, Oxford, Top 50 global universities).
- Tier 2: Recognized state universities, reputed accredited colleges, established national universities.
- Tier 3: Standard unranked colleges, local institutes, unaccredited entities.

Institutions list:
{institutions_json}

Return ONLY valid JSON with no markdown tags:
{{
  "classifications": [
    {{
      "institution": "Exact institution name",
      "tier": "Tier 1 | Tier 2 | Tier 3",
      "score": 1.0,
      "reason": "Brief explanation"
    }}
  ]
}}
"""
