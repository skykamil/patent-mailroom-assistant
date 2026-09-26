from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

UPLOAD_DIR = Path("data/uploads")

@dataclass
class StoredFile:
    storage_path: str
    file_size: int
    sha256: str

def save_file(content: bytes, original_filename: str) -> StoredFile:
    file_hash = sha256(content).hexdigest()
    file_size = len(content)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(original_filename).suffix
    stored_filename = uuid4().hex + suffix
    storage_path = UPLOAD_DIR / stored_filename
    storage_path.write_bytes(content)
    return StoredFile(str(storage_path), file_size, file_hash)
