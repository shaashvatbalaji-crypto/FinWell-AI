
import re


# Extend these labels when additional statement formats are supported.
REFERENCE_LABELS = (
    "REFERENCE",
    "REF",
    "UTR",
    "RRN",
    "TXN ID",
    "TRANSACTION ID",
    "TRANSACTION REF",
    "UPI REF",
    "BANK REF",
)


def normalize_reference(reference):
    """Normalize a reference without changing its underlying identity."""
    if reference is None:
        return None

    value = re.sub(r"[^A-Z0-9]", "", str(reference).upper())

    return value or None


def extract_reference(description, custom_labels=None):
    """
    Extract the first explicitly labelled transaction reference.

    Returns a normalized reference or None.
    """

    if not description:
        return None

    text = " ".join(str(description).upper().split())

    labels = list(REFERENCE_LABELS)

    if custom_labels:
        labels.extend(custom_labels)

    # Prefer longer labels to avoid partial matches.
    labels = sorted(set(labels), key=len, reverse=True)

    escaped_labels = "|".join(
        re.escape(label) for label in labels
    )

    pattern = (
        rf"\b(?:{escaped_labels})\b"
        rf"\s*[:#=-]?\s*"
        rf"([A-Z0-9][A-Z0-9/-]*)"
    )

    match = re.search(pattern, text)

    if not match:
        return None

    return normalize_reference(match.group(1))


def references_conflict(reference1, reference2):
    """
    Return True only when both references exist and differ.
    Missing references are treated as unknown.
    """

    ref1 = normalize_reference(reference1)
    ref2 = normalize_reference(reference2)

    return (
        ref1 is not None
        and ref2 is not None
        and ref1 != ref2
    )
