"""
==============================================================================
LLM Response Validator

Project:
    LLM Based Faculty Resume Information Extraction

Purpose
-------
Validate, repair and standardize JSON returned by the LLM.

Responsibilities
----------------
✓ Clean LLM response
✓ Remove markdown
✓ Remove extra text
✓ Parse JSON
✓ Validate schema
✓ Repair missing fields
✓ Remove unknown fields
✓ Save invalid responses

Author:
    Your Project
==============================================================================
"""

from __future__ import annotations

import copy
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict

from prompt import PromptBuilder


##############################################################################
# PROJECT PATHS
##############################################################################

ROOT = Path(__file__).resolve().parents[2]

INVALID_JSON_DIR = ROOT / "data" / "invalid_json"

INVALID_JSON_DIR.mkdir(
    parents=True,
    exist_ok=True
)

##############################################################################
# LOGGER
##############################################################################

logger = logging.getLogger("LLMExtractor")


##############################################################################
# VALIDATOR
##############################################################################

class JSONValidator:
    """
    Production JSON Validator.
    """

    def __init__(self):

        self.schema = copy.deepcopy(
            PromptBuilder().schema
        )

    ##########################################################################
    # CLEAN RESPONSE
    ##########################################################################

    def clean_response(
        self,
        response: str
    ) -> str:
        """
        Remove markdown and unwanted text
        from the LLM response.
        """

        if not isinstance(response, str):

            raise TypeError(
                "LLM response must be a string."
            )

        text = response.strip()

        ##########################################################
        # Remove Markdown Code Blocks
        ##########################################################

        text = re.sub(
            r"^```json",
            "",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"^```",
            "",
            text
        )

        text = re.sub(
            r"```$",
            "",
            text
        )

        ##########################################################
        # Remove Common Prefixes
        ##########################################################

        prefixes = [

            "Here is the JSON:",

            "Here is your JSON:",

            "Here is the extracted JSON:",

            "The extracted information is:",

            "Output:",

            "Answer:"

        ]

        for prefix in prefixes:

            if text.lower().startswith(
                prefix.lower()
            ):

                text = text[
                    len(prefix):
                ].strip()

        ##########################################################
        # Keep only JSON object
        ##########################################################

        first = text.find("{")

        last = text.rfind("}")

        if first != -1 and last != -1:

            text = text[
                first:last + 1
            ]

        return text.strip()

    ##########################################################################
    # PARSE JSON
    ##########################################################################

    def parse_json(
        self,
        response: str
    ) -> Dict[str, Any]:
        """
        Convert cleaned response
        into Python dictionary.
        """

        cleaned = self.clean_response(
            response
        )

        return json.loads(cleaned)
    
        ##########################################################################
    # RECURSIVE VALIDATION
    ##########################################################################

    def _validate_value(
        self,
        value: Any,
        schema: Any
    ) -> Any:
        """
        Recursively validate value against schema.
        """

        ##############################################################
        # Dictionary
        ##############################################################

        if isinstance(schema, dict):

            if not isinstance(value, dict):

                value = {}

            validated = {}

            for key, schema_value in schema.items():

                if key in value:

                    validated[key] = self._validate_value(
                        value[key],
                        schema_value
                    )

                else:

                    validated[key] = copy.deepcopy(
                        schema_value
                    )

            return validated

        ##############################################################
        # List
        ##############################################################

        if isinstance(schema, list):

            if not isinstance(value, list):

                return []

            ##########################################################
            # Empty schema list
            ##########################################################

            if not schema:

                return value

            validated = []

            item_schema = schema[0]

            for item in value:

                validated.append(

                    self._validate_value(
                        item,
                        item_schema
                    )

                )

            return validated

        ##############################################################
        # Boolean
        ##############################################################

        if isinstance(schema, bool):

            return bool(value)

        ##############################################################
        # String
        ##############################################################

        if isinstance(schema, str):

            if value is None:

                return ""

            return str(value).strip()

        ##############################################################
        # Integer
        ##############################################################

        if isinstance(schema, int):

            try:

                return int(value)

            except Exception:

                return schema

        ##############################################################
        # Float
        ##############################################################

        if isinstance(schema, float):

            try:

                return float(value)

            except Exception:

                return schema

        return value


    ##########################################################################
    # VALIDATE SCHEMA
    ##########################################################################

    def validate_schema(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate dictionary using master schema.
        """

        return self._validate_value(
            data,
            self.schema
        )


    ##########################################################################
    # REMOVE UNKNOWN KEYS
    ##########################################################################

    def remove_unknown_keys(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Remove keys that are not present
        in the schema.
        """

        if not isinstance(data, dict):

            return {}

        cleaned = {}

        for key, schema_value in schema.items():

            if key not in data:

                continue

            value = data[key]

            ##########################################################
            # Nested Dictionary
            ##########################################################

            if isinstance(schema_value, dict):

                cleaned[key] = self.remove_unknown_keys(

                    value,

                    schema_value

                )

            ##########################################################
            # List of Dictionaries
            ##########################################################

            elif (

                isinstance(schema_value, list)

                and schema_value

                and isinstance(schema_value[0], dict)

                and isinstance(value, list)

            ):

                cleaned[key] = [

                    self.remove_unknown_keys(

                        item,

                        schema_value[0]

                    )

                    for item in value

                    if isinstance(item, dict)

                ]

            ##########################################################
            # Primitive
            ##########################################################

            else:

                cleaned[key] = value

        return cleaned
    
        ##########################################################################
    # SAVE INVALID RESPONSE
    ##########################################################################

    def save_invalid_response(
        self,
        response: str,
        file_name: str = "unknown"
    ) -> None:
        """
        Save invalid LLM response for debugging.
        """

        try:

            output_file = (
                INVALID_JSON_DIR /
                f"{Path(file_name).stem}_raw.txt"
            )

            output_file.write_text(
                response,
                encoding="utf-8"
            )

            logger.warning(
                f"Invalid response saved : {output_file.name}"
            )

        except Exception as exc:

            logger.exception(exc)

    ##########################################################################
    # VALIDATE
    ##########################################################################

    def validate(
        self,
        response: str,
        file_name: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Complete validation pipeline.

        Flow
        ----
        Raw Response
            ↓
        Clean Response
            ↓
        Parse JSON
            ↓
        Remove Unknown Keys
            ↓
        Validate Schema
            ↓
        Return Dictionary
        """

        try:

            ##############################################################
            # Parse JSON
            ##############################################################

            parsed = self.parse_json(
                response
            )

            ##############################################################
            # Remove Unknown Keys
            ##############################################################

            cleaned = self.remove_unknown_keys(
                parsed,
                self.schema
            )

            ##############################################################
            # Validate Against Schema
            ##############################################################

            validated = self.validate_schema(
                cleaned
            )

            logger.info(
                "JSON validation successful."
            )

            return validated

        except Exception as exc:

            logger.exception(exc)

            self.save_invalid_response(
                response,
                file_name
            )

            raise ValueError(
                "Invalid JSON returned by LLM."
            ) from exc