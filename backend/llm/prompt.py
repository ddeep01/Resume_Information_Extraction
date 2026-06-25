"""Faculty Resume Prompt Builder.

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

Flow:
    Resume.txt -> PromptBuilder -> Messages -> extractor.py -> Ollama
"""

from __future__ import annotations

import json
from typing import Dict, List


class PromptBuilder:
    """Production Prompt Builder.

    This class generates prompts for faculty resume extraction.
    """

    def __init__(self):
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
                "website": "",
                "orcid": "",
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
            "research_interests": [],
            "publications": [
                {
                    "title": "",
                    "authors": [],
                    "journal": "",
                    "conference": "",
                    "year": "",
                    "doi": "",
                    "publisher": ""
                }
            ],
            "projects": [
                {
                    "title": "",
                    "description": "",
                    "technologies": [],
                    "duration": ""
                }
            ],
            "patents": [],
            "books": [],
            "book_chapters": [],
            "conferences": [],
            "awards": [],
            "certifications": [
                {
                    "name": "",
                    "organization": "",
                    "year": ""
                }
            ],
            "skills": [],
            "languages": [],
            "references": []
        }

    def system_prompt(self) -> str:
        return (
            "You are an expert faculty resume parser. "
            "Extract information accurately from resumes. "
            "Return ONLY valid JSON that exactly matches the provided schema. "
            "Do not add explanations, markdown, or extra text."
        )

    def extraction_rules(self) -> str:
        """User instructions. Kept concise to reduce prompt tokens."""

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

9. Never return null.

11. Preserve original order.

12. Preserve education order.

13. Preserve experience order.

14. Return unique skills only.

15. Calculate total_experience using all professional
experience entries.

16. If candidate is currently employed,
calculate experience until today.

17. Do not double count overlapping jobs.

18. If a section contains multiple entries,
return each entry as a separate object.
"""

    def json_schema(self) -> str:
        """Returns formatted JSON schema."""

        return json.dumps(self.schema, indent=4, ensure_ascii=False)

    def build_messages(self, resume_text: str) -> List[Dict[str, str]]:
        """Build chat messages for Ollama."""

        if not isinstance(resume_text, str):
            raise TypeError("resume_text must be a string.")

        resume_text = resume_text.strip()

        if not resume_text:
            raise ValueError("Resume text is empty.")

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
