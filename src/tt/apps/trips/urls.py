from django.urls import re_path

from . import views


urlpatterns = [
    re_path(r'^create$', views.TripCreateModalView.as_view(), name='trip_create'),
    re_path(r'^(?P<trip_id>\d+)$', views.TripHomeView.as_view(), name='trip_home'),
]
