from django.contrib import admin

from tt.apps.common.admin_utils import admin_link

from . import models


class ItineraryItemInline(admin.TabularInline):
    model = models.ItineraryItem
    extra = 0
    show_change_link = True
    fields = ('title', 'item_type', 'start_datetime', 'end_datetime', 'location', 'route')


@admin.register(models.Itinerary)
class ItineraryAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'title',
        'user_link',
        'trip_link',
        'item_count',
        'created_datetime',
    )

    search_fields = ['title', 'description', 'user__email', 'trip__title']
    readonly_fields = ('created_datetime', 'modified_datetime')
    inlines = [ItineraryItemInline]

    @admin_link('user', 'User')
    def user_link(self, user):
        return user.email

    @admin_link('trip', 'Trip')
    def trip_link(self, trip):
        return trip.title

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'


@admin.register(models.ItineraryItem)
class ItineraryItemAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'title',
        'itinerary_link',
        'item_type',
        'start_datetime',
        'end_datetime',
        'location_link',
    )

    list_filter = ('item_type', 'start_datetime')
    search_fields = ['title', 'description', 'itinerary__title', 'location__title']
    readonly_fields = ('created_datetime', 'modified_datetime')

    @admin_link('itinerary', 'Itinerary')
    def itinerary_link(self, itinerary):
        return itinerary.title

    @admin_link('location', 'Location')
    def location_link(self, location):
        return location.title if location else '-'
