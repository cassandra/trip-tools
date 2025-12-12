from django.contrib import admin

from tt.apps.common.admin_utils import admin_link

from . import models


@admin.register( models.APIToken )
class APITokenAdmin( admin.ModelAdmin ):
    show_full_result_count = False

    list_display = (
        'name',
        'token_type',
        'user_link',
        'lookup_key',
        'created_at',
        'last_used_at',
    )

    list_filter = ( 'token_type', 'created_at', 'last_used_at' )
    search_fields = [ 'name', 'user__email', 'lookup_key' ]
    readonly_fields = ( 'lookup_key', 'created_at', 'last_used_at' )

    fields = (
        'user',
        'name',
        'token_type',
        'lookup_key',
        'created_at',
        'last_used_at',
    )

    @admin_link('user', 'User')
    def user_link(self, user):
        if user:
            return user.email
        return '(No user)'


@admin.register( models.SyncDeletionLog )
class SyncDeletionLogAdmin( admin.ModelAdmin ):
    show_full_result_count = False

    list_display = (
        'uuid',
        'object_type',
        'trip_uuid',
        'deleted_by',
        'deleted_at',
    )

    list_filter = ( 'object_type', 'deleted_at' )
    search_fields = [ 'uuid', 'trip_uuid' ]
    readonly_fields = ( 'uuid', 'object_type', 'trip_uuid', 'deleted_by', 'deleted_at' )
