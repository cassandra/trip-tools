from django.contrib import admin

from tt.apps.common.admin_utils import admin_link
from tt.apps.members.models import TripMember

from . import models


class TripMemberInline(admin.TabularInline):
    model = TripMember
    extra = 0
    readonly_fields = ( 'added_datetime', )

    fields = (
        'user',
        'permission_level',
        'added_by',
        'added_datetime',
    )


@admin.register( models.Trip )
class TripAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'title',
        'owner_link',
        'trip_status',
        'uuid',
        'created_datetime',
        'modified_datetime',
    )

    list_filter = ( 'trip_status', 'created_datetime' )
    search_fields = [ 'title', 'description', 'members__user__email' ]
    readonly_fields = ( 'created_datetime', 'modified_datetime', 'uuid' )
    inlines = [ TripMemberInline ]

    @admin_link( 'owner', 'Owner' )
    def owner_link(self, owner):
        if owner:
            return owner.email
        return '(No owner)'
