def validate_internal_reference_format(internal_reference: str) -> None:
    parts = internal_reference.split("-")
    if not (len(parts) == 3 and parts[0] == "PAT" and len(parts[1]) == 2 and parts[1].isalpha() and parts[1].isupper() and parts[2].isdigit()):
        raise ValueError("Invalid internal reference format")

def derive_jurisdiction(internal_reference: str) -> str:
    validate_internal_reference_format(internal_reference)
    parts = internal_reference.split("-")
    return parts[1]
