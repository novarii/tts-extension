from __future__ import annotations

import re
from typing import Dict


def apply_corrections(text: str, dictionary: Dict[str, str]) -> str:
    """Replace misheard terms with their correct forms using the dictionary.

    Matching is case-insensitive. The replacement preserves the casing style
    of the original match when possible (all-upper, title-case), otherwise
    uses the dictionary value as-is.
    """
    if not text or not dictionary:
        return text

    # Normalize keys to lowercase so case-insensitive lookup works.
    lower_dict = {k.lower(): v for k, v in dictionary.items()}

    # Build a single pattern with all keys, longest-first to avoid partial matches.
    sorted_keys = sorted(lower_dict, key=len, reverse=True)
    pattern = re.compile(
        "|".join(re.escape(k) for k in sorted_keys),
        re.IGNORECASE,
    )

    def _replace(match: re.Match[str]) -> str:
        matched = match.group()
        replacement = lower_dict[matched.lower()]
        # Preserve obvious casing styles from the original text.
        if matched.isupper():
            return replacement.upper()
        if matched.istitle():
            return replacement.title()
        return replacement

    return pattern.sub(_replace, text)
