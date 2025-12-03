from django.contrib import admin

from tt.apps.common.admin_utils import admin_link

from . import models


@admin.register(models.TripImage)
class TripImageAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'uuid',
        'datetime_utc',
        'timezone',
        'timezone_unknown',
        'has_exif',
        'uploaded_by_link',
        'uploaded_datetime',
        'upload_session_uuid',
        'caption_preview',
        'tags_preview',
    )

    list_filter = (
        'datetime_utc',
        'uploaded_datetime',
        'has_exif',
        'timezone',
    )
    search_fields = ['caption', 'tags', 'uploaded_by__email']
    readonly_fields = ('uuid', 'uploaded_datetime', 'upload_session_uuid', 'has_exif', 'timezone_unknown')
    date_hierarchy = 'datetime_utc'

    @admin_link('uploaded_by', 'Uploaded By')
    def uploaded_by_link(self, user):
        return user.email if user else 'Unknown'

    def caption_preview(self, obj):
        if not obj.caption:
            return '(no caption)'
        return obj.caption[:50] + '...' if len(obj.caption) > 50 else obj.caption
    caption_preview.short_description = 'Caption'

    def tags_preview(self, obj):
        if not obj.tags:
            return '(no tags)'
        # Join first 3 tags with commas
        tags_display = ', '.join(obj.tags[:3])
        if len(obj.tags) > 3:
            tags_display += f' (+{len(obj.tags) - 3} more)'
        return tags_display
    tags_preview.short_description = 'Tags'
