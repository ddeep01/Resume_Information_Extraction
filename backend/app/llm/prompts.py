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
      "qualification_type": "PhD | Post Doctoral | PG | UG | Other",
      "degree": "Degree or Qualification title e.g. Ph.D. / B.Tech / 12th / 10th",
      "stream": "Specialization or stream e.g. Computer Science or null",
      "university": "Name of College / University / Board / School or null",
      "year": "Year of completion e.g. 2022 or null",
      "cgpa": "CGPA or percentage string if available or null"
    }
  ],
  "publications": [
    {
      "publication_type": "journal | conference | book | book_chapter | patent | other",
      "publication_name": "Actual paper/publication title",
      "venue_name": "Actual journal/conference/book/venue or null",
      "publication_year": 2023
    }
  ],
  "experience": {
    "academic": [
      {
        "institution": "University / Research Institute",
        "role": "Research Fellow / JRF / SRF / Postdoc / Scholar",
        "start_date": "YYYY-MM or YYYY or null",
        "end_date": "YYYY-MM or YYYY or Present or null",
        "duration_years": 2.0,
        "description": "Brief description of responsibilities or null"
      }
    ],
    "professional": [
      {
        "institution": "University / Institute / Company",
        "role": "Assistant Professor / Lecturer / Software Engineer",
        "start_date": "YYYY-MM or YYYY or null",
        "end_date": "YYYY-MM or YYYY or Present or null",
        "duration_years": 4.5,
        "description": "Brief description of responsibilities or null"
      }
    ]
  },
  "total_experience": 6.5
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
1. COMPREHENSIVE EDUCATION EXTRACTION ACROSS ENTIRE RESUME:
   - Carefully inspect the ENTIRE resume from start to finish, not only a section titled "Education".
   - Educational qualifications may appear under "Academic Background", "Qualifications", "Educational Profile", "Degrees", or inline descriptions.
   - Extract ALL separate education records present in the resume from highest to lowest: Post Doctoral, PhD, PG, UG, 12th, 10th.
   - SEPARATE EDUCATION RECORDS: If the resume contains multiple qualifications, extract them as SEPARATE records. NEVER merge distinct degrees (e.g. B.Tech and M.Tech, or 10th and 12th) into a single record.

2. PRECISE EDUCATION LEVEL / QUALIFICATION CLASSIFICATION:
   For every education record, accurately map "qualification_type" to exactly one of:
   - "PhD": For Doctor of Philosophy, Doctorate, Ph.D., D.Phil.
   - "Post Doctoral": For Postdoctoral Fellow, Post Doctoral Researcher, Post-Doc training, PDF.
     * CRITICAL: Post Doctoral must NEVER be classified as "PhD". For example, "Post Doctoral Researcher — Tufts University" must have "qualification_type": "Post Doctoral" (NEVER "PhD").
   - "PG": For Master's degrees, e.g. M.Tech, M.E., M.Sc, M.S., MCA, MBA, M.Com, M.A., M.Phil.
   - "UG": For Bachelor's degrees, e.g. B.Tech, B.E., B.Sc, B.S., BCA, BBA, B.Com, B.A.
   - "Other": For secondary education and other diplomas/certificates:
     * 12th / HSC / Higher Secondary / Intermediate / Plus Two / Pre-University / PUC -> "Other"
     * 10th / SSC / Secondary / Matriculation / High School -> "Other"
     * Diplomas, vocational certificates -> "Other"

3. FIELD EXTRACTION GUIDELINES FOR EACH EDUCATION RECORD:
   - "qualification_type": "PhD" | "Post Doctoral" | "PG" | "UG" | "Other"
   - "degree": The exact qualification or degree name (e.g. "Ph.D. Computer Science", "B.Tech", "M.Tech", "Higher Secondary / 12th", "Secondary School / 10th").
   - "stream": Specialization, major, or stream (e.g. "Computer Science and Engineering", "Commerce", "Science", or null if not stated).
   - "university": Name of the College, University, Institution, School, or Examination Board (e.g. "Tufts University", "University of Delhi", "CBSE", "State Board", or null).
   - "year": Year of graduation or completion (e.g. "2022", "2018 - 2022", or null if unavailable).
   - "cgpa": CGPA, GPA, percentage, or division string if mentioned (e.g. "8.9 CGPA", "85%", or null if unavailable).
   - Use null when information is genuinely unavailable. Do NOT invent or hallucinate data.

4. AVOID INCORRECT EDUCATION EXTRACTION (STRICT ANTI-POLLUTION):
   Do NOT extract the following as education:
   - Certifications (e.g., NPTEL, Coursera, AWS, Azure, Cisco, PMP)
   - Workshops, training sessions, faculty development programs (FDPs)
   - Seminars, webinars, conference attendances
   - Professional employment or corporate jobs
   - Independent research positions or research fellowships that are not post-doctoral/academic degrees
   - Academic capstone projects or student coursework
   - Research publications, patents, or paper titles
   unless the resume explicitly lists them as a formal academic degree or diploma.

5. COMPREHENSIVE PUBLICATION EXTRACTION ACROSS ENTIRE RESUME:
   - Inspect the ENTIRE resume from start to finish, not only a section titled "Publications".
   - Publications may appear under various headings: "Research Papers", "Journal Articles", "Refereed Publications", "Conference Proceedings", "Conference Papers", "Patents", "Book Chapters", "Books", "Publications Profile", "Scientific Contributions", "Selected Works", "Bibliography", or inline in profile text.
   - Extract EVERY genuine publication. Do not skip or truncate the list.
3. PRECISE PUBLICATION FIELD IDENTIFICATION & DISAMBIGUATION:
   For every genuine publication, accurately identify and map each field:
   - "publication_type": Exactly one of:
     * "journal" (for journal articles, transactions, letters, periodicals)
     * "conference" (for conference proceedings, symposiums, workshops with published papers)
     * "book" (for authored or edited books)
     * "book_chapter" (for book chapters in edited volumes)
     * "patent" (for granted or published utility / design patents)
     * "other" (for preprints e.g. arXiv, technical reports, or other genuine publications)
   - "publication_name": The actual title of the research paper, article, chapter, or patent.
     * Extract ONLY the title of the paper or patent.
     * NEVER include author names in "publication_name" (e.g., if citation is "X. Wang and E. Nalisnick. Are Vision Language Models Robust...", title is "Are Vision Language Models Robust to Classic Uncertainty Challenges?").
     * NEVER include venue names, conference names, or publisher names in "publication_name".
     * Strip prefixes such as "Paper Title:", "Paper Title", "Title:", leading numbering (e.g. "1. ", "• "), or enclosing quotes.
   - "venue_name": The actual journal, conference, book, or patent office/number.
     * Example journals: "Transactions on Machine Learning Research (TMLR)", "Nature Reviews Neuroscience", "IEEE Computer Graphics and Applications", "PLOS Computational Biology", "International Research Journal of Management Science and Technology".
     * Example conferences: "Advances in Neural Information Processing Systems (NeurIPS)", "International Conference on Learning Representations (ICLR)", "ICML", "CVPR", "ECCV", "Interspeech".
     * Example patents: "US Patent Office", "Indian Patent Office", or patent number (e.g. "US08280158", "US11308614B2").
     * CRITICAL: NEVER confuse publication title, venue, publisher, or year.
     * "2023", "2024", or any year must NEVER become "venue_name".
     * Do NOT put a standalone publisher name (e.g., "IEEE", "Springer", "Elsevier") as "venue_name" unless no specific journal or conference is mentioned.
     * If the venue is missing or not stated in the resume, set "venue_name" to null.
   - "publication_year": Integer 4-digit year (e.g. 2023), or null if no year can be determined.
4. STRICT PUBLICATION ANTI-POLLUTION RULES (DO NOT EXTRACT AS PUBLICATIONS):
   Do NOT extract any of the following into publications:
   - Research interests or topics (e.g., "Areas of Research: Generative AI, IoT", "Research Interests").
   - Thesis or dissertation (e.g., "Dissertation: On Priors for Bayesian Neural Networks", "PhD Thesis", "M.S. Thesis").
   - Student academic projects, capstone projects, or college coursework.
   - Presentations, talks, seminars, or conference attendance where no paper was published (e.g., "Participation in Conference on...", "Attended Workshop on Research Paper Writing", "Session chair").
   - Workshops, seminars, webinars, or FDPs organized or attended without evidence of an actual published paper.
   - Journal reviewing or editorial board entries (e.g., "Reviewer for Journal of Econometrics", "Top Reviewer NeurIPS").
   - Publisher names or a journal/conference name listed alone without evidence of an actual publication.
5. PARTIAL / MISSING INFORMATION HANDLING FOR PUBLICATIONS:
   - If a genuine publication has missing information (such as missing venue, missing month, or missing pages), keep the available data and use null for missing fields.
   - Do NOT invent or hallucinate missing information.
   - Do NOT discard or drop valid publications simply because some fields are missing.
6. COMPREHENSIVE WORK EXPERIENCE SEARCH ACROSS ENTIRE RESUME:
   - Carefully inspect the ENTIRE resume from start to finish, not only a section titled "Experience".
   - Work experience and total years may appear anywhere: check "Professional Summary", "Career Profile", "About Me", "Academic Employment", "Industrial Employment", "Teaching Experience", "Work History", or natural language inline descriptions (e.g., "Currently working as Assistant Professor at University A since 2019", "Worked at ABC from 2015 to 2018").
7. TWO EXPERIENCE SECTIONS INSIDE "experience" (dict of lists):
   - "experience" MUST be a dictionary containing exactly two lists: {"academic": [...], "professional": [...]}.
   - "academic": Genuine research fellowship, research scholar, or academic research positions:
     * Junior Research Fellow (JRF)
     * Senior Research Fellow (SRF)
     * Research Fellow / Research Scholar / Project Fellow / Academic Fellow
     * Postdoctoral Fellow / Postdoctoral Researcher / Postdoc
     * Teaching Assistant (TA) / Graduate Assistant
     * CRITICAL: Do NOT treat research topics, research projects, PhD degree coursework, thesis/dissertation, or publications themselves as experience records!
   - "professional": Genuine professional employment and career appointments, including:
     * Actual teaching / faculty experience: Assistant Professor, Associate Professor, Professor, Lecturer, Senior Lecturer, Teaching Faculty, Reader, Adjunct/Visiting Faculty, Instructor.
     * Industry / corporate employment: Software Engineer, Data Scientist, Tech Lead, Analyst, Consultant, Corporate Researcher, etc.
8. EXTRACTING INDIVIDUAL EXPERIENCE RECORDS & DATES:
   - For every genuine experience record in "academic" and "professional", extract:
     * "institution": Name of University / Institute / Company.
     * "role": Designation / Job Title / Role.
     * "start_date": Employment start date (e.g. "2018-01", "Jan 2018", "2018", or null if unavailable).
     * "end_date": Employment end date (e.g. "2022-12", "Dec 2022", "2022", or "Present", "Current", "Till Date", "Ongoing", "Now", or null if unavailable).
     * "duration_years": Number of years as a decimal float (e.g. 4.5, 2.0).
     * "description": Brief description of duties/responsibilities or null.
   - If the resume explicitly states duration (e.g., "11 years and 4 months", "5 Years 10 Months", "3 years"), recognize and convert it to float (e.g., 11.33, 5.83, 3.0).
   - If it provides employment dates but does not state duration, determine the duration from those dates (e.g., 2018 to 2022 = 4.0 years).
   - Recognize different date formats and current employment markers naturally: "Present", "Current", "Till Date", "Ongoing", "Now", "Presently Working". When currently employed, calculate duration from the start date up to the present date (current year).
   - Do NOT invent missing dates. If dates are unavailable, keep them as null and do NOT discard the experience record.
9. CANDIDATE TOTAL EXPERIENCE ("total_experience"):
   - Add the candidate-level float field "total_experience": 8.5.
   - This represents the candidate's total relevant professional/academic experience based on the extracted experience records.
   - Do NOT double-count overlapping periods across multiple concurrent roles.
   - Do NOT count career gaps between separate jobs as experience.
   - Do NOT count education, projects, certifications, publications, or unrelated activities as experience.
   - CRITICAL: Do NOT return 0 experience simply because the candidate did not explicitly write "X years of experience". If the resume lists employment records with dates (e.g. "Assistant Professor — University A — 2018-Present"), infer and compute the total experience from those dates!
   - If the candidate explicitly states total experience anywhere (e.g. "10 years", "10+ years", "8.5 years", "over 10 years", "a decade"), recognize and preserve it.
10. STRICT EXPERIENCE ANTI-POLLUTION RULES:
   - Do NOT put unrelated information into experience.
   - Specifically, do NOT extract any of the following as experience:
     * University accreditation (e.g. NAAC Grade A++, NBA, ABET)
     * NAAC information / NAAC committee representations
     * Research topics / Research interests / Areas of specialization
     * Publications / Journal articles / Conference papers / Patents
     * Academic projects / College capstone projects / Course assignments
     * Thesis / Dissertation
     * Educational degrees / Degree study periods (e.g. "B.Tech Student 2014-2018")
     * Certifications (e.g. NPTEL, AWS, Coursera, PMP)
11. EMPTY / FRESH GRADUATE RESUMES:
   - If the resume contains no professional or academic employment history, return {"academic": [], "professional": []} for experience and 0.0 for total_experience.
   - If no education records exist, return [] for education.
   - If no publications exist, return [] for publications.
12. RETURN ONLY VALID JSON matching the schema.

RESUME TEXT:
{resume_text}
"""

LEAF_EXTRACTION_USER_PROMPT_TEMPLATE = """This is a PART of a larger resume. Extract all candidate information explicitly present in this part according to the JSON schema below.
Do not assume that information absent from this chunk is absent from the overall resume.
Do not invent or hallucinate information.

JSON SCHEMA:
""" + SCHEMA_STR_TEMPLATE + """

INSTRUCTIONS:
1. Extract ALL details present in this chunk.
2. If personal information (name, email, phone) is present in this chunk, extract it; otherwise set missing fields to null.
3. EDUCATION IN THIS CHUNK:
   - Extract ALL separate education records present in this chunk (Post Doctoral, PhD, PG, UG, 12th, 10th).
   - Accurately distinguish:
     * PhD / Doctorate -> "PhD"
     * Postdoctoral / Post Doc -> "Post Doctoral" (CRITICAL: Post Doctoral must NEVER be classified as "PhD")
     * Master's / M.Sc / M.Tech / MBA / M.E. -> "PG"
     * Bachelor's / B.Sc / B.Tech / B.E. -> "UG"
     * 12th / HSC / Higher Secondary -> "Other"
     * 10th / SSC / Secondary -> "Other"
   - Extract qualification_type, degree, stream, university, year, cgpa. Use null for unavailable fields.
   - Do NOT extract certifications, workshops, seminars, employment, projects, or publications as education.
   - Do NOT merge distinct degrees into one record.
4. PUBLICATIONS IN THIS CHUNK:
   - Extract ALL genuine publications (journals, conferences, books, book chapters, patents, preprints) present in this chunk.
   - Accurately map "publication_type" ("journal", "conference", "book", "book_chapter", "patent", "other").
   - Extract the actual paper/patent title as "publication_name" (never author names, never venue, never year).
   - Extract the actual journal/conference/book/patent office as "venue_name" (NEVER put the year e.g. "2023" as venue_name; use null if missing).
   - Extract "publication_year" (integer e.g. 2023 or null).
   - Do NOT extract research topics, thesis/dissertation, projects, presentations, workshops, seminars, or conference attendance without a paper.
   - If genuine publication has missing fields, preserve available data and use null for missing fields. Do NOT invent or discard valid publications.
5. WORK EXPERIENCE IN THIS CHUNK:
   - Carefully inspect this chunk for any professional employment details or explicit experience mentions.
   - Return "experience" as a dictionary with two lists: {"academic": [...], "professional": [...]}.
     * "academic": Research fellowship/scholar positions (JRF, SRF, Postdoc, Research Fellow/Scholar, Project Fellow).
     * "professional": Actual teaching experience (Assistant Professor, Professor, Lecturer, Faculty) and industry/corporate employment.
     * Do NOT extract research topics, thesis, projects, degrees, or certifications as experience.
   - For every genuine position, extract "institution", "role", "start_date", "end_date", "duration_years", and "description".
   - Recognize "Present", "Current", "Till Date", "Ongoing", "Now".
   - Compute or preserve "total_experience" across the extracted records. Do NOT return 0 experience simply because explicit words like "X years of experience" were not used.
6. Return ONLY valid JSON matching the exact schema.

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
1. Preserve ALL unique information across education, publications, and experience.
2. Never discard a field simply because it is missing from another partial result.
3. Merge records that clearly refer to the same entity (e.g. same degree/university, same paper title/venue, same company/role).
4. Remove duplicates caused by overlapping chunks.
5. Combine complementary information from partial records (e.g., if Part 1 has paper title and Part 2 has venue name or year, combine them into one complete publication record).
6. EDUCATION CONSOLIDATION:
   - Consolidate all genuine education records into "education".
   - Deduplicate education records that refer to the same qualification/degree and institution.
   - Combine complementary information from partial records across chunk boundaries (e.g. degree + university from Part 1, year + CGPA from Part 2).
   - Never merge distinct degrees (e.g. 10th and 12th, or B.Tech and M.Tech).
   - Always keep "Post Doctoral" distinct from "PhD".
7. PUBLICATION CONSOLIDATION:
   - Consolidate all genuine publication records into "publications".
   - Deduplicate publications that refer to the same paper title.
   - Ensure "venue_name" is never a year (e.g. "2023" must never become "venue_name") or publisher name alone.
   - Preserve valid publications even if some fields are null.
   - Do NOT allow research topics, thesis, presentations, or conference attendance into publications.
8. WORK EXPERIENCE CONSOLIDATION:
   - Consolidate all genuine experience records into {"academic": [...], "professional": [...]}.
   - Put research fellowships/scholars into "academic" and actual teaching faculty/industry roles into "professional".
   - Recalculate/infer "total_experience" as the continuous non-overlapping total years across all merged records. Do not assume missing explicit experience means 0.
   - Ensure current positions ("Present", "Current", "Till Date") retain active duration up to present.
   - Do NOT allow NAAC, accreditation, projects, thesis, degrees, or certifications into the experience lists.
9. Preserve exact names, dates, organizations, titles, numbers, degrees, skills, publications, etc.
10. Never invent information.
11. If two values conflict and the source information cannot be resolved confidently, preserve the information according to the existing schema rather than inventing a resolution.
12. Return ONLY valid JSON matching the exact schema below.

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
