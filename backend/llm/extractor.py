"""
==============================================================================
LLM Resume Extractor
==============================================================================

Stage 4 : LLM Information Extraction

Responsibilities
----------------
✓ Read cleaned resume text
✓ Build prompt
✓ Send request to Ollama
✓ Receive response
✓ Validate response
✓ Save JSON
✓ Batch processing
✓ Logging
✓ Statistics

Flow

Cleaned Resume
      │
      ▼
Prompt Builder
      │
      ▼
Ollama (Qwen3)
      │
      ▼
Validator
      │
      ▼
JSON Output
==============================================================================

"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import ollama
from validator import JSONValidator
from prompt import PromptBuilder


##############################################################################
# PROJECT PATHS
##############################################################################

ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = ROOT / "data" / "cleaned_text"

OUTPUT_DIR = ROOT / "data" / "extracted_json"

LOG_DIR = ROOT / "logs"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True
)

##############################################################################
# CONFIGURATION
##############################################################################
# MODEL_NAME = "qwen2.5:7b"
# MODEL_NAME = "mistral:7b"
MODEL_NAME = "llama3.1:8b"


REQUEST_TIMEOUT = 180

MAX_RETRIES = 3

RETRY_DELAY = 3

NUM_PREDICT = 8192

TOP_P = 0.8

TEMPERATURE = 0.0

##############################################################################
# LOGGER
##############################################################################

logging.basicConfig(

    level=logging.INFO,

    format="%(asctime)s | %(levelname)s | %(message)s",

    handlers=[

        logging.FileHandler(
            LOG_DIR / "llm_extraction.log",
            encoding="utf-8"
        ),

        logging.StreamHandler()

    ]

)

logger = logging.getLogger("LLMExtractor")

class LLMExtractor:

    """
    Production LLM Resume Extractor.
    """

    def __init__(
        self,
        model: str = MODEL_NAME
    ):

        self.model = model

        self.prompt_builder = PromptBuilder()
        self.validator = JSONValidator()


        logger.info("=" * 70)

        logger.info(
            "LLM Extractor Initialized"
        )

        logger.info(
            f"Model : {self.model}"
        )

        logger.info("=" * 70)


    ##############################################################################
# MODEL CHECK
##############################################################################

    def check_model(self) -> bool:
        """
        Verify that the configured Ollama model exists.
        """

        try:

            models = ollama.list()

            available = []

            for model in models.get("models", []):

                name = model.get("model") or model.get("name")

                if name:
                    available.append(name)

            if self.model not in available:

                logger.error(
                    f"Model '{self.model}' not found."
                )

                logger.error(
                    f"Available Models : {available}"
                )

                return False

            logger.info(
                f"Using Model : {self.model}"
            )

            return True

        except Exception as exc:

            logger.exception(exc)

            return False


##############################################################################
# CALL LLM
##############################################################################

    def call_llm(
        self,
        resume_text: str
    ) -> Optional[str]:
        """
        Send prompt to Ollama.

        Returns
        -------
        Raw JSON string returned by Qwen.
        """

        messages = self.prompt_builder.build_messages(
            resume_text
        )

        for attempt in range(
            1,
            MAX_RETRIES + 1
        ):

            try:

                logger.info(
                    f"LLM Request ({attempt}/{MAX_RETRIES})"
                )


                response = ollama.chat(

                    model=self.model,

                    messages=messages,
                    format="json",

                    options={

                        "temperature": TEMPERATURE,

                        "top_p": TOP_P,

                        "num_predict": NUM_PREDICT

                    }

                )

                logger.info(response)
                message = response.get(
                    "message",
                    {}
                )

                content = message.get(
                    "content",
                    ""
                )

                if not content.strip():

                    raise ValueError(
                        "Empty response received."
                    )

                return content.strip()

            except Exception as exc:

                logger.warning(
                    f"Attempt {attempt} Failed"
                )

                logger.exception(exc)

                if attempt < MAX_RETRIES:

                    logger.info(
                        f"Retrying in {RETRY_DELAY} sec..."
                    )

                    time.sleep(
                        RETRY_DELAY
                    )

        logger.error(
            "Maximum retry limit reached."
        )

        return None
    

    def extract_resume(
        self,
        resume_file: Path
    ) -> bool:
        """
        Extract information from one cleaned resume.
    
        Returns
        -------
        True  -> Success
        False -> Failed
        """
    
        logger.info("-" * 70)
        logger.info(f"Processing : {resume_file.name}")
    
        try:
        
            resume_text = resume_file.read_text(
                encoding="utf-8"
            ).strip()
    
            if not resume_text:
            
                logger.warning(
                    f"{resume_file.name} is empty."
                )
    
                return False
    
            # Retry extraction if JSON validation fails
            for attempt in range(1, MAX_RETRIES + 1):
            
                logger.info(
                    f"Extraction Attempt ({attempt}/{MAX_RETRIES})"
                )
    
                llm_response = self.call_llm(resume_text)
    
                if llm_response is None:
                
                    continue
                
                try:
                
                    validated_json = self.validator.validate(
                        llm_response,
                        resume_file.name
                    )
    
                    self.save_json(
                        validated_json,
                        OUTPUT_DIR / f"{resume_file.stem}.json"
                    )
    
                    logger.info(
                        f"Finished : {resume_file.name}"
                    )
    
                    return True
    
                except Exception as e:
                
                    logger.warning(
                        f"Validation Failed ({attempt}/{MAX_RETRIES})"
                    )
    
                    logger.exception(e)
    
                    if attempt < MAX_RETRIES:
                    
                        logger.info(
                            "Retrying extraction..."
                        )
    
                        time.sleep(RETRY_DELAY)
    
            logger.error(
                f"Failed after {MAX_RETRIES} attempts : {resume_file.name}"
            )
    
            return False
    
        except Exception as exc:
        
            logger.exception(exc)
    
            return False

    def save_json(
        self,
        data: Dict,
        output_file: Path
    ) -> None:
        """
        Save extracted JSON.
        """

        output_file.write_text(

            json.dumps(

                data,

                indent=4,

                ensure_ascii=False

            ),

            encoding="utf-8"

        )

        logger.info(
            f"Saved : {output_file.name}"
        )


    def process_directory(self) -> None:
        """
        Process all cleaned resumes.
        """

        resume_files = sorted(

            INPUT_DIR.glob("*.txt")

        )

        logger.info("=" * 70)

        if not resume_files:

            logger.warning(

                "No resumes found."

            )

            return

        if not self.check_model():

            return

        for resume in resume_files:

            self.extract_resume(

                resume

            )

        logger.info("=" * 70)

        logger.info("EXTRACTION FINISHED")

        logger.info("=" * 70)



def main():

    extractor = LLMExtractor()

    extractor.process_directory()


if __name__ == "__main__":

    main()