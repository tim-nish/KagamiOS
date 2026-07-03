import uuid


def mint_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"
