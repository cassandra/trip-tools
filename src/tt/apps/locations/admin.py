from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from tt.apps.common.admin_utils import admin_link
from tt.apps.contacts.models import ContactInfo

from . import models


class ContactInfoInline(GenericTabularInline):
    model = ContactInfo
    extra = 0
    fields = ('contact_type', 'value', 'label', 'is_primary')


class LocationNoteInline(admin.TabularInline):
    model = models.LocationNote
    extra = 0
    show_change_link = True
    fields = ('text', 'source_label', 'source_url', 'created_datetime')
    readonly_fields = ('created_datetime',)


class LocationSubCategoryInline(admin.TabularInline):
    model = models.LocationSubCategory
    extra = 0
    show_change_link = True
    fields = ('name', 'slug', 'color_code', 'icon_code')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(models.LocationCategory)
class LocationCategoryAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'name',
        'slug',
        'color_code',
        'icon_code',
    )

    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'slug']
    inlines = [LocationSubCategoryInline]


@admin.register(models.LocationSubCategory)
class LocationSubCategoryAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'name',
        'category_link',
        'slug',
        'color_code',
        'icon_code',
    )

    list_filter = ('category',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'slug', 'category__name']

    @admin_link('category', 'Category')
    def category_link(self, category):
        return category.name


@admin.register(models.Location)
class LocationAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'title',
        'trip_link',
        'gmm_id',
        'version',
        'subcategory_link',
        'rating',
        'desirability',
        'open_days_times',
        'created_datetime',
    )

    list_filter = ('desirability', 'advanced_booking', 'subcategory__category')
    search_fields = ['title', 'user__email', 'trip__title']
    readonly_fields = ( 'trip', 'created_datetime', 'modified_datetime')
    inlines = [LocationNoteInline, ContactInfoInline]

    @admin_link('trip', 'Trip')
    def trip_link(self, trip):
        return trip.title

    @admin_link('subcategory', 'Subcategory')
    def subcategory_link(self, subcategory):
        return subcategory.name if subcategory else '-'


@admin.register(models.LocationNote)
class LocationNoteAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'location_link',
        'text_preview',
        'source_label',
        'created_datetime',
    )

    search_fields = ['text', 'source_label', 'location__title']
    readonly_fields = ('created_datetime', 'modified_datetime')

    @admin_link('location', 'Location')
    def location_link(self, location):
        return location.title

    def text_preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    text_preview.short_description = 'Text'
