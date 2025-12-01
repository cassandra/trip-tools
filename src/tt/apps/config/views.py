import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import View

from tt.views import page_not_found_response

from tt.apps.attribute.view_mixins import AttributeMultiEditViewMixin

from tt.context import FeaturePageContext
from tt.enums import FeaturePageType

from .models import SubsystemAttribute
from .settings_mixins import SubsystemAttributeMixin
from .signals import SettingsInitializer
from .subsystem_attribute_edit_context import (
    SubsystemAttributeItemEditContext,
    SubsystemAttributePageEditContext,
)

logger = logging.getLogger('__name__')


class ConfigSettingsView( LoginRequiredMixin,
                          AttributeMultiEditViewMixin,
                          SubsystemAttributeMixin,
                          View ):

    def get(self, request, *args, **kwargs):

        # Setting attributes for a user are lazily created on visiting this
        # config page.
        if not SubsystemAttribute.objects.filter( user = request.user ).exists():
            SettingsInitializer().create_initial_attr_items( user = request.user )
            
        attr_item_context_list = self.create_attr_item_context_list( user = request.user )

        selected_subsystem_id = kwargs.get('subsystem_id')
        if not selected_subsystem_id and attr_item_context_list:
            selected_subsystem_id = str(attr_item_context_list[0].owner_id)

        attr_page_context = SubsystemAttributePageEditContext(
            user = request.user,
            selected_subsystem_id = selected_subsystem_id,
        )
        context = self.create_initial_template_context(
            attr_page_context = attr_page_context,
            attr_item_context_list = attr_item_context_list,
        )
        feature_page_context = FeaturePageContext(
            active_page = FeaturePageType.SETTINGS,
        )
        context['feature_page'] = feature_page_context
        return render( request, 'config/pages/settings.html', context )
        
    def post( self, request, *args, **kwargs ):

        attr_item_context_list = self.create_attr_item_context_list( user = request.user )

        selected_subsystem_id = kwargs.get('subsystem_id')
        if not selected_subsystem_id and attr_item_context_list:
            selected_subsystem_id = str(attr_item_context_list[0].owner_id)

        attr_page_context = SubsystemAttributePageEditContext(
            user = request.user,
            selected_subsystem_id = selected_subsystem_id,
        )
        return self.post_attribute_form(
            request = request,
            attr_page_context = attr_page_context,
            attr_item_context_list = attr_item_context_list,
        )
        

class SubsystemAttributeHistoryInlineView( View, AttributeMultiEditViewMixin ):

    def get(self, request, subsystem_id, attribute_id, *args, **kwargs):
        # Validate that the attribute belongs to this subsystem for security
        try:
            attribute = SubsystemAttribute.objects.select_related('subsystem').get(
                pk = attribute_id,
                subsystem_id = subsystem_id,
            )
        except SubsystemAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")

        attr_item_context = SubsystemAttributeItemEditContext(
            user = request.user,
            subsystem = attribute.subsystem,
        )
        return self.get_history(
            request = request,
            attribute = attribute,
            attr_item_context = attr_item_context,
        )


class SubsystemAttributeRestoreInlineView( View,
                                           SubsystemAttributeMixin,
                                           AttributeMultiEditViewMixin ):
    """View for restoring SubsystemAttribute values from history inline."""
    
    def get(self, request, subsystem_id, attribute_id, history_id, *args, **kwargs):
        """ Need to do restore in a GET since nested in main form and cannot have a form in a form """
        try:
            attribute = SubsystemAttribute.objects.select_related('subsystem').get(
                pk = attribute_id,
                subsystem_id = subsystem_id,
            )
        except SubsystemAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")

        attr_page_context = SubsystemAttributePageEditContext(
            user = request.user,
            selected_subsystem_id = subsystem_id,
        )
        attr_item_context_list = self.create_attr_item_context_list( user = request.user )

        return self.post_restore(
            request = request,
            attribute = attribute,
            history_id = history_id,
            attr_page_context = attr_page_context,
            attr_item_context_list = attr_item_context_list,
        )
