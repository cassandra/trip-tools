from django.contrib import admin

from tt.apps.common.admin_utils import admin_link

from . import models


@admin.register(models.APIToken)
class APITokenAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'name',
        'user_link',
        'lookup_key',
        'created_at',
        'last_used_at',
    )

    list_filter = ('created_at', 'last_used_at')
    search_fields = ['name', 'user__email', 'lookup_key']
    readonly_fields = ('lookup_key', 'created_at', 'last_used_at')

    fields = (
        'user',
        'name',
        'lookup_key',
        'created_at',
        'last_used_at',
    )

    @admin_link('user', 'User')
    def user_link(self, user):
        if user:
            return user.email
        return '(No user)'
