from django.urls import re_path

from . import views


urlpatterns = [

    re_path(r'^$',
            views.TestUiNotebookHomeView.as_view(),
            name='notebook_tests_ui'),

    re_path(r'^modal/conflict$',
            views.TestUiConflictModalView.as_view(),
            name='notebook_tests_ui_conflict_modal'),

    re_path(r'^modal/conflict-long-diff$',
            views.TestUiConflictModalLongDiffView.as_view(),
            name='notebook_tests_ui_conflict_modal_long'),

    re_path(r'^modal/conflict-no-diff$',
            views.TestUiConflictModalEmptyDiffView.as_view(),
            name='notebook_tests_ui_conflict_modal_empty'),
]
