import pytest

from app.domain.case_rules import derive_jurisdiction

def test_derive_jurisdiction_returns_code():
    result = derive_jurisdiction("PAT-CN-001")
    assert result == "CN"

def test_derive_jurisdiction_rejects_invalid_format():
    with pytest.raises(ValueError):
        derive_jurisdiction("PATCN001")
