from django.contrib import admin

from tt.apps.common.admin_utils import admin_link

from . import models


class RouteWaypointInline(admin.TabularInline):
    model = models.RouteWaypoint
    extra = 0
    show_change_link = True
    fields = ('order', 'latitude', 'longitude', 'at_datetime', 'notes')
    ordering = ('order',)


@admin.register(models.Route)
class RouteAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'id',
        'user_link',
        'trip_link',
        'waypoint_count',
        'created_datetime',
    )

    search_fields = ['user__username', 'trip__title', 'notes']
    readonly_fields = ('created_datetime', 'modified_datetime')
    inlines = [RouteWaypointInline]

    @admin_link('user', 'User')
    def user_link(self, user):
        return user.username

    @admin_link('trip', 'Trip')
    def trip_link(self, trip):
        return trip.title

    def waypoint_count(self, obj):
        return obj.waypoints.count()
    waypoint_count.short_description = 'Waypoints'


@admin.register(models.RouteWaypoint)
class RouteWaypointAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'route_link',
        'order',
        'latitude',
        'longitude',
        'at_datetime',
    )

    list_filter = ('route__trip',)
    search_fields = ['route__trip__title', 'notes']
    ordering = ('route', 'order')

    @admin_link('route', 'Route')
    def route_link(self, route):
        return f'Route {route.id}'
