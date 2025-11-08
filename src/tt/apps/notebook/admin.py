from django.contrib import admin

from tt.apps.common.admin_utils import admin_link

from . import models


@admin.register(models.NotebookEntry)
class NotebookEntryAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'date',
        'trip_link',
        'text_preview',
        'created_datetime',
    )

    list_filter = ('date', 'created_datetime')
    search_fields = ['text', 'trip__title']
    readonly_fields = ('created_datetime', 'modified_datetime')
    date_hierarchy = 'date'

    @admin_link('trip', 'Trip')
    def trip_link(self, trip):
        return trip.title

    def text_preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    text_preview.short_description = 'Text'
