from django.urls import path

from . import views

urlpatterns = [
    path(
        r'trip/<uuid:trip_uuid>',
        views.JournalHomeView.as_view(),
        name='journal_home'
    ),
    path(
        r'trip/<uuid:trip_uuid>/create',
        views.JournalCreateView.as_view(),
        name='journal_create'
    ),
    path(
        r'<uuid:journal_uuid>',
        views.JournalView.as_view(),
        name='journal'
    ),
    path(
        r'<uuid:journal_uuid>/entry/new/',
        views.JournalEntryNewView.as_view(),
        name='journal_entry_new'
    ),
    path(
        r'entry/<uuid:entry_uuid>',
        views.JournalEntryView.as_view(),
        name='journal_entry'
    ),
    path(
        r'entry/<uuid:entry_uuid>/save',
        views.JournalEntryAutosaveView.as_view(),
        name='journal_entry_autosave'
    ),
    path(
        r'entry/<uuid:entry_uuid>/delete',
        views.JournalEntryDeleteModalView.as_view(),
        name='journal_entry_delete'
    ),
    path(
        r'entry/<uuid:entry_uuid>/images/',
        views.JournalEntryImagePickerView.as_view(),
        name='journal_entry_images'
    ),
    path(
        r'entry/editor-help',
        views.JournalEditorHelpView.as_view(),
        name='journal_editor_help'
    ),
]
