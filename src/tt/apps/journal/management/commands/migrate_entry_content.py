"""
Management command to migrate/normalize entry content.

Runs active normalizers on JournalEntry and TravelogEntry records to
fix or update HTML content. Safe by default (dry-run mode).

Usage:
    python manage.py migrate_entry_content           # Dry run (preview)
    python manage.py migrate_entry_content --execute # Apply changes
    python manage.py migrate_entry_content --verbose # Show detailed changes
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from tt.apps.journal.models import JournalEntry
from tt.apps.travelog.models import TravelogEntry

from ..content_normalizers import ACTIVE_NORMALIZERS


class Command(BaseCommand):
    help = 'Migrate/normalize HTML content in JournalEntry and TravelogEntry records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--execute',
            action='store_true',
            help='Actually apply changes (default is dry-run)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed per-change information',
        )

    def handle(self, *args, **options):
        execute = options['execute']
        verbose = options['verbose']

        if not ACTIVE_NORMALIZERS:
            self.stdout.write(self.style.WARNING('No active normalizers configured.'))
            return

        # Display mode and normalizers
        if execute:
            self.stdout.write(self.style.WARNING('=== EXECUTE MODE - Changes will be saved ===\n'))
        else:
            self.stdout.write(self.style.NOTICE('=== DRY RUN - No changes will be saved ===\n'))

        self.stdout.write('Active normalizers:')
        for normalizer in ACTIVE_NORMALIZERS:
            self.stdout.write(f'  - {normalizer.name}: {normalizer.description}')
        self.stdout.write('')

        # Track statistics
        stats = {
            'JournalEntry': {'processed': 0, 'modified': 0, 'changes': 0},
            'TravelogEntry': {'processed': 0, 'modified': 0, 'changes': 0},
        }

        # Process entries
        if execute:
            with transaction.atomic():
                self._process_all_entries(stats, verbose, execute=True)
        else:
            self._process_all_entries(stats, verbose, execute=False)

        # Summary
        self._print_summary(stats, execute)

    def _process_all_entries(self, stats, verbose, execute):
        """Process JournalEntry and TravelogEntry records."""
        # Process JournalEntry
        self.stdout.write(self.style.MIGRATE_HEADING('Processing JournalEntry records...'))
        journal_entries = JournalEntry.objects.exclude(text='').order_by('date')
        self._process_entries(
            journal_entries, 'JournalEntry', stats, verbose, execute
        )
        self.stdout.write('')

        # Process TravelogEntry
        self.stdout.write(self.style.MIGRATE_HEADING('Processing TravelogEntry records...'))
        travelog_entries = TravelogEntry.objects.exclude(text='').order_by('travelog', 'date')
        self._process_entries(
            travelog_entries, 'TravelogEntry', stats, verbose, execute
        )
        self.stdout.write('')

    def _process_entries(self, queryset, model_name, stats, verbose, execute):
        """Process a queryset of entries through all normalizers."""
        entries = list(queryset)
        total = len(entries)

        if total == 0:
            self.stdout.write('  No entries with content found.')
            return

        for idx, entry in enumerate(entries, 1):
            entry_label = self._get_entry_label(entry, model_name)
            all_changes = []

            # Run all normalizers
            normalized_text = entry.text
            for normalizer in ACTIVE_NORMALIZERS:
                normalized_text, changes = normalizer.normalize(normalized_text, entry)
                all_changes.extend(changes)

            stats[model_name]['processed'] += 1

            if all_changes:
                stats[model_name]['modified'] += 1
                stats[model_name]['changes'] += len(all_changes)

                # Output entry info
                prefix = f'  [{idx}/{total}]'
                self.stdout.write(f'{prefix} {entry_label}')

                if verbose:
                    for change in all_changes:
                        self.stdout.write(f'    - {change}')
                else:
                    self.stdout.write(f'    - {len(all_changes)} change(s)')

                # Apply if executing
                if execute:
                    entry.text = normalized_text
                    entry.save(update_fields=['text'])

    def _get_entry_label(self, entry, model_name):
        """Generate a human-readable label for an entry."""
        if model_name == 'JournalEntry':
            return f'JournalEntry uuid={entry.uuid} ({entry.date} "{entry.title}")'
        else:
            return f'TravelogEntry id={entry.id} (travelog="{entry.travelog}" date={entry.date})'

    def _print_summary(self, stats, execute):
        """Print summary statistics."""
        self.stdout.write(self.style.MIGRATE_HEADING('Summary:'))

        action_word = 'modified' if execute else 'would be modified'

        for model_name, model_stats in stats.items():
            processed = model_stats['processed']
            modified = model_stats['modified']
            changes = model_stats['changes']

            if processed == 0:
                self.stdout.write(f'  {model_name}: No entries processed')
            else:
                self.stdout.write(
                    f'  {model_name}: {modified} of {processed} {action_word} '
                    f'({changes} total changes)'
                )

        if not execute:
            self.stdout.write('')
            self.stdout.write(self.style.NOTICE('To apply changes, run with --execute'))
