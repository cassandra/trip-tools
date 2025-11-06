from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^trip/(?P<trip_id>\d+)/$', views.JournalHomeView.as_view(), name='journal_home'),
    re_path(r'^trip/(?P<trip_id>\d+)/create$', views.CreateJournalView.as_view(), name='journal_create'),
    re_path(r'^trip/(?P<trip_id>\d+)/entry/(?P<entry_pk>\d+)/$', views.JournalEntryView.as_view(), name='journal_entry'),
    re_path(r'^trip/(?P<trip_id>\d+)/entry/(?P<entry_pk>\d+)/save$', views.JournalEntryAutosaveView.as_view(), name='journal_entry_autosave'),
]
