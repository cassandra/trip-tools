from django.urls import path

from . import views

urlpatterns = [
    path(
        '<uuid:journal_uuid>',
        views.TravelogTableOfContentsView.as_view(),
        name='travelog_toc'
    ),
    path(
        '<journal_uuid>/<str:date>',
        views.TravelogDayView.as_view(),
        name='travelog_day'
    ),
    path(
        '<uuid:journal_uuid>/image/gallery/<int:page_num>',
        views.TravelogImageGalleryView.as_view(),
        name='travelog_gallery'
    ),
    path(
        '<uuid:journal_uuid>/image/browse/<uuid:image_uuid>',
        views.TravelogImageBrowseView.as_view(),
        name='travelog_image_browse'
    ),
]
