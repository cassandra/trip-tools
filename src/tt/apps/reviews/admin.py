from django.contrib import admin

from tt.apps.common.admin_utils import admin_link

from . import models


class ReviewAttributeInline(admin.TabularInline):
    model = models.ReviewAttribute
    extra = 0
    show_change_link = True


@admin.register(models.Review)
class ReviewAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'title',
        'user_link',
        'trip_link',
        'location_link',
        'rating',
        'posted_to_preview',
        'created_datetime',
    )

    list_filter = ('rating', 'created_datetime')
    search_fields = ['title', 'text', 'user__email', 'location__title', 'posted_to']
    readonly_fields = ('created_datetime', 'modified_datetime')
    inlines = [ReviewAttributeInline]

    @admin_link('user', 'User')
    def user_link(self, user):
        return user.email

    @admin_link('trip', 'Trip')
    def trip_link(self, trip):
        return trip.title

    @admin_link('location', 'Location')
    def location_link(self, location):
        return location.title

    def posted_to_preview(self, obj):
        if not obj.posted_to:
            return '-'
        return obj.posted_to[:50] + '...' if len(obj.posted_to) > 50 else obj.posted_to
    posted_to_preview.short_description = 'Posted To'


@admin.register(models.ReviewAttribute)
class ReviewAttributeAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'review_link',
        'name',
        'value',
        'value_type',
        'attribute_type',
    )

    search_fields = ['name', 'value', 'review__title']
    list_filter = ('value_type', 'attribute_type')

    @admin_link('review', 'Review')
    def review_link(self, review):
        return review.title
