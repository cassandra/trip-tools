from django.urls import path

from . import views


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
        '<uuid:journal_uuid>',
        views.TravelogTableOfContentsView.as_view(),
        name='travelog_toc'
    ),
    path(
        '<uuid:journal_uuid>/day/<str:date>',
        views.TravelogDayView.as_view(),
        name='travelog_day'
    ),
    path(
        '<uuid:journal_uuid>/gallery',
        views.TravelogImageGalleryView.as_view(),
        name='travelog_gallery'
    ),
    path(
        '<uuid:journal_uuid>/gallery/<int:page_num>',
        views.TravelogImageGalleryView.as_view(),
        name='travelog_gallery_page'
    ),
    path(
        '<uuid:journal_uuid>/image/<uuid:image_uuid>',
        views.TravelogImageBrowseView.as_view(),
        name='travelog_image_browse'
    ),
]
