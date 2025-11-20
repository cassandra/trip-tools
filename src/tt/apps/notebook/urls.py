from django.urls import path

from . import views

urlpatterns = [
    path(
        'trip/<uuid:trip_uuid>',
        views.NotebookListView.as_view(),
        name='notebook_list'
    ),
    path(
        'trip/<uuid:trip_uuid>/new',
        views.NotebookEntryNewView.as_view(),
        name='notebook_entry_new'
    ),
    path(
        'entry/<uuid:entry_uuid>',
        views.NotebookEntryView.as_view(),
        name='notebook_entry'
    ),
    path(
        'entry/<uuid:entry_uuid>/save',
        views.NotebookAutoSaveView.as_view(),
        name='notebook_autosave'
    ),
    path(
        'entry/<uuid:entry_uuid>/delete',
        views.NotebookEntryDeleteModalView.as_view(),
        name='notebook_entry_delete'
    ),
]
