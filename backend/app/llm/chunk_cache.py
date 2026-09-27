import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from backend.app.config import settings

logger = logging.getLogger("ChunkCache")

class ChunkCache:
    """
    Deterministic cache for leaf extraction chunks.
    """
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or (settings.CACHE_DIR / "chunks")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = settings.CHUNK_CACHE_ENABLED

    def _compute_key(self, doc_hash: str, chunk_text: str, model_name: str, prompt_version: str = "v1") -> str:
        data = f"{doc_hash}:{chunk_text}:{model_name}:{prompt_version}".encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def get(self, doc_hash: str, chunk_text: str, model_name: str, prompt_version: str = "v1") -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        key = self._compute_key(doc_hash, chunk_text, model_name, prompt_version)
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.debug(f"Chunk cache HIT for key {key[:10]}")
                    return data
            except Exception as e:
                logger.warning(f"Failed to read chunk cache file {cache_file}: {e}")
        return None

    def set(self, doc_hash: str, chunk_text: str, model_name: str, result: Dict[str, Any], prompt_version: str = "v1"):
        if not self.enabled:
            return
        key = self._compute_key(doc_hash, chunk_text, model_name, prompt_version)
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            logger.debug(f"Chunk cache STORED for key {key[:10]}")
        except Exception as e:
            logger.warning(f"Failed to write chunk cache file {cache_file}: {e}")
