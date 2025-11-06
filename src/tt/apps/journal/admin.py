from django.contrib import admin

from tt.apps.common.admin_utils import admin_link

from . import models


@admin.register(models.Journal)
class JournalAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'title',
        'trip_link',
        'visibility',
        'has_password',
        'created_datetime',
        'modified_datetime',
    )

    list_filter = ('visibility', 'created_datetime')
    search_fields = ['title', 'description', 'trip__title']
    readonly_fields = ('uuid', 'created_datetime', 'modified_datetime')

    @admin_link('trip', 'Trip')
    def trip_link(self, trip):
        return trip.title


@admin.register(models.JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'date',
        'journal_link',
        'title',
        'has_reference_image',
        'has_source_notebook',
        'modified_datetime',
    )

    list_filter = ('date', 'created_datetime')
    search_fields = ['title', 'text', 'journal__title']
    readonly_fields = ('edit_version', 'created_datetime', 'modified_datetime')
    date_hierarchy = 'date'

    @admin_link('journal', 'Journal')
    def journal_link(self, journal):
        return journal.title

    def has_reference_image(self, obj):
        return bool(obj.reference_image)
    has_reference_image.short_description = 'Ref Image'
    has_reference_image.boolean = True

    def has_source_notebook(self, obj):
        return bool(obj.source_notebook_entry)
    has_source_notebook.short_description = 'From Notebook'
    has_source_notebook.boolean = True
