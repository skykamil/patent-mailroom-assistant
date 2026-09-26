from hashlib import sha256
from pathlib import Path

import pytest

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


def test_save_file_removes_partial_when_write_fails(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(local_storage, "UPLOAD_DIR", tmp_path)
    original_write_bytes = Path.write_bytes

    def partial_write_then_fail(path: Path, data: bytes):
        original_write_bytes(path, data[:5])
        raise RuntimeError("synthetic write failure")

    monkeypatch.setattr(Path, "write_bytes", partial_write_then_fail)
    with pytest.raises(RuntimeError, match="synthetic write failure"):
        local_storage.save_file(
            content=b"synthetic patent document",
            original_filename="Office_Action.pdf",
        )
    assert list(tmp_path.iterdir()) == []
