"""
Heuristics for auto-populating LocationNote fields.

Each heuristic is a function that takes an unsaved LocationNote instance
and mutates it in place. Heuristics are applied in order and should be idempotent.
"""
import re
from typing import Callable, List

from tt.apps.common.utils import get_url_top_level_domain

from .models import LocationNote


# URL pattern for extraction (matches URLs at end of text)
TRAILING_URL_PATTERN = re.compile(
    r'(https?://[^\s]+)\s*$',
    re.IGNORECASE
)


def heuristic_extract_trailing_url( note: LocationNote ) -> None:
    """
    Extract URL from end of note text to populate source_url and source_label.

    Only applies if source_url is empty.
    Sets source_label from TLD if source_label is also empty.
    """
    if note.source_url:
        return

    text = ( note.text or '' ).strip()
    match = TRAILING_URL_PATTERN.search( text )

    if match:
        url = match.group( 1 )
        note.source_url = url

        if not note.source_label:
            tld = get_url_top_level_domain( url )
            if tld:
                note.source_label = tld


def heuristic_source_label_from_url( note: LocationNote ) -> None:
    """
    Derive source_label from source_url TLD when label is missing.

    Only applies if source_url exists but source_label is empty.
    """
    if note.source_label:
        return

    if not note.source_url:
        return

    tld = get_url_top_level_domain( note.source_url )
    if tld:
        note.source_label = tld


# Ordered list of heuristics to apply
NOTE_HEURISTICS: List[Callable[[LocationNote], None]] = [
    heuristic_extract_trailing_url,
    heuristic_source_label_from_url,
]


def apply_note_heuristics( note: LocationNote ) -> None:
    """
    Apply all note heuristics in order.

    Mutates the note in place.

    Args:
        note: Unsaved LocationNote instance to process
    """
    for heuristic in NOTE_HEURISTICS:
        heuristic( note )
