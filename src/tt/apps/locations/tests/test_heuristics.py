"""Tests for LocationNote heuristics."""
from django.test import TestCase

from tt.apps.locations.heuristics import (
    apply_note_heuristics,
    heuristic_extract_trailing_url,
    heuristic_source_label_from_url,
)
from tt.apps.locations.models import LocationNote


class ExtractTrailingUrlHeuristicTestCase( TestCase ):
    """Tests for heuristic_extract_trailing_url."""

    def test_extracts_url_at_end( self ):
        """URL at end of text is extracted as source_url with TLD as source_label."""
        note = LocationNote(
            text = 'Great restaurant https://yelp.com/biz/123',
            source_label = '',
            source_url = '',
        )
        heuristic_extract_trailing_url( note )
        self.assertEqual( note.source_url, 'https://yelp.com/biz/123' )
        self.assertEqual( note.source_label, 'yelp.com' )

    def test_extracts_url_with_trailing_whitespace( self ):
        """URL followed by whitespace is still extracted."""
        note = LocationNote(
            text = 'Check this out https://example.com/page   ',
            source_label = '',
            source_url = '',
        )
        heuristic_extract_trailing_url( note )
        self.assertEqual( note.source_url, 'https://example.com/page' )
        self.assertEqual( note.source_label, 'example.com' )

    def test_skips_if_source_url_exists( self ):
        """Existing source_url is preserved."""
        note = LocationNote(
            text = 'Note https://other.com',
            source_label = '',
            source_url = 'https://existing.com',
        )
        heuristic_extract_trailing_url( note )
        self.assertEqual( note.source_url, 'https://existing.com' )
        self.assertEqual( note.source_label, '' )

    def test_no_url_in_text( self ):
        """Text without URL leaves fields empty."""
        note = LocationNote(
            text = 'Just plain text without any URL',
            source_label = '',
            source_url = '',
        )
        heuristic_extract_trailing_url( note )
        self.assertEqual( note.source_url, '' )
        self.assertEqual( note.source_label, '' )

    def test_url_not_at_end( self ):
        """URL in middle of text is not extracted."""
        note = LocationNote(
            text = 'Check https://example.com for more details here',
            source_label = '',
            source_url = '',
        )
        heuristic_extract_trailing_url( note )
        self.assertEqual( note.source_url, '' )
        self.assertEqual( note.source_label, '' )

    def test_preserves_existing_source_label( self ):
        """Existing source_label is preserved when extracting URL."""
        note = LocationNote(
            text = 'Note https://example.com',
            source_label = 'Custom Label',
            source_url = '',
        )
        heuristic_extract_trailing_url( note )
        self.assertEqual( note.source_url, 'https://example.com' )
        self.assertEqual( note.source_label, 'Custom Label' )

    def test_http_url( self ):
        """HTTP URLs (not just HTTPS) are extracted."""
        note = LocationNote(
            text = 'Old site http://legacy.example.com/page',
            source_label = '',
            source_url = '',
        )
        heuristic_extract_trailing_url( note )
        self.assertEqual( note.source_url, 'http://legacy.example.com/page' )
        # TLD extraction returns just the domain (example.com), not subdomain
        self.assertEqual( note.source_label, 'example.com' )


class SourceLabelFromUrlHeuristicTestCase( TestCase ):
    """Tests for heuristic_source_label_from_url."""

    def test_derives_label_from_url( self ):
        """TLD is derived from source_url when source_label is empty."""
        note = LocationNote(
            text = 'Some note',
            source_label = '',
            source_url = 'https://tripadvisor.com/page',
        )
        heuristic_source_label_from_url( note )
        self.assertEqual( note.source_label, 'tripadvisor.com' )

    def test_skips_if_label_exists( self ):
        """Existing source_label is preserved."""
        note = LocationNote(
            text = 'Note',
            source_label = 'Custom Label',
            source_url = 'https://example.com',
        )
        heuristic_source_label_from_url( note )
        self.assertEqual( note.source_label, 'Custom Label' )

    def test_no_url( self ):
        """No source_url means no change."""
        note = LocationNote(
            text = 'Note',
            source_label = '',
            source_url = '',
        )
        heuristic_source_label_from_url( note )
        self.assertEqual( note.source_label, '' )


class ApplyNoteHeuristicsTestCase( TestCase ):
    """Tests for apply_note_heuristics orchestration."""

    def test_full_pipeline_extracts_and_labels( self ):
        """Full pipeline extracts URL and derives label."""
        note = LocationNote(
            text = 'Great place https://maps.google.com/place/123',
            source_label = '',
            source_url = '',
        )
        apply_note_heuristics( note )
        self.assertEqual( note.source_url, 'https://maps.google.com/place/123' )
        # TLD extraction returns just the domain (google.com), not subdomain
        self.assertEqual( note.source_label, 'google.com' )

    def test_url_provided_label_derived( self ):
        """When source_url is provided but not label, TLD is derived."""
        note = LocationNote(
            text = 'Some note text',
            source_label = '',
            source_url = 'https://tripadvisor.com/restaurant/123',
        )
        apply_note_heuristics( note )
        self.assertEqual( note.source_url, 'https://tripadvisor.com/restaurant/123' )
        self.assertEqual( note.source_label, 'tripadvisor.com' )

    def test_preserves_existing_values( self ):
        """Existing source_label and source_url are preserved."""
        note = LocationNote(
            text = 'Note with URL at end https://other.com',
            source_label = 'My Source',
            source_url = 'https://my.com',
        )
        apply_note_heuristics( note )
        self.assertEqual( note.source_label, 'My Source' )
        self.assertEqual( note.source_url, 'https://my.com' )

    def test_no_url_anywhere( self ):
        """Plain text without URL leaves fields unchanged."""
        note = LocationNote(
            text = 'Just a plain note without any links',
            source_label = '',
            source_url = '',
        )
        apply_note_heuristics( note )
        self.assertEqual( note.source_url, '' )
        self.assertEqual( note.source_label, '' )
