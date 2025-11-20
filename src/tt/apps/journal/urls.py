from django.urls import path

from . import views

urlpatterns = [
    path(
        'trip/<uuid:trip_uuid>',
        views.JournalHomeView.as_view(),
        name='journal_home'
    ),
    path(
        'trip/<uuid:trip_uuid>/create',
        views.JournalCreateView.as_view(),
        name='journal_create'
    ),
    path(
        '<uuid:journal_uuid>',
        views.JournalView.as_view(),
        name='journal'
    ),
    path(
        '<uuid:journal_uuid>/entry/new/',
        views.JournalEntryNewView.as_view(),
        name='journal_entry_new'
    ),
    path(
        'entry/<uuid:entry_uuid>',
        views.JournalEntryView.as_view(),
        name='journal_entry'
    ),
    path(
        'entry/<uuid:entry_uuid>/save',
        views.JournalEntryAutosaveView.as_view(),
        name='journal_entry_autosave'
    ),
    path(
        'entry/<uuid:entry_uuid>/delete',
        views.JournalEntryDeleteModalView.as_view(),
        name='journal_entry_delete'
    ),
    path(
        'entry/<uuid:entry_uuid>/images/',
        views.JournalEntryImagePickerView.as_view(),
        name='journal_entry_images'
    ),
    path(
        'entry/editor-help',
        views.JournalEditorHelpView.as_view(),
        name='journal_editor_help'
    ),
]
