from django.contrib import admin

from tt.apps.common.admin_utils import admin_link

from . import models


class CandidateInline(admin.TabularInline):
    model = models.Candidate
    extra = 0
    show_change_link = True
    fields = ('name', 'preference_order', 'total_cost', 'unit_cost', 'currency')
    ordering = ('preference_order',)


class CandidateAttributeInline(admin.TabularInline):
    model = models.CandidateAttribute
    extra = 0
    show_change_link = True


@admin.register(models.CandidateGroup)
class CandidateGroupAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'title',
        'user_link',
        'trip_link',
        'candidate_type',
        'location_link',
        'candidate_count',
        'created_datetime',
    )

    list_filter = ('candidate_type', 'created_datetime')
    search_fields = ['title', 'description', 'user__username', 'trip__title']
    readonly_fields = ('created_datetime', 'modified_datetime')
    inlines = [CandidateInline]

    @admin_link('user', 'User')
    def user_link(self, user):
        return user.username

    @admin_link('trip', 'Trip')
    def trip_link(self, trip):
        return trip.title

    @admin_link('location', 'Location')
    def location_link(self, location):
        return location.title if location else '-'

    def candidate_count(self, obj):
        return obj.candidates.count()
    candidate_count.short_description = 'Candidates'


@admin.register(models.Candidate)
class CandidateAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'name',
        'group_link',
        'preference_order',
        'total_cost',
        'unit_cost',
        'currency',
        'location_link',
    )

    list_filter = ('group__candidate_type',)
    search_fields = ['name', 'notes', 'group__title']
    readonly_fields = ('created_datetime', 'modified_datetime')
    inlines = [CandidateAttributeInline]

    @admin_link('group', 'Group')
    def group_link(self, group):
        return group.title

    @admin_link('location', 'Location')
    def location_link(self, location):
        return location.title if location else '-'


@admin.register(models.CandidateAttribute)
class CandidateAttributeAdmin(admin.ModelAdmin):
    show_full_result_count = False

    list_display = (
        'candidate_link',
        'name',
        'value',
        'value_type',
        'attribute_type',
    )

    search_fields = ['name', 'value', 'candidate__name']
    list_filter = ('value_type', 'attribute_type')

    @admin_link('candidate', 'Candidate')
    def candidate_link(self, candidate):
        return candidate.name
