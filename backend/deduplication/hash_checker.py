import hashlib
import pandas as pd
from pathlib import Path


def calculate_file_hash(file_path):
    sha = hashlib.sha256()

    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)

    return sha.hexdigest()


def is_duplicate_file(file_path, hash_csv):
    file_hash = calculate_file_hash(file_path)

    if not Path(hash_csv).exists():
        return False, file_hash

    df = pd.read_csv(hash_csv)

    if file_hash in df["file_hash"].values:
        return True, file_hash

    return False, file_hash


def save_file_hash(filename, file_hash, hash_csv):
    row = pd.DataFrame(
        [{
            "filename": filename,
            "file_hash": file_hash
        }]
    )

    if Path(hash_csv).exists():
        row.to_csv(hash_csv, mode="a", header=False, index=False)
    else:
        row.to_csv(hash_csv, index=False)

if __name__ == "__main__":

    HASH_CSV = "data/file_hashes.csv"

    file_path = "data/raw_resumes/resume1.pdf"

    duplicate, file_hash = is_duplicate_file(
        file_path,
        HASH_CSV
    )

    if duplicate:
        print("Duplicate Found")
    else:
        print("New File")

        save_file_hash(
            Path(file_path).name,
            file_hash,
            HASH_CSV
        )