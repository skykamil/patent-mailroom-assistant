import pytest

from app.domain.case_rules import validate_internal_reference_format


def test_validate_internal_reference_format_accepts_valid_reference():
    validate_internal_reference_format("PAT-CN-001")


@pytest.mark.parametrize(
    "internal_reference",
    [
        "PATCN001",
        "XYZ-CN-001",
        "PAT-cn-001",
        "PAT-CNN-001",
        "PAT-C1-001",
        "PAT-CN-ABC",
        "PAT-CN-001-X",
        "PAT-CN-",
    ],
)
def test_validate_internal_reference_format_rejects_invalid_reference(internal_reference):
    with pytest.raises(ValueError):
        validate_internal_reference_format(internal_reference)
