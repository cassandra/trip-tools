"""
Tests for JournalEntrySeederService.

Tests plain text to HTML conversion and NotebookEntry to JournalEntry seeding.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from tt.apps.notebook.models import NotebookEntry
from tt.apps.trips.models import Trip
from tt.apps.journal.models import Journal
from tt.apps.journal.services import JournalEntrySeederService

User = get_user_model()


class TextConversionTests(TestCase):
    """Test cases for convert_plain_text_to_html()."""

    def test_empty_string(self):
        """Test that empty string returns empty string."""
        result = JournalEntrySeederService.convert_plain_text_to_html('')
        self.assertEqual(result, '')

    def test_whitespace_only(self):
        """Test that whitespace-only string returns empty string."""
        result = JournalEntrySeederService.convert_plain_text_to_html('   \n\n  ')
        self.assertEqual(result, '')

    def test_single_line(self):
        """Test that single line becomes single paragraph."""
        result = JournalEntrySeederService.convert_plain_text_to_html('Hello world')
        self.assertEqual(result, '<p>Hello world</p>')

    def test_single_line_with_leading_trailing_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        result = JournalEntrySeederService.convert_plain_text_to_html('  Hello world  ')
        self.assertEqual(result, '<p>Hello world</p>')

    def test_multiple_consecutive_lines_separate_paragraphs(self):
        """Test that each line becomes its own paragraph."""
        result = JournalEntrySeederService.convert_plain_text_to_html('Line 1\nLine 2\nLine 3')
        self.assertEqual(result, '<p>Line 1</p><p>Line 2</p><p>Line 3</p>')

    def test_blank_lines_skipped(self):
        """Test that blank lines are skipped (each line is already a paragraph)."""
        result = JournalEntrySeederService.convert_plain_text_to_html('Para 1\n\nPara 2')
        self.assertEqual(result, '<p>Para 1</p><p>Para 2</p>')

    def test_multiple_consecutive_blank_lines(self):
        """Test that multiple blank lines are all skipped."""
        result = JournalEntrySeederService.convert_plain_text_to_html('Para 1\n\n\n\nPara 2')
        self.assertEqual(result, '<p>Para 1</p><p>Para 2</p>')

    def test_leading_trailing_newlines_stripped(self):
        """Test that leading/trailing newlines are stripped."""
        result = JournalEntrySeederService.convert_plain_text_to_html('\n\nHello\n\n')
        self.assertEqual(result, '<p>Hello</p>')

    def test_whitespace_only_lines_treated_as_blank(self):
        """Test that whitespace-only lines are treated as blank."""
        result = JournalEntrySeederService.convert_plain_text_to_html('Para 1\n  \nPara 2')
        self.assertEqual(result, '<p>Para 1</p><p>Para 2</p>')

    def test_internal_whitespace_normalized(self):
        """Test that multiple internal spaces collapse to single space."""
        result = JournalEntrySeederService.convert_plain_text_to_html('Hello    world')
        self.assertEqual(result, '<p>Hello world</p>')

    def test_mixed_whitespace_scenario(self):
        """Test complex whitespace scenario."""
        text = '  Line 1  \n  Line 2  \n  \n  Para 2  '
        result = JournalEntrySeederService.convert_plain_text_to_html(text)
        self.assertEqual(result, '<p>Line 1</p><p>Line 2</p><p>Para 2</p>')

    def test_carriage_return_normalization(self):
        """Test that \\r and \\r\\n are normalized to \\n."""
        result = JournalEntrySeederService.convert_plain_text_to_html('Line 1\r\nLine 2\rLine 3')
        self.assertEqual(result, '<p>Line 1</p><p>Line 2</p><p>Line 3</p>')

    def test_tab_characters_normalized(self):
        """Test that tab characters are normalized to spaces."""
        result = JournalEntrySeederService.convert_plain_text_to_html('Hello\t\tworld')
        self.assertEqual(result, '<p>Hello world</p>')

    def test_html_characters_preserved(self):
        """Test that HTML characters are preserved (sanitizer will escape them)."""
        result = JournalEntrySeederService.convert_plain_text_to_html('<script>alert("xss")</script>')
        # The conversion just wraps in <p>, sanitizer will escape
        self.assertIn('<script>', result)
        self.assertIn('<p>', result)

    def test_unicode_characters(self):
        """Test that unicode characters are preserved."""
        result = JournalEntrySeederService.convert_plain_text_to_html('Hello 😊 世界')
        self.assertEqual(result, '<p>Hello 😊 世界</p>')

    def test_multiple_paragraphs_complex(self):
        """Test complex multi-paragraph scenario with multiple lines."""
        text = '''First paragraph with
multiple lines.

Second paragraph.

Third paragraph with
more lines and   spaces.'''
        result = JournalEntrySeederService.convert_plain_text_to_html(text)
        self.assertEqual(
            result,
            '<p>First paragraph with</p>'
            '<p>multiple lines.</p>'
            '<p>Second paragraph.</p>'
            '<p>Third paragraph with</p>'
            '<p>more lines and spaces.</p>'
        )


class SeederServiceTests(TestCase):
    """Test cases for create_from_notebook_entry()."""

    def setUp(self):
        """Create test user, trip, and journal."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        self.trip = Trip.objects.create(
            title='Test Trip',
            description='A test trip'
        )

        self.journal = Journal.objects.create(
            trip=self.trip,
            title='Test Journal',
            timezone='America/New_York',
            modified_by=self.user,
        )

    def test_create_from_notebook_entry_basic(self):
        """Test basic conversion from NotebookEntry to JournalEntry."""
        notebook_entry = NotebookEntry.objects.create(
            trip=self.trip,
            date='2024-01-15',
            text='Simple note'
        )

        journal_entry = JournalEntrySeederService.create_from_notebook_entry(
            notebook_entry=notebook_entry,
            journal=self.journal,
            user=self.user,
        )

        self.assertEqual(journal_entry.journal, self.journal)
        self.assertEqual(journal_entry.date, notebook_entry.date)
        self.assertEqual(journal_entry.text, '<p>Simple note</p>')
        self.assertEqual(journal_entry.source_notebook_entry, notebook_entry)
        self.assertEqual(journal_entry.source_notebook_version, notebook_entry.edit_version)
        self.assertEqual(journal_entry.modified_by, self.user)

    def test_create_from_notebook_entry_multi_paragraph(self):
        """Test conversion with multiple paragraphs."""
        notebook_entry = NotebookEntry.objects.create(
            trip=self.trip,
            date='2024-01-15',
            text='Para 1\n\nPara 2\n\nPara 3'
        )

        journal_entry = JournalEntrySeederService.create_from_notebook_entry(
            notebook_entry=notebook_entry,
            journal=self.journal,
            user=self.user,
        )

        self.assertEqual(journal_entry.text, '<p>Para 1</p><p>Para 2</p><p>Para 3</p>')

    def test_create_from_notebook_entry_empty_text(self):
        """Test conversion with empty text."""
        notebook_entry = NotebookEntry.objects.create(
            trip=self.trip,
            date='2024-01-15',
            text=''
        )

        journal_entry = JournalEntrySeederService.create_from_notebook_entry(
            notebook_entry=notebook_entry,
            journal=self.journal,
            user=self.user,
        )

        self.assertEqual(journal_entry.text, '')

    def test_create_from_notebook_entry_html_sanitized(self):
        """Test that HTML is sanitized (dangerous content removed)."""
        notebook_entry = NotebookEntry.objects.create(
            trip=self.trip,
            date='2024-01-15',
            text='<script>alert("xss")</script>Safe content'
        )

        journal_entry = JournalEntrySeederService.create_from_notebook_entry(
            notebook_entry=notebook_entry,
            journal=self.journal,
            user=self.user,
        )

        # Script tags should be escaped by sanitizer
        self.assertNotIn('<script>', journal_entry.text)
        self.assertIn('Safe content', journal_entry.text)
        # Should have paragraph tags
        self.assertIn('<p>', journal_entry.text)

    def test_timezone_inherited_from_journal(self):
        """Test that timezone is inherited from journal, not notebook entry."""
        notebook_entry = NotebookEntry.objects.create(
            trip=self.trip,
            date='2024-01-15',
            text='Test'
        )

        journal_entry = JournalEntrySeederService.create_from_notebook_entry(
            notebook_entry=notebook_entry,
            journal=self.journal,
            user=self.user,
        )

        self.assertEqual(journal_entry.timezone, self.journal.timezone)
        self.assertEqual(journal_entry.timezone, 'America/New_York')
