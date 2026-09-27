import zipfile
import shutil
import logging
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger("ZipService")

class ZipService:
    @staticmethod
    def extract_zip_safely(zip_path: Path, target_dir: Path) -> List[Tuple[str, Path]]:
        """
        Safely extracts ZIP archive to target_dir and discovers PDF/DOCX files.
        Returns: List of tuples (candidate_id, file_path)
        """
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.infolist():
                # Protect against ZipSlip path traversal
                resolved_target = (target_dir / member.filename).resolve()
                if not str(resolved_target).startswith(str(target_dir.resolve())):
                    logger.warning(f"Unsafe file path detected in zip: {member.filename}")
                    continue
                zip_ref.extract(member, target_dir)

        # Discover PDF, DOCX, and TXT files recursively
        discovered_files = []
        for file_path in target_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in [".pdf", ".docx", ".txt"]:
                if not file_path.name.startswith("._") and "__MACOSX" not in str(file_path):
                    discovered_files.append(file_path)

        # Sort files to ensure deterministic candidate ID assignment
        discovered_files.sort(key=lambda p: p.name.lower())

        candidates_with_id = []
        for index, f_path in enumerate(discovered_files, start=1):
            cand_id = f"CAND-{index:04d}"
            candidates_with_id.append((cand_id, f_path))

        return candidates_with_id
