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
        views.NotebookEditView.as_view(),
        name='notebook_new'
    ),
    re_path(
        r'^trip/(?P<trip_id>\d+)/entry/(?P<entry_pk>\d+)/$',
        views.NotebookEditView.as_view(),
        name='notebook_edit'
    ),
    re_path(
        r'^trip/(?P<trip_id>\d+)/entry/(?P<entry_pk>\d+)/save/$',
        views.NotebookAutoSaveView.as_view(),
        name='notebook_autosave'
    ),
]
