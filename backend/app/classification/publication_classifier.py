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
from backend.app.llm.prompts import PUBLICATION_CLASSIFIER_PROMPT, BATCH_PUBLICATION_CLASSIFIER_PROMPT

logger = logging.getLogger("PublicationClassifier")

class PublicationClassifier:
    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_file = cache_file or (settings.CACHE_DIR / "publication_venues.json")
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
                logger.warning(f"Failed to read publication venue cache file: {e}")
        return {}

    def _save_file_cache(self):
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save publication venue cache file: {e}")

    def _get_db_cache(self, venue: str) -> Optional[Dict[str, Any]]:
        try:
            conn = get_db_connection(settings.DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT venue_name, tier, score, reason FROM publication_venue_cache WHERE LOWER(venue_name)=?", (venue.lower(),))
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    "venue_name": row["venue_name"],
                    "tier": row["tier"],
                    "score": row["score"],
                    "reason": row["reason"]
                }
        except Exception as e:
            logger.warning(f"DB venue cache read error: {e}")
        return None

    def _save_db_cache(self, venue: str, tier: str, score: float, reason: str):
        try:
            conn = get_db_connection(settings.DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO publication_venue_cache (venue_name, tier, score, reason, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """, (venue, tier, score, reason, datetime.now().isoformat()))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"DB venue cache save error: {e}")

    def classify(self, venue_name: Optional[str]) -> Dict[str, Any]:
        if not venue_name or not isinstance(venue_name, str) or not venue_name.strip():
            return {
                "venue_name": "Unknown",
                "tier": "Tier 3",
                "score": settings.TIER_3_SCORE,
                "reason": "Missing or invalid venue name"
            }

        name_clean = venue_name.strip()
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
        prompt = PUBLICATION_CLASSIFIER_PROMPT.format(venue_name=name_clean)

        def _call_classifier() -> Dict[str, Any]:
            raw = self.provider.generate(prompt)
            data = self.json_validator.parse_json(raw)
            if isinstance(data, dict):
                tier = data.get("tier", "Tier 3")
                reason = data.get("reason", "LLM Venue Tiering")
                score = settings.TIER_1_SCORE if tier == "Tier 1" else (settings.TIER_2_SCORE if tier == "Tier 2" else settings.TIER_3_SCORE)
                return {
                    "venue_name": name_clean,
                    "tier": tier,
                    "score": score,
                    "reason": reason
                }
            raise ValueError("LLM response is not a valid JSON object.")

        try:
            res = self.retry_handler.execute_with_retry(_call_classifier)
        except Exception as e:
            logger.warning(f"Publication classifier failed for '{name_clean}': {e}. Defaulting safely to Tier 3.")
            res = {
                "venue_name": name_clean,
                "tier": "Tier 3",
                "score": settings.TIER_3_SCORE,
                "reason": "Defaulted due to classification parsing error"
            }

        # Save to caches
        self.cache[key] = res
        self._save_file_cache()
        self._save_db_cache(name_clean, res["tier"], res["score"], res["reason"])

        return res

    def classify_batch(self, venue_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Classify multiple publication venues in a single request where possible.
        """
        results = {}
        uncached = []

        # Check caches first
        for venue in venue_names:
            if not venue or not isinstance(venue, str) or not venue.strip():
                results[venue] = {
                    "venue_name": "Unknown",
                    "tier": "Tier 3",
                    "score": settings.TIER_3_SCORE,
                    "reason": "Missing venue name"
                }
                continue

            v_clean = venue.strip()
            key = v_clean.lower()
            if key in self.cache:
                results[v_clean] = self.cache[key]
            else:
                db_res = self._get_db_cache(v_clean)
                if db_res:
                    self.cache[key] = db_res
                    results[v_clean] = db_res
                else:
                    uncached.append(v_clean)

        if not uncached:
            return results

        # Process uncached venues in batch
        logger.info(f"Classifying {len(uncached)} publication venues in batch...")
        prompt = BATCH_PUBLICATION_CLASSIFIER_PROMPT.format(venues_json=json.dumps(uncached))

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
                v_name = item.get("venue_name")
                tier = item.get("tier", "Tier 3")
                score = settings.TIER_1_SCORE if tier == "Tier 1" else (settings.TIER_2_SCORE if tier == "Tier 2" else settings.TIER_3_SCORE)
                reason = item.get("reason", "Batch LLM classification")
                
                res_obj = {
                    "venue_name": v_name,
                    "tier": tier,
                    "score": score,
                    "reason": reason
                }
                if v_name:
                    key = v_name.lower()
                    self.cache[key] = res_obj
                    self._save_db_cache(v_name, tier, score, reason)
                    results[v_name] = res_obj
            self._save_file_cache()
        except Exception as e:
            logger.warning(f"Batch venue classification failed ({e}). Falling back to individual venue processing.")

        # Fallback for any uncached venues not resolved by batch
        for v_clean in uncached:
            if v_clean not in results:
                results[v_clean] = self.classify(v_clean)

        return results
