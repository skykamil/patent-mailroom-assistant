def derive_jurisdiction(internal_reference: str) -> str:
    parts = internal_reference.split("-")
    if not (len(parts) == 3 and parts[0] == "PAT" and len(parts[1]) == 2 and parts[1].isalpha() and parts[1].isupper() and parts[2].isdigit()):
        raise ValueError("Invalid internal reference format")
    return parts[1]
