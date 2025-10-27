from django.contrib import admin

from tt.apps.common.admin_utils import admin_link

from . import models


class SubsystemAttributeInLine(admin.TabularInline):
    model = models.SubsystemAttribute
    extra = 0
    show_change_link = True


class SubsystemAttributeHistoryInLine(admin.TabularInline):
    model = models.SubsystemAttributeHistory
    extra = 0
    show_change_link = True
    readonly_fields = ('value', 'changed_datetime')
    can_delete = False


@admin.register(models.Subsystem)
class SubsystemAdmin(admin.ModelAdmin):
    show_full_result_count = False
    
    list_display = (
        'name',
        'subsystem_key',
        'created_datetime',
    )

    inlines = [ SubsystemAttributeInLine, ]


@admin.register(models.SubsystemAttribute)
class SubsystemAttributeAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'subsystem',
        'user_link',
        'name',
        'value',
        'value_type',
        'attribute_type',
        'setting_key',
        'created_datetime',
    )

    search_fields = ['name', 'subsystem__name', 'setting_key']
    readonly_fields = ('subsystem', 'created_datetime')
    inlines = [SubsystemAttributeHistoryInLine]
    
    @admin_link('user', 'User')
    def user_link(self, user):
        return user.admin_name


