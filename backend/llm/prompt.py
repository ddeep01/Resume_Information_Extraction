"""
Faculty Resume Prompt Builder.

Project:
    LLM Based Faculty Resume Information Extraction

Purpose:
    Builds optimized prompts for extracting structured
    information from faculty resumes.

Responsibilities:
    - Store extraction schema
    - Build system prompt
    - Build user prompt
    - Return chat messages for Ollama

Does NOT:
    - Call LLM
    - Parse JSON
    - Save files
"""

from __future__ import annotations

import json
from typing import Dict, List


class PromptBuilder:
    """Production Prompt Builder."""

    def __init__(self):

        ######################################################################
        # OUTPUT SCHEMA
        ######################################################################

        self.schema = {

            "personal_information": {

                "full_name": "",
                "current_designation": "",
                "total_experience": "",
                "email": "",
                "phone": "",
                "date_of_birth": "",
                "gender": "",
                "address": "",
                "linkedin": "",
                "google_scholar": "",
                "researchgate": ""

            },

            "education": [

                {

                    "degree": "",
                    "specialization": "",
                    "institution": "",
                    "board_university": "",
                    "year": "",
                    "cgpa_percentage": ""

                }

            ],

            "experience": [

                {

                    "designation": "",
                    "organization": "",
                    "start_date": "",
                    "end_date": "",
                    "duration": "",
                    "description": ""

                }

            ],

            "publication_summary": {

                "journal_publications": 0,
                "conference_publications": 0,
                "book_publications": 0,
                "book_chapters": 0,
                "patents": 0

            }

        }

    ##########################################################################
    # SYSTEM PROMPT
    ##########################################################################

    def system_prompt(self) -> str:

        return (
            "You are an expert faculty resume parser. "
            "Extract information accurately from faculty resumes. "
            "Return ONLY valid JSON matching the provided schema. "
            "Do not return markdown. "
            "Do not explain anything. "
            "Do not hallucinate missing information."
        )

    ##########################################################################
    # EXTRACTION RULES
    ##########################################################################

    def extraction_rules(self) -> str:

        return """
RULES

1. Return ONLY valid JSON.

2. Never explain your answer.

3. Never generate Markdown.

4. Never wrap JSON inside ```.

5. Never hallucinate information.

6. Every schema key must exist.

7. Missing string -> ""

8. Missing list -> []

9. Missing count -> 0

10. Never return null.

11. Preserve education order.

12. Preserve experience order.

13. Extract every education entry.

14. Extract every experience entry.

15. Keep experience description concise.
Maximum 1-2 sentences.

16. DO NOT extract individual publication details.

17. Count only:
    - Journal publications
    - Conference publications
    - Books
    - Book Chapters
    - Patents

18. Do NOT include:
    - publication title
    - authors
    - journal name
    - conference name
    - DOI
    - publisher
    - ISBN

19. Return publication counts only.

20. If a publication category is absent,
return 0.

21. Return JSON only.
"""

    ##########################################################################
    # JSON SCHEMA
    ##########################################################################

    def json_schema(self) -> str:

        return json.dumps(
            self.schema,
            indent=4,
            ensure_ascii=False
        )

    ##########################################################################
    # BUILD CHAT MESSAGES
    ##########################################################################

    def build_messages(
        self,
        resume_text: str
    ) -> List[Dict[str, str]]:

        if not isinstance(resume_text, str):

            raise TypeError(
                "resume_text must be a string."
            )

        resume_text = resume_text.strip()

        if not resume_text:

            raise ValueError(
                "Resume text is empty."
            )

        return [

            {

                "role": "system",

                "content": self.system_prompt()

            },

            {

                "role": "user",

                "content": f"""
{self.extraction_rules()}

JSON SCHEMA

{self.json_schema()}

RESUME

{resume_text}

Return ONLY valid JSON.
""".strip()

            }

        ]