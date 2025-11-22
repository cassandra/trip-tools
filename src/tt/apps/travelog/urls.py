from django.urls import path, register_converter

from . import views
from .enums import ContentType


class ContentTypeConverter:
    """
    Allows content type parameterization with regular "path" UUID conveniences.
    Converts URL string to ContentType enum.
    """
    regex = '(draft|view|version)'

    def to_python(self, value):
        return ContentType.from_name(value)

    def to_url(self, value):
        if isinstance(value, ContentType):
            return value.name.lower()
        return str(value).lower()


register_converter(ContentTypeConverter, 'content_type')


urlpatterns = [

    path(
        'user/<uuid:user_uuid>',
        views.TravelogUserListView.as_view(),
        name='travelog_user_list'
    ),
    path(
        'password/<uuid:journal_uuid>',
        views.TravelogPasswordEntryView.as_view(),
        name='travelog_password_entry'
    ),
    path(
        '<content_type:content_type>/<uuid:journal_uuid>',
        views.TravelogTableOfContentsView.as_view(),
        name='travelog_toc'
    ),
    path(
        '<content_type:content_type>/<uuid:journal_uuid>/day/<str:date>',
        views.TravelogDayView.as_view(),
        name='travelog_day'
    ),
    path(
        '<content_type:content_type>/<uuid:journal_uuid>/gallery',
        views.TravelogImageGalleryView.as_view(),
        name='travelog_gallery'
    ),
    path(
        '<content_type:content_type>/<uuid:journal_uuid>/gallery/<int:page_num>',
        views.TravelogImageGalleryView.as_view(),
        name='travelog_gallery_page'
    ),
    path(
        '<content_type:content_type>/<uuid:journal_uuid>/image/<uuid:image_uuid>',
        views.TravelogImageBrowseView.as_view(),
        name='travelog_image_browse'
    ),
]
