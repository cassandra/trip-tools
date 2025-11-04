from django.urls import re_path

from . import views

urlpatterns = [
    re_path(
        r'^trip/(?P<trip_id>\d+)/$',
        views.NotebookListView.as_view(),
        name='notebook_list'
    ),
    re_path(
        r'^trip/(?P<trip_id>\d+)/entry/new/$',
        views.NotebookEntryView.as_view(),
        name='notebook_entry_new'
    ),
    re_path(
        r'^trip/(?P<trip_id>\d+)/entry/(?P<entry_pk>\d+)/$',
        views.NotebookEntryView.as_view(),
        name='notebook_entry'
    ),
    re_path(
        r'^trip/(?P<trip_id>\d+)/entry/(?P<entry_pk>\d+)/save/$',
        views.NotebookAutoSaveView.as_view(),
        name='notebook_autosave'
    ),
]
