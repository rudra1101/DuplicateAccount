from rapidfuzz import fuzz


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0

    return fuzz.ratio(a.lower(), b.lower())