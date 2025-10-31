from django.contrib import admin

from tt.apps.common.admin_utils import admin_link

from . import models


@admin.register(models.Trip)
class TripAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'title',
        'user_link',
        'trip_status',
        'created_datetime',
        'modified_datetime',
    )

    list_filter = ('trip_status', 'created_datetime')
    search_fields = ['title', 'description', 'user__email']
    readonly_fields = ('created_datetime', 'modified_datetime')

    @admin_link('user', 'User')
    def user_link(self, user):
        return user.email
