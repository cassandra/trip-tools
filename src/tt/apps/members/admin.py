from django.contrib import admin

from tt.apps.common.admin_utils import admin_link

from . import models


@admin.register( models.TripMember )
class TripMemberAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'trip',
        'user_link',
        'permission_level',
        'added_by_link',
        'added_datetime',
    )

    list_filter = ( 'permission_level', 'added_datetime' )
    search_fields = [ 'trip__title', 'user__email' ]
    readonly_fields = ( 'added_datetime', )

    @admin_link( 'user', 'User' )
    def user_link(self, user):
        return user.email

    @admin_link( 'added_by', 'Added By' )
    def added_by_link(self, added_by):
        if added_by:
            return added_by.email
        return '(System)'
