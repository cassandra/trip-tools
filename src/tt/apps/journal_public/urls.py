from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^(?P<journal_uuid>[0-9a-f-]+)/$', views.JournalTableOfContentsView.as_view(), name='journal_public_toc'),
    re_path(r'^(?P<journal_uuid>[0-9a-f-]+)/(?P<date>\d{4}-\d{2}-\d{2})$', views.JournalDayView.as_view(), name='journal_public_day'),
    re_path(r'^(?P<journal_uuid>[0-9a-f-]+)/image/gallery/(?P<page_num>\d+)$', views.JournalImageGalleryView.as_view(), name='journal_public_gallery'),
    re_path(r'^(?P<journal_uuid>[0-9a-f-]+)/image/browse/(?P<image_uuid>[0-9a-f-]+)$', views.JournalImageBrowseView.as_view(), name='journal_public_image_browse'),
]
