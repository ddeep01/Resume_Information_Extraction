import json
import re
import logging
from typing import Dict, Any, Optional, Union, List
from backend.app.llm.base import LLMProvider

logger = logging.getLogger("JSONValidator")

JSON_REPAIR_PROMPT = """You are a strict JSON repair utility.
The following text contains malformed JSON or syntax errors.
Repair ONLY the JSON syntax.
Do NOT change the information, values, names, classifications, or meaning.
Do NOT invent missing data.
Output ONLY valid JSON without markdown fences, preambles, or postscripts.

MALFORMED TEXT:
{malformed_text}
"""

class JSONValidator:
    """
    Utility for robust cleaning, syntax repair, schema validation, and LLM-assisted JSON recovery.
    """

    @staticmethod
    def clean_json_response(text: str) -> str:
        if not text:
            return ""
        text = text.strip()
        # 1. Remove ```json ... ``` codeblock wrappers
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE).strip()
        
        # 2. Strip accidental "json /" or "JSON:" prefixes
        text = re.sub(r"^(?:json|JSON)\s*/?\s*", "", text).strip()

        # 3. Extract JSON object {...} or array [...] if LLM included leading/trailing commentary
        json_obj_match = re.search(r"\{.*\}", text, re.DOTALL)
        json_arr_match = re.search(r"\[.*\]", text, re.DOTALL)
        
        if json_obj_match and json_arr_match:
            # Pick whichever starts earlier
            if json_obj_match.start() <= json_arr_match.start():
                text = json_obj_match.group(0)
            else:
                text = json_arr_match.group(0)
        elif json_obj_match:
            text = json_obj_match.group(0)
        elif json_arr_match:
            text = json_arr_match.group(0)

        # 4. Fix trailing commas before closing braces/brackets
        text = re.sub(r",\s*([\}\]])", r"\1", text)
        
        # 5. Fix Python literals if unquoted
        text = re.sub(r"\bTrue\b", "true", text)
        text = re.sub(r"\bFalse\b", "false", text)
        text = re.sub(r"\bNone\b", "null", text)

        return text.strip()

    @classmethod
    def parse_json(cls, raw_text: str) -> Union[Dict[str, Any], List[Any]]:
        cleaned = cls.clean_json_response(raw_text)
        if not cleaned:
            raise ValueError("Empty response text after cleaning.")
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.debug(f"Initial JSON parse failed: {e}. Attempting second-pass regex fixes...")
            
            # Second-pass fix: single-quoted keys, single-quoted values, single-line comments
            fixed = re.sub(r"//.*$", "", cleaned, flags=re.MULTILINE)
            # Replace single quotes around keys: 'key': -> "key":
            fixed = re.sub(r"(?<=[{,\s])'([a-zA-Z0-9_]+)'\s*:", r'"\1":', fixed)
            # Replace single quotes around simple string values: : 'val' -> : "val"
            fixed = re.sub(r":\s*'([^'\n]*)'", r': "\1"', fixed)
            # Fix trailing commas
            fixed = re.sub(r",\s*([\}\]])", r"\1", fixed)
            
            try:
                return json.loads(fixed)
            except json.JSONDecodeError as err:
                raise ValueError(f"Failed to parse JSON: {err}. Snippet: {cleaned[:200]!r}")

    @classmethod
    def repair_with_llm(cls, raw_text: str, provider: LLMProvider) -> Union[Dict[str, Any], List[Any]]:
        """
        Use LLM to repair syntax of malformed JSON without modifying data contents.
        """
        logger.warning("Attempting LLM-assisted JSON syntax repair...")
        prompt = JSON_REPAIR_PROMPT.replace("{malformed_text}", raw_text[:4000])
        repaired_raw = provider.generate(prompt)
        return cls.parse_json(repaired_raw)
