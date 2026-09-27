import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from backend.app.config import settings
from backend.app.models.database import get_db_connection
from backend.app.llm.extraction import get_llm_provider
from backend.app.llm.remote_provider import MockFallbackProvider
from backend.app.llm.prompts import PUBLICATION_CLASSIFIER_PROMPT

logger = logging.getLogger("PublicationClassifier")

class PublicationClassifier:
    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_file = cache_file or (settings.CACHE_DIR / "publication_venues.json")
        self.cache = self._load_file_cache()
        self.provider = get_llm_provider()
        self.fallback = MockFallbackProvider()

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

        # 3. Perform LLM classification
        prompt = PUBLICATION_CLASSIFIER_PROMPT.format(venue_name=name_clean)
        try:
            raw = self.provider.generate(prompt)
            clean_raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            clean_raw = re.sub(r"```\s*$", "", clean_raw, flags=re.MULTILINE).strip()
            data = json.loads(clean_raw)
            tier = data.get("tier", "Tier 3")
            score = settings.TIER_1_SCORE if tier == "Tier 1" else (settings.TIER_2_SCORE if tier == "Tier 2" else settings.TIER_3_SCORE)
            res = {
                "venue_name": name_clean,
                "tier": tier,
                "score": score,
                "reason": data.get("reason", "LLM Venue Tiering")
            }
        except Exception as e:
            logger.warning(f"LLM venue classification failed for '{name_clean}': {e}. Using fallback.")
            raw = self.fallback.generate(prompt)
            data = json.loads(re.sub(r"```(?:json)?", "", raw).strip())
            tier = data.get("tier", "Tier 3")
            score = settings.TIER_1_SCORE if tier == "Tier 1" else (settings.TIER_2_SCORE if tier == "Tier 2" else settings.TIER_3_SCORE)
            res = {
                "venue_name": name_clean,
                "tier": tier,
                "score": score,
                "reason": data.get("reason", "Heuristic Venue Classification")
            }

        # Save to caches
        self.cache[key] = res
        self._save_file_cache()
        self._save_db_cache(name_clean, res["tier"], res["score"], res["reason"])

        return res
