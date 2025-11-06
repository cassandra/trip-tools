from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^trip$', views.TripImagesHomeView.as_view(), name='images_trip_home'),
    re_path(r'^trip-image/(?P<image_uuid>[0-9a-f-]+)/inspect/$', views.TripImageInspectView.as_view(), name='images_trip_image_inspect'),
]
