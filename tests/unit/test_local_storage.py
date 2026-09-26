from hashlib import sha256
from pathlib import Path

from app.storage import local_storage

def test_save_file_writes_content_and_returns_metadata(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(local_storage, "UPLOAD_DIR", tmp_path)
    content = b"synthetic patent document"
    result = local_storage.save_file(
        content=content,
        original_filename="Office_Action.pdf"
    )
    assert result.file_size == len(content)
    saved_path = Path(result.storage_path)
    assert saved_path.exists()
    assert saved_path.read_bytes() == content
    assert result.sha256 == sha256(content).hexdigest()
    assert saved_path.suffix == ".pdf"

def test_delete_file_removes_saved_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(local_storage, "UPLOAD_DIR", tmp_path)
    content = b"synthetic patent document"
    result = local_storage.save_file(
        content=content,
        original_filename="Office_Action.pdf"
    )
    saved_path = Path(result.storage_path)
    assert saved_path.exists()
    local_storage.delete_file(result.storage_path)
    assert not saved_path.exists()