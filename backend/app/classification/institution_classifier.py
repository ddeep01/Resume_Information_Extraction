import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.app.config import settings
from backend.app.models.database import get_db_connection
from backend.app.llm.extraction import get_llm_provider
from backend.app.llm.json_validator import JSONValidator
from backend.app.llm.retry_handler import RetryHandler
from backend.app.llm.prompts import INSTITUTION_CLASSIFIER_PROMPT, BATCH_INSTITUTION_CLASSIFIER_PROMPT

logger = logging.getLogger("InstitutionClassifier")

class InstitutionClassifier:
    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_file = cache_file or (settings.CACHE_DIR / "institutions.json")
        self.cache = self._load_file_cache()
        self.provider = get_llm_provider()
        self.json_validator = JSONValidator()
        self.retry_handler = RetryHandler()

    def _load_file_cache(self) -> Dict[str, Any]:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read institution cache file: {e}")
        return {}

    def _save_file_cache(self):
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save institution cache file: {e}")

    def _get_db_cache(self, name: str) -> Optional[Dict[str, Any]]:
        try:
            conn = get_db_connection(settings.DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT institution_name, tier, score, reason FROM institution_cache WHERE LOWER(institution_name)=?", (name.lower(),))
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    "institution": row["institution_name"],
                    "tier": row["tier"],
                    "score": row["score"],
                    "reason": row["reason"]
                }
        except Exception as e:
            logger.warning(f"DB cache read error: {e}")
        return None

    def _save_db_cache(self, name: str, tier: str, score: float, reason: str):
        try:
            conn = get_db_connection(settings.DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO institution_cache (institution_name, tier, score, reason, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """, (name, tier, score, reason, datetime.now().isoformat()))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"DB cache save error: {e}")

    def classify(self, institution_name: Optional[str]) -> Dict[str, Any]:
        if not institution_name or not isinstance(institution_name, str) or not institution_name.strip():
            return {
                "institution": "Unknown",
                "tier": "Tier 3",
                "score": settings.TIER_3_SCORE,
                "reason": "Missing or invalid institution name"
            }

        name_clean = institution_name.strip()
        key = name_clean.lower()

        # 1. Check in-memory file cache
        if key in self.cache:
            return self.cache[key]

        # 2. Check DB cache
        db_res = self._get_db_cache(name_clean)
        if db_res:
            self.cache[key] = db_res
            return db_res

        # 3. Perform LLM classification with JSON validation & retries
        prompt = INSTITUTION_CLASSIFIER_PROMPT.format(institution_name=name_clean)

        def _call_classifier() -> Dict[str, Any]:
            raw = self.provider.generate(prompt)
            data = self.json_validator.parse_json(raw)
            if isinstance(data, dict):
                tier = data.get("tier", "Tier 3")
                reason = data.get("reason", "LLM Tier Classification")
                score = settings.TIER_1_SCORE if tier == "Tier 1" else (settings.TIER_2_SCORE if tier == "Tier 2" else settings.TIER_3_SCORE)
                return {
                    "institution": name_clean,
                    "tier": tier,
                    "score": score,
                    "reason": reason
                }
            raise ValueError("LLM response is not a valid JSON object.")

        try:
            res = self.retry_handler.execute_with_retry(_call_classifier)
        except Exception as e:
            logger.warning(f"Institution classifier failed for '{name_clean}': {e}. Defaulting safely to Tier 3.")
            res = {
                "institution": name_clean,
                "tier": "Tier 3",
                "score": settings.TIER_3_SCORE,
                "reason": "Defaulted due to classification parsing error"
            }

        # Save to caches
        self.cache[key] = res
        self._save_file_cache()
        self._save_db_cache(name_clean, res["tier"], res["score"], res["reason"])

        return res

    def classify_batch(self, institution_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Classify multiple educational institutions in a single request where possible.
        """
        results = {}
        uncached = []

        for inst in institution_names:
            if not inst or not isinstance(inst, str) or not inst.strip():
                results[inst] = {
                    "institution": "Unknown",
                    "tier": "Tier 3",
                    "score": settings.TIER_3_SCORE,
                    "reason": "Missing institution name"
                }
                continue

            i_clean = inst.strip()
            key = i_clean.lower()
            if key in self.cache:
                results[i_clean] = self.cache[key]
            else:
                db_res = self._get_db_cache(i_clean)
                if db_res:
                    self.cache[key] = db_res
                    results[i_clean] = db_res
                else:
                    uncached.append(i_clean)

        if not uncached:
            return results

        logger.info(f"Classifying {len(uncached)} institutions in batch...")
        prompt = BATCH_INSTITUTION_CLASSIFIER_PROMPT.format(institutions_json=json.dumps(uncached))

        def _call_batch() -> List[Dict[str, Any]]:
            raw = self.provider.generate(prompt)
            data = self.json_validator.parse_json(raw)
            if isinstance(data, dict) and "classifications" in data:
                return data["classifications"]
            elif isinstance(data, list):
                return data
            raise ValueError("Batch classification format mismatch.")

        try:
            batch_res = self.retry_handler.execute_with_retry(_call_batch)
            for item in batch_res:
                inst_name = item.get("institution")
                tier = item.get("tier", "Tier 3")
                score = settings.TIER_1_SCORE if tier == "Tier 1" else (settings.TIER_2_SCORE if tier == "Tier 2" else settings.TIER_3_SCORE)
                reason = item.get("reason", "Batch LLM classification")
                
                res_obj = {
                    "institution": inst_name,
                    "tier": tier,
                    "score": score,
                    "reason": reason
                }
                if inst_name:
                    key = inst_name.lower()
                    self.cache[key] = res_obj
                    self._save_db_cache(inst_name, tier, score, reason)
                    results[inst_name] = res_obj
            self._save_file_cache()
        except Exception as e:
            logger.warning(f"Batch institution classification failed ({e}). Falling back to individual processing.")

        for i_clean in uncached:
            if i_clean not in results:
                results[i_clean] = self.classify(i_clean)

        return results
