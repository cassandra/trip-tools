from django.contrib import admin

from tt.apps.common.admin_utils import admin_link

from . import models


class BookingAttributeInline(admin.TabularInline):
    model = models.BookingAttribute
    extra = 0
    show_change_link = True


@admin.register(models.BookingData)
class BookingDataAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'id',
        'user_link',
        'trip_link',
        'itinerary_item_link',
        'booking_status',
        'payment_status',
        'confirmed',
        'total_cost',
        'currency',
    )

    list_filter = ('booking_status', 'payment_status', 'confirmed', 'booking_date')
    search_fields = [
        'user__username',
        'trip__title',
        'booking_site',
        'booking_reference',
        'confirmation_number',
    ]
    readonly_fields = ('created_datetime', 'modified_datetime')
    inlines = [BookingAttributeInline]

    @admin_link('user', 'User')
    def user_link(self, user):
        return user.username

    @admin_link('trip', 'Trip')
    def trip_link(self, trip):
        return trip.title

    @admin_link('itinerary_item', 'Itinerary Item')
    def itinerary_item_link(self, itinerary_item):
        return itinerary_item.title


@admin.register(models.BookingAttribute)
class BookingAttributeAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'booking_data_link',
        'name',
        'value',
        'value_type',
        'attribute_type',
    )

    search_fields = ['name', 'value', 'booking_data__booking_reference']
    list_filter = ('value_type', 'attribute_type')

    @admin_link('booking_data', 'Booking')
    def booking_data_link(self, booking_data):
        return f'Booking {booking_data.id}'
