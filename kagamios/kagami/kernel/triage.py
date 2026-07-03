COMPUTABLE = "computable"
HUMAN_ONLY = "human-only"
DEFERRABLE = "deferrable"

TRIAGE_CLASSES = (COMPUTABLE, HUMAN_ONLY, DEFERRABLE)


class TriageError(Exception):
    pass


def triage_unknown(unknown_class_hint: str, blocking: bool) -> str:
    """FR-17: three-way unknown triage.

    Only a human-only unknown that is also blocking becomes a candidate
    question; a human-only unknown that is not blocking is deferred (an AI
    default is applied and recorded) rather than asked.
    """
    if unknown_class_hint == COMPUTABLE:
        return COMPUTABLE
    if unknown_class_hint == HUMAN_ONLY:
        return HUMAN_ONLY if blocking else DEFERRABLE
    if unknown_class_hint == DEFERRABLE:
        return DEFERRABLE
    raise TriageError(f"unknown 'unknown_class_hint' value: {unknown_class_hint!r}")
