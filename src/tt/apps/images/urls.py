from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^trip$', views.TripImagesHomeView.as_view(), name='images_trip_home'),
]
