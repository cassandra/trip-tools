from django.contrib import admin

from . import models


@admin.register(models.ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'contact_type',
        'label',
        'value_preview',
        'is_primary',
        'content_type',
        'object_id',
        'created_datetime',
    )

    list_filter = ('contact_type', 'is_primary', 'content_type')
    search_fields = ['value', 'label', 'notes']
    readonly_fields = ('created_datetime', 'modified_datetime', 'content_type', 'object_id')

    def value_preview(self, obj):
        return obj.value[:50] + '...' if len(obj.value) > 50 else obj.value
    value_preview.short_description = 'Value'
